import { app } from 'electron'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { vertexObservability } from './vertex-observability-core'

type JsonRecord = Record<string, unknown>

type CardSnapshot = {
  id: string
  artifactId: string | null
  jobId: string | null
  correlationId: string | null
  originVera: string | null
  originSession: string | null
  originWindow: string | null
  humanApproval: string | null
  dispatchPhase: string | null
  status: string | null
  requestedLane: string | null
  lanePolicy: string | null
  allocatedLane: string | null
  workstationRegistration: string | null
  workstationJobState: string | null
  workstationEvidenceState: string | null
  workstationEvidenceReturnState: string | null
  evidenceIdentity: string | null
}

const POLL_MS = 800
let started = false
let initialized = false
let timer: NodeJS.Timeout | null = null
let lastReadError = ''
const previous = new Map<string, CardSnapshot>()

function asRecord(value: unknown): JsonRecord | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as JsonRecord
    : null
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null
}

function field(card: JsonRecord, camel: string, snake: string): unknown {
  return card[camel] ?? card[snake]
}

function snapshot(card: JsonRecord): CardSnapshot | null {
  const id = asString(field(card, 'id', 'id'))
  if (!id) return null

  return {
    id,
    artifactId: asString(field(card, 'artifactId', 'artifact_id')),
    jobId: asString(field(card, 'jobId', 'job_id')),
    correlationId: asString(field(card, 'correlationId', 'correlation_id')),
    originVera: asString(field(card, 'originVera', 'origin_vera')),
    originSession: asString(field(card, 'originSession', 'origin_session'))
      ?? asString(field(card, 'sourceSessionId', 'source_session_id')),
    originWindow: asString(field(card, 'originWindow', 'origin_window')),
    humanApproval: asString(field(card, 'humanApproval', 'human_approval')),
    dispatchPhase: asString(field(card, 'dispatchPhase', 'dispatch_phase')),
    status: asString(field(card, 'status', 'status')),
    requestedLane: asString(field(card, 'requestedLane', 'requested_lane')),
    lanePolicy: asString(field(card, 'lanePolicy', 'lane_policy')),
    allocatedLane: asString(field(card, 'allocatedLane', 'allocated_lane')),
    workstationRegistration: asString(field(card, 'workstationRegistration', 'workstation_registration')),
    workstationJobState: asString(field(card, 'workstationJobState', 'workstation_job_state')),
    workstationEvidenceState: asString(field(card, 'workstationEvidenceState', 'workstation_evidence_state')),
    workstationEvidenceReturnState: asString(field(card, 'workstationEvidenceReturnState', 'workstation_evidence_return_state')),
    evidenceIdentity: asString(field(card, 'evidenceIdentity', 'evidence_identity')),
  }
}

function cardsFromLedger(raw: unknown): JsonRecord[] {
  if (Array.isArray(raw)) {
    return raw.map(asRecord).filter((x): x is JsonRecord => x !== null)
  }
  const root = asRecord(raw)
  if (!root) return []

  for (const candidate of [root.cards, asRecord(root.state)?.cards, asRecord(root.data)?.cards]) {
    if (Array.isArray(candidate)) {
      return candidate.map(asRecord).filter((x): x is JsonRecord => x !== null)
    }
  }
  return []
}

function context(card: CardSnapshot) {
  return {
    ...(card.correlationId ? { correlation_id: card.correlationId } : {}),
    ...(card.originSession ? { session_id: card.originSession } : {}),
    ...(card.jobId ? { job_id: card.jobId } : {}),
    ...(card.allocatedLane ? { lane_id: card.allocatedLane } : {}),
  }
}

function safePayload(card: CardSnapshot): JsonRecord {
  return {
    card_id: card.id,
    artifact_id: card.artifactId,
    origin_vera: card.originVera,
    origin_window: card.originWindow,
    human_approval: card.humanApproval,
    dispatch_phase: card.dispatchPhase,
    status: card.status,
    requested_lane: card.requestedLane,
    lane_policy: card.lanePolicy,
    allocated_lane: card.allocatedLane,
    workstation_registration: card.workstationRegistration,
    workstation_job_state: card.workstationJobState,
    workstation_evidence_state: card.workstationEvidenceState,
    workstation_evidence_return_state: card.workstationEvidenceReturnState,
    evidence_identity_present: card.evidenceIdentity !== null,
  }
}

