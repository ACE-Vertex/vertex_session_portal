import Database from 'better-sqlite3'
import { safeStorage } from 'electron'
import type {
  AiLaneId,
  AiLaneOverrideState,
  AiLaneSettingsState,
  AiLaneState,
  ProviderKind,
  ProviderSettingsState,
  SaveAiLaneSettingsRequest,
  SaveProviderSettingsRequest
} from '../../shared/contracts'

interface ProviderSettingsRow {
  provider: ProviderKind
  endpoint: string
  model: string
  updatedUtc: string
}

interface LaneSettingsRow {
  laneId: AiLaneId
  provider: ProviderKind
  endpoint: string
  model: string
  localModelPath: string
  updatedUtc: string
}

export interface ResolvedProviderConfig {
  laneId: AiLaneId | null
  source: 'VERA_DEFAULT' | 'LANE_OVERRIDE'
  provider: ProviderKind
  endpoint: string
  model: string
  localModelPath: string
  apiKey?: string
}

const laneDefinitions: Array<{ laneId: AiLaneId; label: string; sessionId: string | null }> = [
  { laneId: 'lane-1', label: 'LANE 1', sessionId: 'vera-01' },
  { laneId: 'lane-2', label: 'LANE 2', sessionId: 'vera-02' },
  { laneId: 'lane-3', label: 'LANE 3', sessionId: 'vera-03' },
  { laneId: 'lane-4', label: 'LANE 4', sessionId: 'vera-04' },
  { laneId: 'lane-5', label: 'LANE 5', sessionId: 'vera-05' }
]

const providerLabels: Record<ProviderKind, string> = {
  ollama: 'Ollama',
  lmstudio: 'LM Studio',
  openai: 'OpenAI',
  'openai-compatible': 'OpenAI Compatible',
  local: 'Local Raw LLM'
}

const providerEndpoints: Record<ProviderKind, string> = {
  ollama: 'http://127.0.0.1:11434',
  lmstudio: 'http://127.0.0.1:1234',
  openai: 'https://api.openai.com',
  'openai-compatible': 'http://127.0.0.1:8000',
  local: ''
}

export function providerLabel(provider: ProviderKind): string {
  return providerLabels[provider]
}

export function defaultProviderEndpoint(provider: ProviderKind): string {
  return providerEndpoints[provider]
}

export function sessionLaneId(sessionId: string): AiLaneId | null {
  const direct = laneDefinitions.find(item => item.sessionId === sessionId)
  return direct?.laneId ?? null
}

export class ProviderSettingsStore {
  private readonly db: Database.Database

  constructor(filePath: string) {
    this.db = new Database(filePath)
    this.db.pragma('journal_mode = WAL')
    this.initialize()
  }

