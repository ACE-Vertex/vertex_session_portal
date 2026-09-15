export const VRA_REGISTRY_SCHEMA = 'vertex-session-portal/vra-registry/1' as const
export const VLOG_SCHEMA = 'vertex-session-portal/vlog/1' as const

export type RegistryDispatchMode = 'AUTO'

export type RegistryState =
  | 'REGISTERED'
  | 'READY_FOR_BAY'
  | 'DISPATCHED'
  | 'EXECUTING'
  | 'EVIDENCE_AVAILABLE'
  | 'RETURN_QUEUED'
  | 'RETURNED'
  | 'FAILED'
  | 'REJECTED'

export type ExternalLanePolicy = 'ANY' | 'PREFER'

export interface ImmutableRegistryOrigin {
  originVera: 'VERA01' | 'VERA02' | 'VERA03' | 'VERA04' | 'VERA05'
  originSession: 'vera-01' | 'vera-02' | 'vera-03' | 'vera-04' | 'vera-05'
  originWindow: 'vera-01' | 'vera-02' | 'vera-03' | 'vera-04' | 'vera-05'
  returnChannel: string
}

export interface AutoRegistryIntake {
  dispatchMode: RegistryDispatchMode
  registryId: string
  jobId: string
  artifactId: string
  correlationId: string
  projectId: string | null
  projectName: string | null
  requestedLane: string | null
  lanePolicy: ExternalLanePolicy
  parallelism: number
  workerConcurrency: number | null
  origin: ImmutableRegistryOrigin
}

export interface RegistryRecord extends AutoRegistryIntake {
  schema: typeof VRA_REGISTRY_SCHEMA
  state: RegistryState
  allocatedLane: string | null
  evidenceId: string | null
  rerunOfJobId: string | null
  createdUtc: string
  updatedUtc: string
}

export interface RegistryTransition {
  registryId: string
  jobId: string
  artifactId: string
  correlationId: string
  from: RegistryState | null
  to: RegistryState
  occurredUtc: string
  evidenceId: string | null
  allocatedLane: string | null
}

export interface RegistryMutationResult {
  record: RegistryRecord
  changed: boolean
  idempotent: boolean
}
