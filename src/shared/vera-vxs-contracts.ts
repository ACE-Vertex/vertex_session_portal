import type {
  VertexShellCommandResult,
  VertexShellStreamEvent
} from './vertex-shell-contracts'

export const VERA_VXS_REQUEST_SCHEMA = 'vertex-vxs/vera-request-1' as const
export const VERA_VXS_RESULT_SCHEMA = 'vertex-vxs/vera-result-1' as const

export type VeraVxsAuthority = 'AUTO_SAFE' | 'HUMAN_APPLY'

export interface VeraVxsOrigin {
  vera: string
  session: string
  window: string
}

export interface VeraVxsRequest {
  schema: typeof VERA_VXS_REQUEST_SCHEMA
  requestId: string
  correlationId: string
  origin: VeraVxsOrigin
  authority: VeraVxsAuthority
  command: string
  cwd?: string
}

export interface VeraVxsResult {
  schema: typeof VERA_VXS_RESULT_SCHEMA
  requestId: string
  correlationId: string
  origin: VeraVxsOrigin
  requestedAuthority: VeraVxsAuthority
  authorityEnforcement: 'VXS_EXISTING_POLICY'
  transport: 'VERTEX_SHELL_SERVICE'
  acceptedAt: string
  completedAt: string
  streamBytes: number
  streamTruncated: boolean
  streamEvents: VertexShellStreamEvent[]
  shellResult: VertexShellCommandResult
}
