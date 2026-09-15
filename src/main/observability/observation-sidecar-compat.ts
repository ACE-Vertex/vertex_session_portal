import { createHash } from 'node:crypto'
import { readFileSync, statSync } from 'node:fs'

export const WORKSTATION_OBSERVATION_PAYLOAD_SCHEMA =
  'vertex-workstation/observation-payload-1' as const

export const OBSERVATION_REFERENCE_KIND =
  'WORKSTATION_OBSERVATION_SIDECAR' as const

export interface WorkstationObservationReference {
  path: string
  bytes: number
  sha256: string
  schema: typeof WORKSTATION_OBSERVATION_PAYLOAD_SCHEMA
  artifact_id: string
  verified?: boolean
  execution_lane?: string
}

export interface ObservationSupplement {
  kind: typeof OBSERVATION_REFERENCE_KIND
  artifactId: string
  path: string
  bytes: number
  sha256: string
  verified?: boolean
  executionLane?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function asOptionalBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined
}

function asOptionalString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim().length > 0 ? value : undefined
}

function sha256File(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

export function parseObservationReference(
  value: unknown,
  expectedArtifactId?: string
): WorkstationObservationReference | null {
  if (!isRecord(value)) return null

  const path = typeof value.path === 'string' ? value.path.trim() : ''
  const bytes = typeof value.bytes === 'number' ? value.bytes : Number.NaN
  const sha256 = typeof value.sha256 === 'string' ? value.sha256.toLowerCase() : ''
  const schema = value.schema
  const artifactId =
    typeof value.artifact_id === 'string' ? value.artifact_id.trim() : ''

  if (!path) return null
  if (!Number.isSafeInteger(bytes) || bytes < 0) return null
  if (!/^[0-9a-f]{64}$/.test(sha256)) return null
  if (schema !== WORKSTATION_OBSERVATION_PAYLOAD_SCHEMA) return null
  if (!artifactId) return null
  if (expectedArtifactId && artifactId !== expectedArtifactId) return null

  try {
    const stat = statSync(path)
    if (!stat.isFile() || stat.size !== bytes) return null
    if (sha256File(path) !== sha256) return null
  } catch {
    return null
  }

  return {
    path,
    bytes,
    sha256,
    schema: WORKSTATION_OBSERVATION_PAYLOAD_SCHEMA,
    artifact_id: artifactId,
    verified: asOptionalBoolean(value.verified),
    execution_lane: asOptionalString(value.execution_lane)
  }
}

export function toObservationSupplement(
  value: unknown,
  expectedArtifactId?: string
): ObservationSupplement | null {
  const reference = parseObservationReference(value, expectedArtifactId)
  if (!reference) return null

  return {
    kind: OBSERVATION_REFERENCE_KIND,
    artifactId: reference.artifact_id,
    path: reference.path,
    bytes: reference.bytes,
    sha256: reference.sha256,
    verified: reference.verified,
    executionLane: reference.execution_lane
  }
}
