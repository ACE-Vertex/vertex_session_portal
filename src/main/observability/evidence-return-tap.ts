import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, renameSync, unlinkSync, writeFileSync } from 'node:fs'
import { basename, dirname, join } from 'node:path'
import type { BlackBoxEntry, ObservabilityAnalysis } from './contracts'
import { createObservabilityCoordinator, type ObservabilityCoordinator } from './observability-coordinator'
import { toObservationSupplement } from './observation-sidecar-compat'

export const EVIDENCE_RETURN_OBSERVABILITY_TAP = 'vertex-session-portal/evidence-return-observability-tap-1' as const

type ObservationStatus = 'ABSENT' | 'ATTACHED' | 'REJECTED'
type ObservationSupplement = ReturnType<typeof toObservationSupplement>

export interface EvidenceReturnTapInput {
  raw: unknown
  jobId: string | null
  artifactId: string | null
  evidenceId: string
  originSession: string | null
}

export interface EvidenceReturnTapRecord {
  schema: typeof EVIDENCE_RETURN_OBSERVABILITY_TAP
  status: 'ANALYZED' | 'DEGRADED'
  observedAt: string
  jobId: string | null
  artifactId: string | null
  evidenceId: string
  originSession: string | null
  observationStatus: ObservationStatus
  observationSupplement: ObservationSupplement
  analysis: ObservabilityAnalysis | null
  blackBoxTail: Pick<BlackBoxEntry, 'sequence' | 'timestamp' | 'channel' | 'sha256'> | null
  error: string | null
}

function boundedError(error: unknown): string {
  const text = error instanceof Error ? `${error.name}:${error.message}` : String(error)
  return text.length <= 4096 ? text : `${text.slice(0, 4096)}…<TRUNCATED>`
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}

function extractObservationReference(raw: unknown): unknown | null {
  const root = asRecord(raw)
  if (!root) return null

  // Canonical Workstation HTTP response:
  // raw.evidence.envelope.evidence.observation_reference
  const responseEvidence = asRecord(root.evidence)
  const envelope =
    asRecord(responseEvidence?.envelope) ??
    asRecord(root.envelope)

  const executionEvidence =
    asRecord(envelope?.evidence) ??
    (
      responseEvidence && (
        'observation_reference' in responseEvidence ||
        'observationReference' in responseEvidence
      )
        ? responseEvidence
        : null
    )

  if (!executionEvidence) return null

  return executionEvidence.observation_reference ??
    executionEvidence.observationReference ??
    null
}

function resolveObservation(raw: unknown): {
  status: ObservationStatus
  supplement: ObservationSupplement
} {
  const reference = extractObservationReference(raw)
  if (reference === null || reference === undefined) {
    return { status: 'ABSENT', supplement: null }
  }

  try {
    const supplement = toObservationSupplement(reference)
    return supplement
      ? { status: 'ATTACHED', supplement }
      : { status: 'REJECTED', supplement: null }
  } catch {
    // Observation is additive only. A malformed optional reference must never
    // block canonical Evidence routing, delivery, or ACK.
    return { status: 'REJECTED', supplement: null }
  }
}

export class EvidenceReturnObservabilityTap {
  private readonly coordinator: ObservabilityCoordinator
  private readonly cacheRoot: string

  constructor(stagingRoot: string, worksIncomingRoot: string) {
    const developmentRoot = dirname(worksIncomingRoot)
    const workstationLanes = join(developmentRoot, 'vertex_workstation', 'runtime', 'lanes')
    this.coordinator = createObservabilityCoordinator([workstationLanes])
    this.cacheRoot = join(stagingRoot, 'observability', 'evidence')
  }

