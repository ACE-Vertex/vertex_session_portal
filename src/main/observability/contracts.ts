export const OBSERVABILITY_CONTRACT = 'vertex-session-portal/observability-1' as const

export type ObservabilitySeverity = 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL'
export type RayNodeKind = 'file' | 'directory' | 'symlink' | 'other'
export type JudgeFailureClass =
  | 'NONE'
  | 'VERIFY_FAILURE'
  | 'BUILD_FAILURE'
  | 'TIMEOUT'
  | 'PATH_SCOPE_DENIED'
  | 'LOCK_FAILURE'
  | 'ORIGIN_UNRESOLVED'
  | 'WORKSTATION_OFFLINE'
  | 'EVIDENCE_UNAVAILABLE'
  | 'UNKNOWN'

export interface RayNode {
  path: string
  relativePath: string
  kind: RayNodeKind
  depth: number
  sizeBytes: number | null
  modifiedMs: number | null
}

export interface RayTreeReport {
  schema: typeof OBSERVABILITY_CONTRACT
  root: string
  nodes: RayNode[]
  truncated: boolean
  warnings: string[]
  scannedAt: string
}

export interface RayTextRead {
  path: string
  bytesRead: number
  truncated: boolean
  tail: boolean
  text: string
}

export interface RayContentHit {
  path: string
  line: number
  text: string
}

export interface RaySourceFile {
  path: string
  relativePath: string
  extension: string
  imports: string[]
  symbols: string[]
  sizeBytes: number
}

export interface RayDependencyEdge {
  from: string
  specifier: string
  to: string | null
}

export interface DeepRayReport {
  schema: typeof OBSERVABILITY_CONTRACT
  root: string
  tree: RayTreeReport
  sourceFiles: RaySourceFile[]
  edges: RayDependencyEdge[]
  manifests: string[]
  truncated: boolean
  scannedAt: string
}

export interface SensorSignal {
  code: string
  severity: ObservabilitySeverity
  message: string
  source: 'RAY' | 'WORKSTATION_EVIDENCE' | 'PORTAL'
  evidence: Record<string, string | number | boolean | null>
}

export interface WorkstationEvidenceDigest {
  jobId: string | null
  artifactId: string | null
  evidenceId: string | null
  executionLane: string | null
  result: string | null
  verified: boolean | null
  success: boolean | null
  timedOut: boolean
  exitCodes: number[]
  internalReference: string | null
  evidencePath: string | null
  stdout: string | null
  stderr: string | null
  rawFailureText: string
}

export interface JudgeDecision {
  failureClass: JudgeFailureClass
  confidence: number
  summary: string
  recommendedAction: string
  safeToRetryUnchanged: boolean
  needsMoreRay: boolean
  signals: string[]
}

export interface ImpactEntry {
  target: string
  directDependents: string[]
  transitiveDependents: string[]
}

export interface ImpactReport {
  method: 'RESOLVED_IMPORT_GRAPH'
  entries: ImpactEntry[]
  affectedFileCount: number
}

export type ObservabilityOperationKind = 'read' | 'write' | 'delete' | 'exec'

export interface ObservabilityOperation {
  kind: ObservabilityOperationKind
  path?: string
  command?: string
}

export interface GuardRequest {
  mode: 'RAY' | 'ANALYZE' | 'APPLY' | 'VERIFY' | 'RECOVERY'
  authority?: string | null
  humanApproval?: 'PENDING' | 'APPROVED' | null
  operations: ObservabilityOperation[]
}

export interface GuardDecision {
  allowed: boolean
  reasons: string[]
}

export interface BlackBoxEntry {
  sequence: number
  timestamp: string
  channel: string
  payload: string
  sha256: string
}

export interface ObservabilityAnalysis {
  schema: typeof OBSERVABILITY_CONTRACT
  digest: WorkstationEvidenceDigest
  signals: SensorSignal[]
  judge: JudgeDecision
  hydratedLogs: Array<{
    kind: 'stdout' | 'stderr'
    path: string
    available: boolean
    text: string | null
    error: string | null
  }>
}