  private initialize(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS provider_settings (
        singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
        provider TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        model TEXT NOT NULL,
        updated_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS provider_secret (
        provider TEXT PRIMARY KEY,
        api_key_encrypted BLOB NOT NULL,
        updated_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS provider_lane_settings (
        lane_id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        endpoint TEXT NOT NULL DEFAULT '',
        model TEXT NOT NULL DEFAULT '',
        local_model_path TEXT NOT NULL DEFAULT '',
        updated_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS provider_lane_secret (
        lane_id TEXT PRIMARY KEY,
        api_key_encrypted BLOB NOT NULL,
        updated_utc TEXT NOT NULL
      );
    `)

    this.db.prepare(`
      INSERT OR IGNORE INTO provider_settings
      (singleton_id, provider, endpoint, model, updated_utc)
      VALUES (1, 'ollama', 'http://127.0.0.1:11434', 'qwen3:8b', ?)
    `).run(new Date().toISOString())
  }

  get(): ProviderSettingsState {
    const row = this.db.prepare(`
      SELECT
        provider,
        endpoint,
        model,
        updated_utc AS updatedUtc
      FROM provider_settings
      WHERE singleton_id = 1
    `).get() as ProviderSettingsRow

    const provider = this.normalizeProvider(row.provider)
    const stored = this.db.prepare(`
      SELECT 1
      FROM provider_secret
      WHERE provider = ?
    `).get(provider)

    const envKey = this.environmentKey(provider)
    const apiKeySource: ProviderSettingsState['apiKeySource'] =
      stored ? 'STORED' : envKey ? 'ENV' : 'NONE'

    return {
      provider,
      endpoint: row.endpoint,
      model: row.model,
      hasApiKey: Boolean(stored || envKey),
      apiKeySource,
      encryptionAvailable: safeStorage.isEncryptionAvailable(),
      updatedUtc: row.updatedUtc
    }
  }

  save(request: SaveProviderSettingsRequest): ProviderSettingsState {
    const provider = this.normalizeProvider(request.provider)
    const endpoint = provider === 'local'
      ? ''
      : this.requireText(request.endpoint, 'PROVIDER_ENDPOINT', 2048).replace(/\/+$/, '')
    const model = this.requireText(request.model, 'PROVIDER_MODEL', 512)
    const now = new Date().toISOString()

    this.db.prepare(`
      INSERT INTO provider_settings
      (singleton_id, provider, endpoint, model, updated_utc)
      VALUES (1, ?, ?, ?, ?)
      ON CONFLICT(singleton_id)
      DO UPDATE SET
        provider = excluded.provider,
        endpoint = excluded.endpoint,
        model = excluded.model,
        updated_utc = excluded.updated_utc
    `).run(provider, endpoint, model, now)

    const key = request.apiKey?.trim() ?? ''
    if (key) this.saveDefaultSecret(provider, key, now)

    return this.get()
  }

  clearApiKey(): ProviderSettingsState {
    const provider = this.get().provider
    this.db.prepare('DELETE FROM provider_secret WHERE provider = ?').run(provider)
    return this.get()
  }

  apiKey(): string | undefined {
    const state = this.get()
    return this.defaultApiKey(state.provider)
  }

  getAiLaneSettings(): AiLaneSettingsState {
    const veraDefault = this.get()
    return {
      veraDefault,
      lanes: laneDefinitions.map(definition => this.buildLaneState(definition, veraDefault))
    }
  }

  saveLane(request: SaveAiLaneSettingsRequest): AiLaneSettingsState {
    const laneId = this.normalizeLaneId(request.laneId)
    if (!request.provider) {
      this.db.prepare('DELETE FROM provider_lane_settings WHERE lane_id = ?').run(laneId)
      this.db.prepare('DELETE FROM provider_lane_secret WHERE lane_id = ?').run(laneId)
      return this.getAiLaneSettings()
    }

    const provider = this.normalizeProvider(request.provider)
    const endpoint = provider === 'local'
      ? ''
      : (request.endpoint?.trim() || defaultProviderEndpoint(provider)).replace(/\/+$/, '')
    const localModelPath = provider === 'local' ? (request.localModelPath?.trim() ?? '') : ''
    const model = request.model?.trim() ?? ''
    const now = new Date().toISOString()

    if (provider !== 'local' && !endpoint) throw new Error('LANE_PROVIDER_ENDPOINT_EMPTY')
    if (provider === 'local' && !localModelPath) throw new Error('LANE_LOCAL_MODEL_PATH_EMPTY')

    this.db.prepare(`
      INSERT INTO provider_lane_settings
      (lane_id, provider, endpoint, model, local_model_path, updated_utc)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(lane_id)
      DO UPDATE SET
        provider = excluded.provider,
        endpoint = excluded.endpoint,
        model = excluded.model,
        local_model_path = excluded.local_model_path,
        updated_utc = excluded.updated_utc
    `).run(laneId, provider, endpoint, model, localModelPath, now)

    const key = request.apiKey?.trim() ?? ''
    if (key) this.saveLaneSecret(laneId, key, now)

    return this.getAiLaneSettings()
  }

  clearLaneApiKey(laneIdInput: AiLaneId): AiLaneSettingsState {
    const laneId = this.normalizeLaneId(laneIdInput)
    this.db.prepare('DELETE FROM provider_lane_secret WHERE lane_id = ?').run(laneId)
    return this.getAiLaneSettings()
  }

  resolveLane(laneIdInput: AiLaneId): ResolvedProviderConfig {
    const laneId = this.normalizeLaneId(laneIdInput)
    const row = this.readLane(laneId)
    if (!row) {
      const state = this.get()
      return {
        laneId,
        source: 'VERA_DEFAULT',
        provider: state.provider,
        endpoint: state.endpoint,
        model: state.model,
        localModelPath: '',
        apiKey: this.defaultApiKey(state.provider)
      }
    }

    const provider = this.normalizeProvider(row.provider)
    return {
      laneId,
      source: 'LANE_OVERRIDE',
      provider,
      endpoint: row.endpoint,
      model: row.model,
      localModelPath: row.localModelPath,
      apiKey: this.laneApiKey(laneId, provider)
    }
  }

  close(): void {
    this.db.close()
  }

  private buildLaneState(
    definition: { laneId: AiLaneId; label: string; sessionId: string | null },
    veraDefault: ProviderSettingsState
  ): AiLaneState {
    const row = this.readLane(definition.laneId)
    if (!row) {
      return {
        laneId: definition.laneId,
        label: definition.label,
        sessionId: definition.sessionId,
        fallbackToVera: true,
        override: null,
        resolvedProvider: veraDefault.provider,
        resolvedEndpoint: veraDefault.endpoint,
        resolvedModel: veraDefault.model,
        resolvedLocalModelPath: ''
      }
    }

    const provider = this.normalizeProvider(row.provider)
    const stored = this.db.prepare('SELECT 1 FROM provider_lane_secret WHERE lane_id = ?').get(definition.laneId)
    const envKey = this.environmentKey(provider)
    const apiKeySource: AiLaneOverrideState['apiKeySource'] = stored ? 'STORED' : envKey ? 'ENV' : 'NONE'
    const override: AiLaneOverrideState = {
      laneId: definition.laneId,
      provider,
      endpoint: row.endpoint,
      model: row.model,
      localModelPath: row.localModelPath,
      hasApiKey: Boolean(stored || envKey),
      apiKeySource,
      encryptionAvailable: safeStorage.isEncryptionAvailable(),
      updatedUtc: row.updatedUtc
    }

    return {
      laneId: definition.laneId,
      label: definition.label,
      sessionId: definition.sessionId,
      fallbackToVera: false,
      override,
      resolvedProvider: provider,
      resolvedEndpoint: row.endpoint,
      resolvedModel: row.model,
      resolvedLocalModelPath: row.localModelPath
    }
  }

  private readLane(laneId: AiLaneId): LaneSettingsRow | undefined {
    return this.db.prepare(`
      SELECT
        lane_id AS laneId,
        provider,
        endpoint,
        model,
        local_model_path AS localModelPath,
        updated_utc AS updatedUtc
      FROM provider_lane_settings
      WHERE lane_id = ?
    `).get(laneId) as LaneSettingsRow | undefined
  }

  private saveDefaultSecret(provider: ProviderKind, key: string, now: string): void {
    if (!safeStorage.isEncryptionAvailable()) throw new Error('PROVIDER_API_KEY_ENCRYPTION_UNAVAILABLE')
    const encrypted = safeStorage.encryptString(key)
    this.db.prepare(`
      INSERT INTO provider_secret
      (provider, api_key_encrypted, updated_utc)
      VALUES (?, ?, ?)
      ON CONFLICT(provider)
      DO UPDATE SET api_key_encrypted = excluded.api_key_encrypted, updated_utc = excluded.updated_utc
    `).run(provider, encrypted, now)
  }

  private saveLaneSecret(laneId: AiLaneId, key: string, now: string): void {
    if (!safeStorage.isEncryptionAvailable()) throw new Error('PROVIDER_API_KEY_ENCRYPTION_UNAVAILABLE')
    const encrypted = safeStorage.encryptString(key)
    this.db.prepare(`
      INSERT INTO provider_lane_secret
      (lane_id, api_key_encrypted, updated_utc)
      VALUES (?, ?, ?)
      ON CONFLICT(lane_id)
      DO UPDATE SET api_key_encrypted = excluded.api_key_encrypted, updated_utc = excluded.updated_utc
    `).run(laneId, encrypted, now)
  }

  private defaultApiKey(provider: ProviderKind): string | undefined {
    const row = this.db.prepare(`
      SELECT api_key_encrypted AS encrypted
      FROM provider_secret
      WHERE provider = ?
    `).get(provider) as { encrypted: Buffer } | undefined

    if (row && safeStorage.isEncryptionAvailable()) return safeStorage.decryptString(row.encrypted)
    return this.environmentKey(provider)
  }

  private laneApiKey(laneId: AiLaneId, provider: ProviderKind): string | undefined {
    const row = this.db.prepare(`
      SELECT api_key_encrypted AS encrypted
      FROM provider_lane_secret
      WHERE lane_id = ?
    `).get(laneId) as { encrypted: Buffer } | undefined

    if (row && safeStorage.isEncryptionAvailable()) return safeStorage.decryptString(row.encrypted)
    return this.environmentKey(provider)
  }

  private environmentKey(provider: ProviderKind): string | undefined {
    if (provider === 'openai') return process.env.OPENAI_API_KEY ?? process.env.VERTEX_PROVIDER_API_KEY
    if (provider === 'local') return undefined
    return process.env.VERTEX_PROVIDER_API_KEY
  }

  private normalizeLaneId(value: unknown): AiLaneId {
    if (value === 'lane-1' || value === 'lane-2' || value === 'lane-3' || value === 'lane-4' || value === 'lane-5') return value
    throw new Error('AI_LANE_ID_INVALID')
  }

  private normalizeProvider(value: unknown): ProviderKind {
    if (value === 'ollama' || value === 'lmstudio' || value === 'openai' || value === 'openai-compatible' || value === 'local') return value
    throw new Error('PROVIDER_KIND_INVALID')
  }

  private requireText(value: unknown, label: string, maxLength: number): string {
    if (typeof value !== 'string') throw new Error(`${label}_NOT_STRING`)
    const text = value.trim()
    if (!text) throw new Error(`${label}_EMPTY`)
    if (text.length > maxLength) throw new Error(`${label}_TOO_LONG`)
    return text
  }
}
