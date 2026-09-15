import type { RegistryRecord, RegistryState } from './vra-registry-contract'
import type { VraRegistryCore } from './vra-registry-core'
import type { VraRegistryStore } from './vra-registry-store'

type WorkstationRegistrationState = 'NOT_READY' | 'PENDING' | 'REGISTERING' | 'REGISTERED' | 'BLOCKED'
type WorkstationJobState =
  | 'REGISTERED'
  | 'DISPATCHED'
  | 'EXECUTING'
  | 'SUCCEEDED'
  | 'FAILED'
  | 'REJECTED'
  | 'ROLLED_BACK'

export interface AutoRegistryWorkstationObservation {
  jobId: string
  artifactId: string | null
  correlationId: string
  portalPublished: boolean
  workstationRegistration: WorkstationRegistrationState
  workstationJobState: WorkstationJobState | null
  allocatedLane: string | null
  evidenceId: string | null
  evidenceState: string | null
  evidenceReturnState: string | null
}

export interface AutoRegistryWorkstationSyncResult {
  tracked: boolean
  registryId: string | null
  state: RegistryState | null
}

function assertIdentity(record: RegistryRecord, observation: AutoRegistryWorkstationObservation): void {
  if (!observation.artifactId || record.artifactId !== observation.artifactId) {
    throw new Error('REGISTRY_WORKSTATION_ARTIFACT_ID_MISMATCH')
  }
  if (record.correlationId !== observation.correlationId) {
    throw new Error('REGISTRY_WORKSTATION_CORRELATION_ID_MISMATCH')
  }
  if (record.jobId !== observation.jobId) {
    throw new Error('REGISTRY_WORKSTATION_JOB_ID_MISMATCH')
  }
}

async function reload(store: VraRegistryStore, registryId: string): Promise<RegistryRecord> {
  const record = await store.getByRegistryId(registryId)
  if (!record) throw new Error('REGISTRY_RECORD_LOST_DURING_SYNC')
  return record
}

/**
 * AUTO Registry lifecycle projection from authoritative Workstation facts.
 *
 * This adapter never allocates lanes and never changes a VRA, Human approval,
 * Dispatch Bay presentation, Workstation execution, or Evidence payload.
 *
 * No Registry record means MANUAL/non-AUTO work: return without mutation.
 */
export async function syncAutoRegistryWorkstationLifecycle(
  core: VraRegistryCore,
  store: VraRegistryStore,
  observation: AutoRegistryWorkstationObservation,
): Promise<AutoRegistryWorkstationSyncResult> {
  let record = await store.getByJobId(observation.jobId)
  if (!record) return { tracked: false, registryId: null, state: null }

  assertIdentity(record, observation)

  if (record.state === 'RETURNED' || record.state === 'REJECTED') {
    return { tracked: true, registryId: record.registryId, state: record.state }
  }

  // Recovery boundary: publication may have committed before a post-publish
  // Registry DISPATCHED update survived. Only a durably published Portal card
  // can repair READY_FOR_BAY -> DISPATCHED.
  if (
    record.state === 'READY_FOR_BAY' &&
    observation.portalPublished &&
    ['REGISTERING', 'REGISTERED'].includes(observation.workstationRegistration)
  ) {
    await core.markDispatched(record.registryId)
    record = await reload(store, record.registryId)
  }

  const workstationFailed =
    observation.workstationJobState === 'FAILED' ||
    observation.workstationJobState === 'REJECTED' ||
    observation.workstationJobState === 'ROLLED_BACK'

  if (workstationFailed) {
    if (record.state !== 'FAILED' && record.state !== 'RETURNED' && record.state !== 'REJECTED') {
      await core.fail(record.registryId)
      record = await reload(store, record.registryId)
    }
    return { tracked: true, registryId: record.registryId, state: record.state }
  }

  // Workstation owns final lane allocation. Registry records it only after
  // Workstation has reached EXECUTING or SUCCEEDED.
  if (
    record.state === 'DISPATCHED' &&
    (observation.workstationJobState === 'EXECUTING' || observation.workstationJobState === 'SUCCEEDED') &&
    observation.allocatedLane
  ) {
    await core.markExecuting(record.registryId, observation.allocatedLane)
    record = await reload(store, record.registryId)
  }

  if (
    record.state === 'EXECUTING' &&
    observation.evidenceState === 'AVAILABLE' &&
    observation.evidenceId
  ) {
    await core.bindEvidence(record.registryId, observation.evidenceId)
    record = await reload(store, record.registryId)
  }

  if (
    record.state === 'EVIDENCE_AVAILABLE' &&
    (observation.evidenceReturnState === 'RETURN_QUEUED' ||
      observation.evidenceReturnState === 'RETURNED')
  ) {
    await core.markReturnQueued(record.registryId)
    record = await reload(store, record.registryId)
  }

  if (record.state === 'RETURN_QUEUED' && observation.evidenceReturnState === 'RETURNED') {
    await core.markReturned(record.registryId)
    record = await reload(store, record.registryId)
  }

  return { tracked: true, registryId: record.registryId, state: record.state }
}
