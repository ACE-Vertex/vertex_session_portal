// Vertex System Policy Layer — Phase 1 Foundation
// Source of truth: unique valid Canonical VRA Manifest resolved at install time.
// This file does not grant mutation authority.

export const SYSTEM_POLICY_REGISTRY_SCHEMA = 'vertex-system-policy-registry/1' as const

export type SystemPolicyApprovalState =
  | 'ACTIVE_CANONICAL_BASELINE'
  | 'PROPOSED'
  | 'REJECTED'
  | 'SUPERSEDED'

export interface SystemPolicyProvenance {
  readonly kind: 'CANONICAL_IMPORT'
  readonly canonical_manifest: string
  readonly contract_catalog_id: 'vertex.vra.issue/1'
}

export interface VraIssuePolicyContract {
  readonly schema_version: 'vra/1'
  readonly authority: 'HUMAN_APPLY'
  readonly routing: {
    readonly contract_version: 'vra-routing/1'
    readonly required: readonly [
      'job_id',
      'origin_vera',
      'origin_session',
      'origin_window',
      'return_channel',
      'project_id',
      'project_name',
      'correlation_id',
      'lane_policy'
    ]
    readonly return_channel: 'vertex-session-portal:return-queue'
    readonly lane_policy_allowed: readonly ['ANY', 'PREFER']
    readonly lane_allocation_authority: 'Vertex Workstation'
  }
  readonly identity: {
    readonly fresh_per_issuance: readonly ['artifact_id', 'job_id', 'correlation_id']
    readonly immutable_origin: readonly ['origin_vera', 'origin_session', 'origin_window']
  }
  readonly operations: {
    readonly allowed: readonly ['copy']
    readonly source_prefix: 'payload/'
    readonly path_separator: '/'
    readonly sha256: 'actual-64hex-lowercase'
  }
  readonly verification: {
    readonly execute_copied_destination: true
  }
  readonly test_work: {
    readonly card_kind: 'TEST'
    readonly prefer_disposable_read_only: true
  }
  readonly forbidden: readonly [
    'unknown_schema_fields',
    'custom_execution_envelopes',
    'custom_evidence_formats',
    'invented_operations'
  ]
}

export interface SystemPolicyRecord<TContract> {
  readonly policy_id: string
  readonly policy_version: string
  readonly active_version: string
  readonly approval_state: SystemPolicyApprovalState
  readonly compatibility: readonly string[]
  readonly provenance: SystemPolicyProvenance
  readonly contract: TContract
}

export const VRA_ISSUE_POLICY_1_0_0 = {
  policy_id: 'vertex.vra.issue',
  policy_version: '1.0.0',
  active_version: '1.0.0',
  approval_state: 'ACTIVE_CANONICAL_BASELINE',
  compatibility: ['vra/1', 'vra-routing/1'] as const,
  provenance: {
    kind: 'CANONICAL_IMPORT',
    canonical_manifest: "G:/Vertex_Project/Development/vertex_workstation/runtime/lanes/lane-06/temp/stage-vertex-vra-canonical-manifest-store-000151V5-1789223261693-72/apply-prepared/VRA_CANONICAL_MANIFEST_vra-1_000150V5.json",
    contract_catalog_id: 'vertex.vra.issue/1'
  },
  contract: {
    schema_version: 'vra/1',
    authority: 'HUMAN_APPLY',
    routing: {
      contract_version: 'vra-routing/1',
      required: [
        'job_id',
        'origin_vera',
        'origin_session',
        'origin_window',
        'return_channel',
        'project_id',
        'project_name',
        'correlation_id',
        'lane_policy'
      ] as const,
      return_channel: 'vertex-session-portal:return-queue',
      lane_policy_allowed: ['ANY', 'PREFER'] as const,
      lane_allocation_authority: 'Vertex Workstation'
    },
    identity: {
      fresh_per_issuance: ['artifact_id', 'job_id', 'correlation_id'] as const,
      immutable_origin: ['origin_vera', 'origin_session', 'origin_window'] as const
    },
    operations: {
      allowed: ['copy'] as const,
      source_prefix: 'payload/',
      path_separator: '/',
      sha256: 'actual-64hex-lowercase'
    },
    verification: {
      execute_copied_destination: true
    },
    test_work: {
      card_kind: 'TEST',
      prefer_disposable_read_only: true
    },
    forbidden: [
      'unknown_schema_fields',
      'custom_execution_envelopes',
      'custom_evidence_formats',
      'invented_operations'
    ] as const
  }
} as const satisfies SystemPolicyRecord<VraIssuePolicyContract>

const POLICY_RECORDS = [VRA_ISSUE_POLICY_1_0_0] as const

export type KnownSystemPolicyRecord = (typeof POLICY_RECORDS)[number]

export function listSystemPolicyRecords(): readonly KnownSystemPolicyRecord[] {
  return POLICY_RECORDS
}

export function getSystemPolicyRecord(
  policyId: string,
  policyVersion: string
): KnownSystemPolicyRecord | null {
  return POLICY_RECORDS.find(
    record => record.policy_id === policyId && record.policy_version === policyVersion
  ) ?? null
}

export const SYSTEM_POLICY_PHASE1_GUARDS = [
  'POLICY_NOT_OWNED_BY_LLM',
  'NO_POLICY_MUTATION_API_IN_PHASE1',
  'VRA_REGISTRY_RESPONSIBILITY_REMAINS_SEPARATE',
  'WORKSTATION_EXECUTION_AUTHORITY_REMAINS_SEPARATE',
  'HUMAN_FINAL_AUTHORITY'
] as const

// VERTEX_SYSTEM_POLICY_RESOLVER_000062V2

export interface SystemPolicyResolverProvider {
  resolveActiveSystemPolicy: (policyId: string) => unknown
  listActiveSystemPolicies: () => readonly unknown[]
}

let systemPolicyResolverProvider: SystemPolicyResolverProvider | null = null

export function configureSystemPolicyResolverProvider(
  provider: SystemPolicyResolverProvider
): void {
  systemPolicyResolverProvider = provider
}

export function resolveActiveSystemPolicy(
  policyId: string
): KnownSystemPolicyRecord | null {
  if (systemPolicyResolverProvider) {
    return systemPolicyResolverProvider.resolveActiveSystemPolicy(policyId) as never
  }

  const records = POLICY_RECORDS.filter(record => record.policy_id === policyId)
  if (records.length === 0) return null

  const activeVersion = records[0]?.active_version
  if (!activeVersion) return null

  return records.find(record => record.policy_version === activeVersion) ?? null
}

export function listActiveSystemPolicies(): readonly KnownSystemPolicyRecord[] {
  if (systemPolicyResolverProvider) {
    return systemPolicyResolverProvider.listActiveSystemPolicies() as never
  }

  const seen = new Set<string>()
  const active: KnownSystemPolicyRecord[] = []

  for (const record of POLICY_RECORDS) {
    if (seen.has(record.policy_id)) continue
    seen.add(record.policy_id)

    const resolved = resolveActiveSystemPolicy(record.policy_id)
    if (resolved) active.push(resolved)
  }

  return active
}
