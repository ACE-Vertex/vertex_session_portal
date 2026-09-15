import type { SqliteVraRegistryStore } from './sqlite-vra-registry-store'

type OriginVera = 'VERA01' | 'VERA02' | 'VERA03' | 'VERA04' | 'VERA05' | 'UNKNOWN'

export interface EvidenceReturnRouteCandidate {
  jobId: string
  artifactId: string | null
  correlationId: string
  originVera: OriginVera
  originSession: string | null
  originWindow: string | null
  returnChannel: string
  evidenceId: string | null
}

/**
 * Registry guard for the already-existing exact-origin Evidence return route.
 *
 * MANUAL/non-AUTO work has no Registry record and remains on the legacy direct path.
 * AUTO work must match the durable Registry identity, immutable origin and Evidence ID,
 * and must already be in RETURN_QUEUED before the renderer is allowed to receive payload.
 *
 * This function does not deliver Evidence and does not ACK Workstation.
 */
export function registryAllowsEvidenceReturn(
  store: SqliteVraRegistryStore,
  candidate: EvidenceReturnRouteCandidate,
): boolean {
  const record = store.getByJobId(candidate.jobId)

  // No Registry record means the legacy MANUAL path. Registry is AUTO-only.
  if (!record) return true

  if (record.dispatchMode !== 'AUTO') return false
  if (record.state !== 'RETURN_QUEUED') return false
  if (!record.evidenceId || record.evidenceId !== candidate.evidenceId) return false

  if (!candidate.artifactId || record.artifactId !== candidate.artifactId) return false
  if (record.correlationId !== candidate.correlationId) return false

  if (
    candidate.originVera === 'UNKNOWN' ||
    record.origin.originVera !== candidate.originVera ||
    record.origin.originSession !== candidate.originSession ||
    record.origin.originWindow !== candidate.originWindow ||
    record.origin.returnChannel !== candidate.returnChannel
  ) return false

  return true
}
