import { existsSync } from 'node:fs'
import { basename } from 'node:path'
import type {
  AiLaneId,
  ListAiLaneModelsRequest,
  ProviderKind,
  SessionProviderStatus
} from '../../shared/contracts'
import {
  ProviderSettingsStore,
  providerLabel,
  type ResolvedProviderConfig
} from './provider-settings-store'

export interface ProviderMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

interface OpenAiModelsResponse {
  data?: Array<{ id?: string }>
}

interface OpenAiChatResponse {
  model?: string
  choices?: Array<{ message?: { content?: string } }>
}

interface OllamaTagsResponse {
  models?: Array<{ name?: string; model?: string }>
}

interface OllamaChatResponse {
  model?: string
  message?: { content?: string }
}

export class ConfiguredProvider {
  constructor(private readonly settings: ProviderSettingsStore) {}

  async status(laneId?: AiLaneId): Promise<SessionProviderStatus> {
    const cfg = this.resolve(laneId)
    try {
      if (cfg.provider === 'local') return this.localStatus(cfg)
      if (cfg.provider === 'ollama') return await this.ollamaStatus(cfg.endpoint, cfg.model)
      return await this.openAiCompatibleStatus(cfg.provider, cfg.endpoint, cfg.model, cfg.apiKey)
    } catch (error: unknown) {
      return {
        ready: false,
        provider: cfg.provider,
        providerLabel: providerLabel(cfg.provider),
        endpoint: cfg.endpoint,
        model: cfg.model || null,
        configuredModel: cfg.model,
        availableModels: [],
        detail: error instanceof Error ? error.message : String(error)
      }
    }
  }

  async listModels(request: ListAiLaneModelsRequest): Promise<string[]> {
    if (!request.provider) return []
    const provider = request.provider
    if (provider === 'local') {
      const source = request.localModelPath?.trim() ?? ''
      return source && existsSync(source) ? [basename(source)] : []
    }

    const resolved = this.settings.resolveLane(request.laneId)
    const endpoint = (request.endpoint?.trim() || resolved.endpoint).replace(/\/+$/, '')
    if (!endpoint) return []

    if (provider === 'ollama') {
      const response = await this.fetchWithTimeout(`${endpoint}/api/tags`, { method: 'GET' }, 5000)
      if (!response.ok) throw new Error(`OLLAMA_MODELS_HTTP_${response.status}`)
      const payload = await response.json() as OllamaTagsResponse
      return Array.from(new Set((payload.models ?? []).map(item => item.name ?? item.model ?? '').filter(Boolean)))
    }

    const headers: Record<string, string> = {}
    if (resolved.apiKey) headers.authorization = `Bearer ${resolved.apiKey}`
    const response = await this.fetchWithTimeout(this.v1Url(endpoint, 'models'), { method: 'GET', headers }, 6000)
    if (!response.ok) throw new Error(`OPENAI_COMPAT_MODELS_HTTP_${response.status}`)
    const payload = await response.json() as OpenAiModelsResponse
    return Array.from(new Set((payload.data ?? []).map(item => item.id ?? '').filter(Boolean)))
  }