  async observeAndPersist(input: EvidenceReturnTapInput): Promise<EvidenceReturnTapRecord> {
    const existing = this.readExisting(input)
    if (existing) return existing

    const observedAt = new Date().toISOString()
    const observation = resolveObservation(input.raw)

    if (observation.status === 'ATTACHED') {
      this.coordinator.blackBox.append('WORKSTATION_OBSERVATION_ATTACHED', {
        evidenceId: input.evidenceId,
        jobId: input.jobId,
        artifactId: input.artifactId
      })
    } else if (observation.status === 'REJECTED') {
      this.coordinator.blackBox.append('WORKSTATION_OBSERVATION_REJECTED', {
        evidenceId: input.evidenceId,
        jobId: input.jobId,
        artifactId: input.artifactId
      })
    }

    let record: EvidenceReturnTapRecord
    try {
      if (!input.jobId || !input.artifactId || !input.originSession) {
        throw new Error('OBSERVABILITY_EVIDENCE_IDENTITY_INCOMPLETE')
      }

      const analysis = await this.coordinator.analyzeWorkstationEvidence(input.raw)
      const tail = this.coordinator.blackBox.snapshot().at(-1) ?? null

      record = {
        schema: EVIDENCE_RETURN_OBSERVABILITY_TAP,
        status: 'ANALYZED',
        observedAt,
        jobId: input.jobId,
        artifactId: input.artifactId,
        evidenceId: input.evidenceId,
        originSession: input.originSession,
        observationStatus: observation.status,
        observationSupplement: observation.supplement,
        analysis,
        blackBoxTail: tail ? {
          sequence: tail.sequence,
          timestamp: tail.timestamp,
          channel: tail.channel,
          sha256: tail.sha256
        } : null,
        error: null
      }
    } catch (error) {
      const message = boundedError(error)
      const tail = this.coordinator.blackBox.append('EVIDENCE_RETURN_TAP_DEGRADED', {
        evidenceId: input.evidenceId,
        jobId: input.jobId,
        error: message
      })

      record = {
        schema: EVIDENCE_RETURN_OBSERVABILITY_TAP,
        status: 'DEGRADED',
        observedAt,
        jobId: input.jobId,
        artifactId: input.artifactId,
        evidenceId: input.evidenceId,
        originSession: input.originSession,
        observationStatus: observation.status,
        observationSupplement: observation.supplement,
        analysis: null,
        blackBoxTail: {
          sequence: tail.sequence,
          timestamp: tail.timestamp,
          channel: tail.channel,
          sha256: tail.sha256
        },
        error: message
      }
    }

    // Observability is non-authoritative. A persistence error must never block
    // exact-origin canonical Evidence return or the existing ACK state machine.
    try {
      this.writeAtomic(this.pathFor(input.evidenceId), record)
    } catch {
      // Black Box still retains the in-process observation.
      // Existing Evidence routing remains authoritative.
    }

    return record
  }

  readByEvidenceId(evidenceId: string): EvidenceReturnTapRecord | null {
    const safeId = evidenceId.trim()
    if (!safeId) return null

    try {
      const value = JSON.parse(readFileSync(this.pathFor(safeId), 'utf8')) as EvidenceReturnTapRecord
      return value?.schema === EVIDENCE_RETURN_OBSERVABILITY_TAP && value.evidenceId === safeId
        ? value
        : null
    } catch {
      return null
    }
  }

  private readExisting(input: EvidenceReturnTapInput): EvidenceReturnTapRecord | null {
    const existing = this.readByEvidenceId(input.evidenceId)
    if (!existing) return null

    if (
      existing.jobId !== input.jobId ||
      existing.artifactId !== input.artifactId ||
      existing.originSession !== input.originSession
    ) {
      return null
    }

    return existing
  }

  private pathFor(evidenceId: string): string {
    const digest = createHash('sha256').update(evidenceId).digest('hex')
    return join(this.cacheRoot, `${digest}.json`)
  }

  private writeAtomic(path: string, value: EvidenceReturnTapRecord): void {
    mkdirSync(dirname(path), { recursive: true })
    const temp = join(dirname(path), `.${basename(path)}.${process.pid}.${Date.now()}.tmp`)

    try {
      writeFileSync(temp, JSON.stringify(value, null, 2), 'utf8')
      renameSync(temp, path)
    } finally {
      if (existsSync(temp)) {
        try { unlinkSync(temp) } catch { /* best effort */ }
      }
    }
  }
}
