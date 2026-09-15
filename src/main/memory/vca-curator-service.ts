import type {
  AiLaneId,
  AppendVcaWeightRevisionRequest,
  ProviderKind,
  RunVcaCuratorRequest,
  VcaCuratorMode,
  VcaCuratorRunResult,
  VcaCuratorState,
  VcaRecord,
  VcaWeightDimensions
} from '../../shared/contracts'
import { ConfiguredProvider, type ProviderMessage } from '../providers/configured-provider'
import { ProviderSettingsStore } from '../providers/provider-settings-store'
import { WorkstationDb } from '../storage/workstation-db'

interface CuratorItem extends VcaWeightDimensions {
  eventId: string
  rationale: string
}

interface CuratorPayload {
  items?: CuratorItem[]
}

export class VcaCuratorService {
  private scheduled: NodeJS.Timeout | null = null
  private running = false

  constructor(
    private readonly db: WorkstationDb,
    private readonly providerSettings: ProviderSettingsStore,
    private readonly provider: ConfiguredProvider
  ) {}

  async state(): Promise<VcaCuratorState> {
    const settings = this.db.getVcaCuratorSettings()
    const lanes = this.providerSettings.getAiLaneSettings().lanes
    const lane = lanes.find(item => item.laneId === settings.laneId)
    const pendingCount = this.db.countVcaCuratorPending()

    if (!lane?.override) {
      return {
        settings,
        configured: false,
        ready: false,
        provider: null,
        model: null,
        pendingCount,
        detail: `${settings.laneId.toUpperCase()} has no dedicated AI Assistant. Curator will not fall back to another model.`
      }
    }

    const status = await this.provider.status(settings.laneId)
    return {
      settings,
      configured: true,
      ready: status.ready,
      provider: lane.override.provider,
      model: (status.model ?? lane.override.model) || null,
      pendingCount,
      detail: status.ready
        ? `VCA Curator ready on ${settings.laneId.toUpperCase()} / ${status.providerLabel} / ${status.model ?? lane.override.model}`
        : status.detail ?? 'Configured AI Assistant is not ready.'
    }
  }

  saveSettings(request: import('../../shared/contracts').SaveVcaCuratorSettingsRequest): Promise<VcaCuratorState> {
    this.db.saveVcaCuratorSettings(request)
    return this.state()
  }

  start(): void {
    this.schedule('STARTUP')
  }

  stop(): void {
    if (this.scheduled) clearTimeout(this.scheduled)
    this.scheduled = null
  }

