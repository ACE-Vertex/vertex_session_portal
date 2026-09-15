import type {
  SessionProviderStatus
} from '../../shared/contracts'

export interface ProviderMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

interface OllamaTagsResponse {
  models?: Array<{
    name?: string
    model?: string
  }>
}

interface OllamaChatResponse {
  model?: string
  message?: {
    role?: string
    content?: string
  }
}

export class OllamaProvider {
  readonly endpoint: string

  constructor(
    endpoint =
      process.env.VERTEX_OLLAMA_ENDPOINT ??
      'http://127.0.0.1:11434'
  ) {
    this.endpoint =
      endpoint.replace(/\/+$/, '')
  }

  async status():
    Promise<SessionProviderStatus> {
    try {
      const response =
        await this.fetchWithTimeout(
          `${this.endpoint}/api/tags`,
          {
            method: 'GET'
          },
          3500
        )

      if (!response.ok) {
        return {
          ready: false,
          provider: 'ollama',
          providerLabel: 'Ollama',
          endpoint: this.endpoint,
          model: null,
          configuredModel: process.env.VERTEX_OLLAMA_MODEL ?? 'qwen3:8b',
          availableModels: []
        }
      }

      const payload =
        await response.json() as
          OllamaTagsResponse

      const availableModels =
        (payload.models ?? [])
          .map(
            (item) =>
              item.name ??
              item.model ??
              ''
          )
          .filter(Boolean)

      const requested =
        process.env
          .VERTEX_OLLAMA_MODEL

      const preferred =
        requested &&
        availableModels
          .includes(requested)
          ? requested
          : availableModels
              .find(
                (name) =>
                  name === 'qwen3:8b'
              ) ??
            availableModels[0] ??
            null

      return {
        ready:
          Boolean(preferred),
        provider: 'ollama',
        providerLabel: 'Ollama',
        endpoint: this.endpoint,
        model: preferred,
        configuredModel: requested ?? 'qwen3:8b',
        availableModels
      }
    } catch {
      return {
        ready: false,
        provider: 'ollama',
        providerLabel: 'Ollama',
        endpoint: this.endpoint,
        model: null,
        configuredModel: process.env.VERTEX_OLLAMA_MODEL ?? 'qwen3:8b',
        availableModels: []
      }
    }
  }

  async chat(
    messages: ProviderMessage[]
  ): Promise<{
    model: string
    content: string
  }> {
    const status =
      await this.status()

    if (
      !status.ready ||
      !status.model
    ) {
      throw new Error(
        'OLLAMA_PROVIDER_NOT_READY'
      )
    }

    const response =
      await this.fetchWithTimeout(
        `${this.endpoint}/api/chat`,
        {
          method: 'POST',
          headers: {
            'content-type':
              'application/json'
          },
          body: JSON.stringify({
            model: status.model,
            stream: false,
            messages
          })
        },
        120000
      )

    if (!response.ok) {
      throw new Error(
        `OLLAMA_CHAT_HTTP_${response.status}`
      )
    }

    const payload =
      await response.json() as
        OllamaChatResponse

    const content =
      payload.message
        ?.content
        ?.trim() ?? ''

    if (!content) {
      throw new Error(
        'OLLAMA_CHAT_EMPTY_RESPONSE'
      )
    }

    return {
      model:
        payload.model ??
        status.model,
      content
    }
  }

  private async fetchWithTimeout(
    url: string,
    init: RequestInit,
    timeoutMs: number
  ): Promise<Response> {
    const controller =
      new AbortController()

    const timeout =
      setTimeout(
        () =>
          controller.abort(),
        timeoutMs
      )

    try {
      return await fetch(
        url,
        {
          ...init,
          signal:
            controller.signal
        }
      )
    } finally {
      clearTimeout(timeout)
    }
  }
}