function trace(event: string, card: CardSnapshot, extra: JsonRecord = {}): void {
  vertexObservability.trace(event, {
    ...safePayload(card),
    ...extra,
  }, context(card))
}

function transition(
  card: CardSnapshot,
  prev: CardSnapshot,
  fieldName: keyof CardSnapshot,
  event: string,
): void {
  const before = prev[fieldName]
  const after = card[fieldName]
  if (before === after) return

  vertexObservability.stateTransition(
    `vra.${String(fieldName)}`,
    before,
    after,
    safePayload(card),
    context(card),
  )
  trace(event, card, { from: before, to: after })
}

function observe(card: CardSnapshot, prev: CardSnapshot | undefined): void {
  if (!prev) {
    trace('vra_capture_staged_observed', card, {
      durable_observer: true,
      observation_source: 'vra-dispatch-ledger',
    })
    return
  }

  transition(card, prev, 'humanApproval', 'human_approval_transition_observed')
  transition(card, prev, 'dispatchPhase', 'dispatch_phase_transition_observed')
  transition(card, prev, 'status', 'vra_status_transition_observed')
  transition(card, prev, 'workstationRegistration', 'workstation_registration_transition_observed')
  transition(card, prev, 'workstationJobState', 'workstation_job_state_transition_observed')
  transition(card, prev, 'workstationEvidenceState', 'evidence_state_transition_observed')
  transition(card, prev, 'workstationEvidenceReturnState', 'evidence_return_state_transition_observed')

  if (prev.humanApproval !== 'APPROVED' && card.humanApproval === 'APPROVED') {
    trace('human_approval_durable_commit_observed', card)
  }
  if (prev.dispatchPhase !== 'PUBLISHED' && card.dispatchPhase === 'PUBLISHED') {
    trace('incoming_atomic_publish_observed', card)
  }
  if (prev.allocatedLane !== card.allocatedLane && card.allocatedLane) {
    trace('workstation_lane_allocation_observed', card, {
      prior_lane: prev.allocatedLane,
    })
  }
  if (!prev.evidenceIdentity && card.evidenceIdentity) {
    trace('workstation_evidence_return_observed', card, {
      evidence_id_present: true,
    })
  }
}

function poll(): void {
  const ledger = path.join(app.getPath('userData'), 'vra-dispatch', 'ledger.json')
  try {
    if (!fs.existsSync(ledger)) return
    const parsed = JSON.parse(fs.readFileSync(ledger, 'utf8')) as unknown
    const cards = cardsFromLedger(parsed)
    const current = new Map<string, CardSnapshot>()

    for (const raw of cards) {
      const next = snapshot(raw)
      if (!next) continue
      current.set(next.id, next)

      if (initialized) observe(next, previous.get(next.id))
    }

    if (initialized) {
      for (const [id, old] of previous) {
        if (!current.has(id)) {
          trace('vra_card_removed_from_durable_ledger', old)
        }
      }
    }

    previous.clear()
    for (const [id, card] of current) previous.set(id, card)

    if (!initialized) {
      initialized = true
      vertexObservability.trace('dispatch_correlation_observer_baseline', {
        durable_card_count: current.size,
        correlation_contract: 'vra-routing/1',
        mutation: false,
      })
    }
    lastReadError = ''
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message !== lastReadError) {
      lastReadError = message
      vertexObservability.trace('dispatch_correlation_observer_read_error', {
        message,
        mutation: false,
      })
    }
  }
}

export function startDispatchCorrelationObserver(): void {
  if (started) return
  started = true

  vertexObservability.trace('dispatch_correlation_observer_started', {
    poll_ms: POLL_MS,
    source: 'durable-vra-dispatch-ledger',
    write_path_hook: false,
    mutation: false,
  })

  poll()
  timer = setInterval(poll, POLL_MS)
  timer.unref()

  app.on('before-quit', () => {
    if (timer) clearInterval(timer)
    timer = null
  })
}
