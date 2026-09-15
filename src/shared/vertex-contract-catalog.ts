export const VERTEX_CONTRACT_CATALOG_SCHEMA = 'vertex-contract-catalog/1' as const

export type VertexContractId =
  | 'vertex.vra.issue/1'
  | 'vertex.evidence.read/1'

export type VertexContractCatalogEntry = {
  id: VertexContractId
  version: string
  status: 'ACTIVE'
  purpose: string
  rules: readonly string[]
  example?: Readonly<Record<string, unknown>>
  stateSemantics?: Readonly<Record<string, string>>
  readingOrder?: readonly string[]
  failureClassification?: Readonly<Record<string, string>>
}

const VRA_ISSUE_CONTRACT: VertexContractCatalogEntry = Object.freeze({
  id: 'vertex.vra.issue/1',
  version: '1.0.0',
  status: 'ACTIVE',
  purpose: 'Canonical VRA issuance contract. Never reconstruct VRA format from LLM memory.',
  rules: Object.freeze([
    'schema_version MUST be vra/1.',
    'authority MUST be HUMAN_APPLY.',
    'routing.contract_version MUST be vra-routing/1.',
    'artifact_id, routing.job_id, and routing.correlation_id MUST be fresh for every issuance.',
    'routing.origin_vera, origin_session, and origin_window are immutable issuer provenance.',
    'routing.return_channel MUST be vertex-session-portal:return-queue.',
    'routing.lane_policy MAY be ANY or PREFER. Workstation remains final lane allocation authority.',
    'operations MUST use existing canonical operations. Current canonical issuance uses copy.',
    'copy.source MUST start with payload/ and use forward slashes.',
    'copy.sha256 MUST be the actual 64-character lowercase hexadecimal SHA256 of the payload bytes.',
    'verification MUST execute the copied destination path used by the VRA.',
    'TEST work SHOULD set card_kind to TEST and remain disposable/read-only where practical.',
    'Unknown schema fields, custom execution envelopes, custom Evidence formats, and invented operations are forbidden.'
  ]),
  example: Object.freeze({
    schema_version: 'vra/1',
    artifact_id: '<fresh-artifact-id>',
    title: '<title>',
    source: Object.freeze({
      actor: '<VERAxx>',
      model: '<model>'
    }),
    target: Object.freeze({
      project_root: '<absolute-project-root>'
    }),
    authority: 'HUMAN_APPLY',
    routing: Object.freeze({
      contract_version: 'vra-routing/1',
      job_id: '<fresh-job-id>',
      origin_vera: '<VERAxx>',
      origin_session: '<vera-xx>',
      origin_window: '<vera-xx>',
      return_channel: 'vertex-session-portal:return-queue',
      project_id: '<project-id>',
      project_name: '<project-name>',
      correlation_id: '<fresh-correlation-id>',
      lane_policy: 'ANY'
    }),
    operations: Object.freeze([
      Object.freeze({
        op: 'copy',
        source: 'payload/scripts/<script>',
        destination: 'scripts/<script>',
        sha256: '<actual-64hex-sha256>'
      })
    ]),
    verification: Object.freeze([
      Object.freeze({
        program: 'python',
        args: Object.freeze(['scripts/<script>'])
      })
    ])
  })
})

const EVIDENCE_READ_CONTRACT: VertexContractCatalogEntry = Object.freeze({
  id: 'vertex.evidence.read/1',
  version: '1.0.0',
  status: 'ACTIVE',
  purpose: 'Canonical Workstation Evidence interpretation contract. Never infer state meaning from LLM memory.',
  rules: Object.freeze([
    'First bind Evidence to the expected artifact_id, job_id, correlation_id, and immutable origin.',
    'Interpret Workstation execution success from result, verified, verification success, command exit_code, and final_state together.',
    'AVAILABLE means durable Evidence exists. It does not by itself prove Vera/chat delivery.',
    'RETURN_QUEUED means the return handoff is queued or awaiting completion/ack. It is not proof that Vera/chat has not already displayed the Evidence.',
    'RETURNED means the configured return workflow recorded completion/ack. It is not proof that a human has read the message.',
    'Transport state and chat visibility state are distinct observations.',
    'If verification failed, inspect rollback state before assuming production files remain modified.',
    'A released write lock indicates the Workstation lane write lock is no longer held.',
    'Do not blame Registry, Portal, or Workstation without locating the first boundary whose durable facts disagree.'
  ]),
  stateSemantics: Object.freeze({
    'result=succeeded + verified=true': 'Workstation verification succeeded for the artifact.',
    'result=failed OR verified=false': 'Workstation verification did not succeed; inspect command and rollback evidence.',
    'verification.success=true': 'All verification commands in this verification evidence succeeded.',
    'command.exit_code=0': 'That verification command exited successfully.',
    'final_state=VERIFIED': 'Workstation stage reached VERIFIED.',
    'final_state=FAILED': 'Workstation stage failed verification.',
    'rollback.STATE=ROLLED_BACK': 'Workstation recovery restored/removed applied changes according to rollback evidence.',
    'write_lock_released=true': 'Workstation released the write lock for the stage.',
    'evidence_state=AVAILABLE': 'Evidence is durably available.',
    'evidence_return_state=RETURN_QUEUED': 'Evidence is queued/in-flight in the return workflow; chat visibility is a separate fact.',
    'evidence_return_state=RETURNED': 'Return workflow recorded delivery completion/ack.'
  }),
  readingOrder: Object.freeze([
    '1.identity: artifact_id, job_id, correlation_id, origin',
    '2.execution: result, verified, final_state',
    '3.verification: command_count, program, args, exit_code, timed_out',
    '4.recovery: rollback state and write lock release',
    '5.evidence: evidence_state and evidence_id',
    '6.return: evidence_return_state and evidence_returned_at',
    '7.boundary: identify the first durable boundary that disagrees before assigning responsibility'
  ]),
  failureClassification: Object.freeze({
    'IDENTITY_MISMATCH': 'artifact/job/correlation/origin does not match the expected contract.',
    'VERIFY_FAILED': 'Workstation verification failed.',
    'ROLLED_BACK': 'Failure occurred and recovery rolled back the stage.',
    'EVIDENCE_AVAILABLE_RETURN_QUEUED': 'Execution produced Evidence; return workflow is queued/in-flight.',
    'RETURNED_NOT_VISIBLE': 'Return workflow says complete but Vera/chat UI visibility is not observed.',
    'NO_DURABLE_MISMATCH': 'Visible durable facts do not show a contract/state inconsistency.'
  })
})

const CATALOG: Readonly<Record<VertexContractId, VertexContractCatalogEntry>> = Object.freeze({
  'vertex.vra.issue/1': VRA_ISSUE_CONTRACT,
  'vertex.evidence.read/1': EVIDENCE_READ_CONTRACT
})

export function resolveVertexContract(id: VertexContractId): VertexContractCatalogEntry {
  return CATALOG[id]
}

export function listVertexContracts(): readonly VertexContractCatalogEntry[] {
  return Object.freeze(Object.values(CATALOG))
}

export const VERTEX_SYSTEM_CONTRACT_RULES = Object.freeze([
  'SYSTEM CONTRACT MUST NOT BE RECONSTRUCTED FROM LLM MEMORY. RESOLVE THE ACTIVE CONTRACT BEFORE USE.',
  'SYSTEM EVIDENCE MUST NOT BE INTERPRETED FROM LLM MEMORY. RESOLVE THE ACTIVE EVIDENCE CONTRACT BEFORE DIAGNOSIS.'
] as const)
