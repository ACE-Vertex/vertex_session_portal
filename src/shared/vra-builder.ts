import { resolveActiveSystemPolicy } from './system-policy-registry'
import { resolveVertexContract as getContract } from './vertex-contract-catalog'
import { validateVraAgainstActivePolicy, type VraValidationResult } from './vra-policy-validator'

export interface VraBuilderInput {
  readonly artifact_id: string
  readonly title: string
  readonly source: Readonly<{ actor: string; model: string }>
  readonly target: Readonly<{ project_root: string }>
  readonly routing: Readonly<{
    job_id: string
    origin_vera: string
    origin_session: string
    origin_window: string
    project_id: string
    project_name: string
    correlation_id: string
    lane_policy: 'ANY' | 'PREFER'
  }>
  readonly operations: readonly unknown[]
  readonly verification: readonly unknown[]
  readonly card_kind?: 'TEST'
}

export interface VraBuilderResult {
  readonly manifest: unknown
  readonly validation: VraValidationResult
}

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(label)
  }
  return value as Record<string, unknown>
}

function readStaticPath(root: unknown, segments: readonly string[]): Record<string, unknown> {
  let current: unknown = root
  for (const segment of segments) {
    const record = asRecord(current, 'VRA_CONTRACT_PROFILE_INVALID')
    current = record[segment]
  }
  return asRecord(current, 'VRA_CONTRACT_PROFILE_INVALID')
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key]
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error('VRA_CONTRACT_PROFILE_MISSING_' + key)
  }
  return value
}

/**
 * Build a VRA manifest from the currently active System Policy and the
 * machine-readable canonical profile in the Contract Catalog.
 *
 * The LLM/issuer supplies variable work data. Fixed issuance semantics are
 * resolved from policy/catalog and the completed manifest is validated
 * deterministically before it can leave this boundary.
 */
export function buildVraFromActivePolicy(input: VraBuilderInput): VraBuilderResult {
  const policy = resolveActiveSystemPolicy('vertex.vra.issue')
  if (!policy) throw new Error('ACTIVE_VRA_ISSUANCE_POLICY_NOT_FOUND')

  const policyView = policy as unknown as Record<string, unknown>
  const contractRef = policyView['contract_catalog_id']
  const versionValue = policyView['policy_version']

  if (typeof contractRef !== 'string' || contractRef.length === 0) {
    throw new Error('ACTIVE_VRA_ISSUANCE_CONTRACT_REF_MISSING')
  }
  const policyVersion = typeof versionValue === 'string' ? versionValue : ''

  const contract = (getContract as unknown as (id: string) => unknown)(contractRef)
  if (!contract) throw new Error('ACTIVE_VRA_ISSUANCE_CONTRACT_NOT_FOUND')

  const profile = readStaticPath(contract, [])
  const schemaVersion = requireString(profile, 'schema_version')
  const authority = requireString(profile, 'authority')

  const routingProfile =
    profile['routing'] && typeof profile['routing'] === 'object'
      ? asRecord(profile['routing'], 'VRA_ROUTING_PROFILE_INVALID')
      : profile

  const contractVersion = requireString(routingProfile, 'contract_version')
  const returnChannel = requireString(routingProfile, 'return_channel')

  const manifest: unknown = {
    schema_version: schemaVersion,
    artifact_id: input.artifact_id,
    title: input.title,
    source: input.source,
    target: input.target,
    authority,
    routing: {
      contract_version: contractVersion,
      job_id: input.routing.job_id,
      origin_vera: input.routing.origin_vera,
      origin_session: input.routing.origin_session,
      origin_window: input.routing.origin_window,
      return_channel: returnChannel,
      project_id: input.routing.project_id,
      project_name: input.routing.project_name,
      correlation_id: input.routing.correlation_id,
      lane_policy: input.routing.lane_policy
    },
    operations: input.operations,
    verification: input.verification,
    ...(input.card_kind ? { card_kind: input.card_kind } : {})
  }

  const validation = validateVraAgainstActivePolicy(manifest)
  if (!validation.valid) {
    throw new Error('VRA_BUILDER_POLICY_VALIDATION_FAILED')
  }

  return { manifest, validation }
}
