import type { RegistryTransition } from './vra-registry-contract'

export type VLogEventKind =
  | 'REGISTRY_REGISTERED'
  | 'STATE_TRANSITION'
  | 'BAY_TRIGGER_READY'
  | 'EVIDENCE_BOUND'
  | 'RETURN_COMPLETE'
  | 'ANOMALY'

export interface VLogEvent {
  schema: 'vertex-session-portal/vlog/1'
  eventId: string
  kind: VLogEventKind
  registryId: string
  jobId: string
  artifactId: string
  correlationId: string
  occurredUtc: string
  stateFrom: string | null
  stateTo: string | null
  evidenceId: string | null
  code: string | null
  note: string | null
}

export interface VLogQuery {
  reason: string
  jobId?: string
  artifactId?: string
  correlationId?: string
  limit?: number
}

export interface VLogAppendStore {
  append(event: VLogEvent): Promise<void> | void
}

export interface VLogQueryGate {
  query(request: VLogQuery): Promise<readonly VLogEvent[]> | readonly VLogEvent[]
}

/**
 * Canonical SQLite schema for the durable adapter.
 * Foundation intentionally does not import a SQLite driver. The production
 * adapter is wired in a separate pass after runtime dependency detection.
 */
export const VLOG_SQLITE_SCHEMA = `
CREATE TABLE IF NOT EXISTS vertex_vlog (
  event_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  kind TEXT NOT NULL,
  registry_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  occurred_utc TEXT NOT NULL,
  state_from TEXT NULL,
  state_to TEXT NULL,
  evidence_id TEXT NULL,
  code TEXT NULL,
  note TEXT NULL
);
CREATE INDEX IF NOT EXISTS idx_vertex_vlog_job ON vertex_vlog(job_id, occurred_utc);
CREATE INDEX IF NOT EXISTS idx_vertex_vlog_artifact ON vertex_vlog(artifact_id, occurred_utc);
CREATE INDEX IF NOT EXISTS idx_vertex_vlog_correlation ON vertex_vlog(correlation_id, occurred_utc);
`.trim()

export function eventFromTransition(
  eventId: string,
  transition: RegistryTransition,
): VLogEvent {
  return {
    schema: 'vertex-session-portal/vlog/1',
    eventId,
    kind: transition.to === 'RETURNED' ? 'RETURN_COMPLETE' : 'STATE_TRANSITION',
    registryId: transition.registryId,
    jobId: transition.jobId,
    artifactId: transition.artifactId,
    correlationId: transition.correlationId,
    occurredUtc: transition.occurredUtc,
    stateFrom: transition.from,
    stateTo: transition.to,
    evidenceId: transition.evidenceId,
    code: null,
    note: null,
  }
}

export function validateVLogQuery(request: VLogQuery): Required<Pick<VLogQuery, 'reason' | 'limit'>> & VLogQuery {
  const reason = request.reason.trim()
  if (!reason) throw new Error('VLOG_QUERY_REASON_REQUIRED')
  if (!request.jobId && !request.artifactId && !request.correlationId) {
    throw new Error('VLOG_QUERY_SCOPE_REQUIRED')
  }
  const limit = request.limit ?? 100
  if (!Number.isInteger(limit) || limit < 1 || limit > 200) {
    throw new Error('VLOG_QUERY_LIMIT_INVALID')
  }
  return { ...request, reason, limit }
}