  schedule(_reason: string): void {
    const settings = this.db.getVcaCuratorSettings()
    if (!settings.autoRun || this.running || this.scheduled) return

    this.scheduled = setTimeout(() => {
      this.scheduled = null
      void this.run({ mode: 'PENDING', limit: settings.batchSize }).catch((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error)
        console.warn(`[VCA_CURATOR_AUTO] ${message}`)
      })
    }, 650)
  }

  async run(request: RunVcaCuratorRequest = {}): Promise<VcaCuratorRunResult> {
    if (this.running) throw new Error('VCA_CURATOR_BUSY')
    this.running = true
    try {
      return await this.runInternal(request)
    } finally {
      this.running = false
    }
  }

  private async runInternal(request: RunVcaCuratorRequest): Promise<VcaCuratorRunResult> {
    const startedUtc = new Date().toISOString()
    const settings = this.db.getVcaCuratorSettings()
    const mode: VcaCuratorMode = request.mode === 'REEVALUATE' ? 'REEVALUATE' : 'PENDING'
    const requestedLimit = request.limit ?? settings.batchSize
    const limit = Math.min(Math.max(Math.trunc(requestedLimit), 1), 24)
    const lanes = this.providerSettings.getAiLaneSettings().lanes
    const lane = lanes.find(item => item.laneId === settings.laneId)

    if (!lane?.override) {
      return this.emptyResult(mode, settings.laneId, startedUtc, 'NO_ASSISTANT_CONFIGURED', false)
    }

    const status = await this.provider.status(settings.laneId)
    if (!status.ready) {
      return this.emptyResult(
        mode,
        settings.laneId,
        startedUtc,
        status.detail ?? 'ASSISTANT_NOT_READY',
        true,
        lane.override.provider,
        (status.model ?? lane.override.model) || null
      )
    }

    const candidates = this.db.listVcaCuratorCandidates(mode, limit)
    if (candidates.length === 0) {
      return {
        mode,
        laneId: settings.laneId,
        configured: true,
        provider: lane.override.provider,
        model: (status.model ?? lane.override.model) || null,
        candidateCount: 0,
        processed: 0,
        skipped: 0,
        failures: [],
        startedUtc,
        finishedUtc: new Date().toISOString()
      }
    }

    const messages = this.buildPrompt(candidates, settings.laneId)
    const response = await this.provider.chat(messages, settings.laneId)
    const payload = this.parsePayload(response.content)
    const allowed = new Map(candidates.map(item => [item.id, item]))
    const seen = new Set<string>()
    const failures: string[] = []
    let processed = 0
    let skipped = 0

    for (const item of payload.items ?? []) {
      if (!item || typeof item.eventId !== 'string' || !allowed.has(item.eventId) || seen.has(item.eventId)) {
        skipped += 1
        continue
      }

      seen.add(item.eventId)
      try {
        const revision: AppendVcaWeightRevisionRequest = {
          eventId: item.eventId,
          humanSignal: this.dimension(item.humanSignal),
          veraSignal: this.dimension(item.veraSignal),
          mutualSignal: this.dimension(item.mutualSignal),
          purposeRelation: this.dimension(item.purposeRelation),
          implementationLink: this.dimension(item.implementationLink),
          recurrence: this.dimension(item.recurrence),
          novelty: this.dimension(item.novelty),
          confidence: this.dimension(item.confidence),
          curator: `AI_ASSISTANT:${settings.laneId}:${response.provider}:${response.model}`,
          rationale: this.rationale(item.rationale)
        }
        this.db.appendVcaWeightRevision(revision)
        this.db.markVcaInboxCuratedByEvent(item.eventId)
        processed += 1
      } catch (error: unknown) {
        failures.push(`${item.eventId}:${error instanceof Error ? error.message : String(error)}`)
      }
    }

    skipped += Math.max(0, candidates.length - seen.size)

    return {
      mode,
      laneId: settings.laneId,
      configured: true,
      provider: response.provider,
      model: response.model,
      candidateCount: candidates.length,
      processed,
      skipped,
      failures,
      startedUtc,
      finishedUtc: new Date().toISOString()
    }
  }

  private buildPrompt(candidates: VcaRecord[], laneId: AiLaneId): ProviderMessage[] {
    const highGravity = this.db.searchVca('', 12)
      .filter(record => !candidates.some(candidate => candidate.id === record.id))
      .slice(0, 8)
      .map(record => ({
        eventId: record.id,
        gravity: record.memoryGravity,
        actor: record.actor,
        body: record.body.slice(0, 900)
      }))

    const canonical = this.db.searchVcr('', 12).map(item => ({
      key: item.key,
      title: item.title,
      status: item.status,
      body: item.body.slice(0, 700)
    }))

    const candidatePayload = candidates.map(record => ({
      eventId: record.id,
      memoryRevision: record.memoryRevision,
      session: record.sessionTitle,
      actor: record.actor,
      sourceKind: record.sourceKind,
      body: record.body.slice(0, 5000),
      current: {
        humanSignal: record.humanSignal,
        veraSignal: record.veraSignal,
        mutualSignal: record.mutualSignal,
        purposeRelation: record.purposeRelation,
        implementationLink: record.implementationLink,
        recurrence: record.recurrence,
        novelty: record.novelty,
        confidence: record.confidence,
        gravity: record.memoryGravity,
        curator: record.curator
      }
    }))

    return [
      {
        role: 'system',
        content: [
          'You are the VERTEX VCA Memory Curator, a dedicated AI Assistant beneath Vera.',
          `You are operating through ${laneId.toUpperCase()}; you are not Vera and must not impersonate Vera.`,
          'Evaluate conversation memories for long-term retrieval gravity.',
          'Human and Vera are peer speakers. Never grant priority merely because the speaker is HUMAN or VERA.',
          'Do not reduce importance merely because a memory is old. Age alone is not decay.',
          'Score every dimension from 0 to 100.',
          'purposeRelation means connection to goals, original intent, canonical direction, identity or design philosophy.',
          'implementationLink means demonstrated relation to code, VRA, Works, Evidence, build, decisions or delivered artifacts.',
          'mutualSignal is high when Human and Vera jointly reinforce, adopt or build upon the same idea.',
          'recurrence is high when the idea connects strongly to repeated or already-important memories.',
          'Return JSON only. No markdown and no commentary.',
          'Schema: {"items":[{"eventId":"...","humanSignal":0,"veraSignal":0,"mutualSignal":0,"purposeRelation":0,"implementationLink":0,"recurrence":0,"novelty":0,"confidence":0,"rationale":"short reason"}]}',
          'Return exactly one item for every supplied candidate eventId and never invent an eventId.'
        ].join('\n')
      },
      {
        role: 'user',
        content: JSON.stringify({
          canonicalReference: canonical,
          highGravityReference: highGravity,
          candidates: candidatePayload
        })
      }
    ]
  }

  private parsePayload(content: string): CuratorPayload {
    let text = content.trim()
    if (text.startsWith('```')) {
      text = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
    }

    const first = text.indexOf('{')
    const last = text.lastIndexOf('}')
    if (first >= 0 && last > first) text = text.slice(first, last + 1)

    const parsed = JSON.parse(text) as CuratorPayload
    if (!parsed || !Array.isArray(parsed.items)) throw new Error('VCA_CURATOR_RESPONSE_SCHEMA_INVALID')
    return parsed
  }

  private dimension(value: unknown): number {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('VCA_CURATOR_DIMENSION_INVALID')
    return Math.max(0, Math.min(100, Math.round(value * 100) / 100))
  }

  private rationale(value: unknown): string {
    if (typeof value !== 'string') return 'AI Assistant memory-gravity reevaluation.'
    const text = value.trim()
    return (text || 'AI Assistant memory-gravity reevaluation.').slice(0, 2000)
  }

  private emptyResult(
    mode: VcaCuratorMode,
    laneId: AiLaneId,
    startedUtc: string,
    reason: string,
    configured = false,
    provider: ProviderKind | null = null,
    model: string | null = null
  ): VcaCuratorRunResult {
    return {
      mode,
      laneId,
      configured,
      provider,
      model,
      candidateCount: 0,
      processed: 0,
      skipped: 0,
      failures: [reason],
      startedUtc,
      finishedUtc: new Date().toISOString()
    }
  }
}
