// VXS_WORKSTATION_READ_ADAPTER_FOUNDATION_000053
//
// Canonical VXS -> Vertex Workstation READ boundary.
// This module deliberately does not own execution, scheduling, lanes, mutation,
// Evidence routing, ACK, or Human authority.
//
// Current transport policy:
//   official Control Plane reads -> loopback HTTP 127.0.0.1:47832
//   forensic/durable observation -> bounded local filesystem roots
//
// Production mutation through this adapter is forbidden.

import type {
  VxsCommandDispatchResult
} from './vxs-command-registry'

export const VXS_WORKSTATION_READ_CONTRACT =
  'vertex-vxs/workstation-read-adapter-1' as const

export const VXS_WORKSTATION_BASE_URL =
  'http://127.0.0.1:47832' as const

export const VXS_WORKSTATION_AUTHORITY_CLASS =
  'OBSERVE' as const

export const VXS_WORKSTATION_DURABLE_ROOTS = Object.freeze({
  jobRegistry:
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry',
  evidence:
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\evidence',
  lanes:
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\lanes',
  portalDispatch:
    'G:\\Vertex_Project\\Development\\vertex_session_portal'
})

const DEFAULT_PORTAL_ROOT =
  'G:\\Vertex_Project\\Development\\vertex_session_portal'

const JOB_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$/

export type VxsWorkstationReadChannel =
  | 'HTTP_CONTROL_PLANE'
  | 'DURABLE_FILESYSTEM_OBSERVATION'

export interface VxsWorkstationReadDescriptor {
  contract: typeof VXS_WORKSTATION_READ_CONTRACT
  authorityClass: typeof VXS_WORKSTATION_AUTHORITY_CLASS
  channel: VxsWorkstationReadChannel
  operation: string
  target: string
  mutation: false
}

function psSingleQuote(value: string): string {
  return `'${value.replaceAll("'", "''")}'`
}

export function isValidVxsWorkstationJobId(value: string): boolean {
  return JOB_ID_PATTERN.test(value)
}

export function describeVxsWorkstationHttpRead(
  urlPath: string
): VxsWorkstationReadDescriptor {
  return {
    contract: VXS_WORKSTATION_READ_CONTRACT,
    authorityClass: VXS_WORKSTATION_AUTHORITY_CLASS,
    channel: 'HTTP_CONTROL_PLANE',
    operation: 'GET',
    target: `${VXS_WORKSTATION_BASE_URL}${urlPath}`,
    mutation: false
  }
}

export function describeVxsWorkstationDurableRead(
  operation: string,
  target: string
): VxsWorkstationReadDescriptor {
  return {
    contract: VXS_WORKSTATION_READ_CONTRACT,
    authorityClass: VXS_WORKSTATION_AUTHORITY_CLASS,
    channel: 'DURABLE_FILESYSTEM_OBSERVATION',
    operation,
    target,
    mutation: false
  }
}

export class VxsWorkstationReadAdapter {
  readonly contract = VXS_WORKSTATION_READ_CONTRACT
  readonly authorityClass = VXS_WORKSTATION_AUTHORITY_CLASS
  readonly baseUrl = VXS_WORKSTATION_BASE_URL

  constructor(
    readonly portalRoot: string = DEFAULT_PORTAL_ROOT
  ) {}

  health(): VxsCommandDispatchResult {
    return this.getJson('/v1/health', 'WORKSTATION', 'GET /v1/health')
  }

  safety(): VxsCommandDispatchResult {
    return this.getJson('/v1/safety', 'WORKSTATION', 'GET /v1/safety')
  }

  job(jobId: string): VxsCommandDispatchResult {
    if (!isValidVxsWorkstationJobId(jobId)) {
      return this.invalidJobId('vxs workstation job <job-id>')
    }

    return this.getJson(
      `/v1/jobs/${encodeURIComponent(jobId)}`,
      'WORKSTATION',
      `GET /v1/jobs/${jobId}`
    )
  }

  evidence(jobId: string): VxsCommandDispatchResult {
    if (!isValidVxsWorkstationJobId(jobId)) {
      return this.invalidJobId('vxs evidence <job-id>')
    }

    return this.getJson(
      `/v1/jobs/${encodeURIComponent(jobId)}/evidence`,
      'EVIDENCE',
      `GET /v1/jobs/${jobId}/evidence`
    )
  }

  durableJobRegistry(): VxsWorkstationReadDescriptor {
    return describeVxsWorkstationDurableRead(
      'READ_JOB_REGISTRY',
      VXS_WORKSTATION_DURABLE_ROOTS.jobRegistry
    )
  }

  durableEvidenceStore(): VxsWorkstationReadDescriptor {
    return describeVxsWorkstationDurableRead(
      'READ_EVIDENCE_STORE',
      VXS_WORKSTATION_DURABLE_ROOTS.evidence
    )
  }

  durableLaneObservation(): VxsWorkstationReadDescriptor {
    return describeVxsWorkstationDurableRead(
      'READ_LANE_OBSERVATION',
      VXS_WORKSTATION_DURABLE_ROOTS.lanes
    )
  }

  private getJson(
    urlPath: string,
    capability: string,
    summary: string
  ): VxsCommandDispatchResult {
    const descriptor = describeVxsWorkstationHttpRead(urlPath)
    const command = [
      "$ErrorActionPreference='Stop'",
      `$r=Invoke-RestMethod -Method Get -Uri ${psSingleQuote(descriptor.target)} -TimeoutSec 4`,
      "$r | ConvertTo-Json -Depth 16"
    ].join('; ')

    return {
      kind: 'execute',
      executionCommand: command,
      executionCwd: this.portalRoot,
      capability,
      routeSummary: summary
    }
  }

  private invalidJobId(usage: string): VxsCommandDispatchResult {
    return {
      kind: 'immediate',
      output: [
        'ERROR: A valid job-id is required.',
        `Usage: ${usage}`,
        ''
      ].join('\n'),
      exitCode: 2,
      stream: 'stderr'
    }
  }
}

export const vxsWorkstationReadAdapter =
  new VxsWorkstationReadAdapter()