  async chat(
    messages: ProviderMessage[],
    laneId?: AiLaneId
  ): Promise<{ provider: ProviderKind; model: string; content: string }> {
    const cfg = this.resolve(laneId)

    if (cfg.provider === 'local') {
      if (!cfg.localModelPath || !existsSync(cfg.localModelPath)) throw new Error('LOCAL_RAW_LLM_SOURCE_NOT_FOUND')
      throw new Error('LOCAL_RAW_LLM_RUNTIME_NOT_BOUND')
    }

    if (cfg.provider === 'ollama') {
      const status = await this.ollamaStatus(cfg.endpoint, cfg.model)
      if (!status.ready || !status.model) throw new Error('OLLAMA_PROVIDER_NOT_READY')
      const response = await this.fetchWithTimeout(
        `${cfg.endpoint}/api/chat`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ model: status.model, stream: false, messages })
        },
        120000
      )
      if (!response.ok) throw new Error(`OLLAMA_CHAT_HTTP_${response.status}`)
      const payload = await response.json() as OllamaChatResponse
      const content = payload.message?.content?.trim() ?? ''
      if (!content) throw new Error('OLLAMA_CHAT_EMPTY_RESPONSE')
      return { provider: cfg.provider, model: payload.model ?? status.model, content }
    }

    const status = await this.openAiCompatibleStatus(cfg.provider, cfg.endpoint, cfg.model, cfg.apiKey)
    const model = status.model ?? cfg.model
    if (!model) throw new Error('OPENAI_COMPAT_MODEL_NOT_SELECTED')

    const headers: Record<string, string> = { 'content-type': 'application/json' }
    if (cfg.apiKey) headers.authorization = `Bearer ${cfg.apiKey}`
    const response = await this.fetchWithTimeout(
      this.v1Url(cfg.endpoint, 'chat/completions'),
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ model, messages, stream: false })
      },
      120000
    )
    if (!response.ok) throw new Error(`OPENAI_COMPAT_CHAT_HTTP_${response.status}`)
    const payload = await response.json() as OpenAiChatResponse
    const content = payload.choices?.[0]?.message?.content?.trim() ?? ''
    if (!content) throw new Error('OPENAI_COMPAT_CHAT_EMPTY_RESPONSE')
    return { provider: cfg.provider, model: payload.model ?? model, content }
  }

  private resolve(laneId?: AiLaneId): ResolvedProviderConfig {
    if (laneId) return this.settings.resolveLane(laneId)
    const state = this.settings.get()
    return {
      laneId: null,
      source: 'VERA_DEFAULT',
      provider: state.provider,
      endpoint: state.endpoint,
      model: state.model,
      localModelPath: '',
      apiKey: this.settings.apiKey()
    }
  }

  private localStatus(cfg: ResolvedProviderConfig): SessionProviderStatus {
    const source = cfg.localModelPath
    const exists = Boolean(source && existsSync(source))
    const model = source ? basename(source) : cfg.model || null
    return {
      ready: false,
      provider: 'local',
      providerLabel: providerLabel('local'),
      endpoint: '',
      model,
      configuredModel: cfg.model || model || '',
      availableModels: exists && model ? [model] : [],
      detail: exists ? 'Raw local model selected; runtime bridge not attached yet.' : 'Select a local raw LLM file.'
    }
  }

  private async ollamaStatus(endpoint: string, configuredModel: string): Promise<SessionProviderStatus> {
    const response = await this.fetchWithTimeout(`${endpoint}/api/tags`, { method: 'GET' }, 3500)
    if (!response.ok) {
      return {
        ready: false,
        provider: 'ollama',
        providerLabel: providerLabel('ollama'),
        endpoint,
        model: configuredModel || null,
        configuredModel,
        availableModels: [],
        detail: `HTTP ${response.status}`
      }
    }
    const payload = await response.json() as OllamaTagsResponse
    const availableModels = (payload.models ?? []).map(item => item.name ?? item.model ?? '').filter(Boolean)
    const model = configuredModel || availableModels[0] || null
    return {
      ready: Boolean(model && availableModels.includes(model)),
      provider: 'ollama',
      providerLabel: providerLabel('ollama'),
      endpoint,
      model,
      configuredModel,
      availableModels,
      detail: model && !availableModels.includes(model) ? 'Configured model not loaded' : undefined
    }
  }

  private async openAiCompatibleStatus(
    provider: Exclude<ProviderKind, 'ollama' | 'local'>,
    endpoint: string,
    configuredModel: string,
    apiKey?: string
  ): Promise<SessionProviderStatus> {
    const headers: Record<string, string> = {}
    if (apiKey) headers.authorization = `Bearer ${apiKey}`
    const response = await this.fetchWithTimeout(this.v1Url(endpoint, 'models'), { method: 'GET', headers }, 5000)
    if (!response.ok) {
      return {
        ready: false,
        provider,
        providerLabel: providerLabel(provider),
        endpoint,
        model: configuredModel || null,
        configuredModel,
        availableModels: [],
        detail: `HTTP ${response.status}`
      }
    }
    const payload = await response.json() as OpenAiModelsResponse
    const availableModels = (payload.data ?? []).map(item => item.id ?? '').filter(Boolean)
    const model = configuredModel || availableModels[0] || null
    return {
      ready: Boolean(model),
      provider,
      providerLabel: providerLabel(provider),
      endpoint,
      model,
      configuredModel,
      availableModels,
      detail: model && availableModels.length > 0 && !availableModels.includes(model)
        ? 'Configured model not reported by /v1/models'
        : undefined
    }
  }

  private v1Url(endpoint: string, path: string): string {
    const base = endpoint.replace(/\/+$/, '')
    if (/\/v1$/i.test(base)) return `${base}/${path}`
    return `${base}/v1/${path}`
  }

  private async fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), timeoutMs)
    try {
      return await fetch(url, { ...init, signal: controller.signal })
    } finally {
      clearTimeout(timeout)
    }
  }
}
