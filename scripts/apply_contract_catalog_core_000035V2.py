from pathlib import Path
import subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
TS = ROOT / "src/shared/vertex-contract-catalog.ts"
DOC = ROOT / "docs/ARCHITECTURE/VERTEX_CONTRACT_CATALOG.md"

TS_CONTENT = "export const VERTEX_CONTRACT_CATALOG_SCHEMA = 'vertex-contract-catalog/1' as const\n\nexport type VertexContractId =\n  | 'vertex.vra.issue/1'\n  | 'vertex.evidence.read/1'\n\nexport type VertexContractCatalogEntry = {\n  id: VertexContractId\n  version: string\n  status: 'ACTIVE'\n  purpose: string\n  rules: readonly string[]\n  example?: Readonly<Record<string, unknown>>\n  stateSemantics?: Readonly<Record<string, string>>\n  readingOrder?: readonly string[]\n  failureClassification?: Readonly<Record<string, string>>\n}\n\nconst VRA_ISSUE_CONTRACT: VertexContractCatalogEntry = Object.freeze({\n  id: 'vertex.vra.issue/1',\n  version: '1.0.0',\n  status: 'ACTIVE',\n  purpose: 'Canonical VRA issuance contract. Never reconstruct VRA format from LLM memory.',\n  rules: Object.freeze([\n    'schema_version MUST be vra/1.',\n    'authority MUST be HUMAN_APPLY.',\n    'routing.contract_version MUST be vra-routing/1.',\n    'artifact_id, routing.job_id, and routing.correlation_id MUST be fresh for every issuance.',\n    'routing.origin_vera, origin_session, and origin_window are immutable issuer provenance.',\n    'routing.return_channel MUST be vertex-session-portal:return-queue.',\n    'routing.lane_policy MAY be ANY or PREFER. Workstation remains final lane allocation authority.',\n    'operations MUST use existing canonical operations. Current canonical issuance uses copy.',\n    'copy.source MUST start with payload/ and use forward slashes.',\n    'copy.sha256 MUST be the actual 64-character lowercase hexadecimal SHA256 of the payload bytes.',\n    'verification MUST execute the copied destination path used by the VRA.',\n    'TEST work SHOULD set card_kind to TEST and remain disposable/read-only where practical.',\n    'Unknown schema fields, custom execution envelopes, custom Evidence formats, and invented operations are forbidden.'\n  ]),\n  example: Object.freeze({\n    schema_version: 'vra/1',\n    artifact_id: '<fresh-artifact-id>',\n    title: '<title>',\n    source: Object.freeze({\n      actor: '<VERAxx>',\n      model: '<model>'\n    }),\n    target: Object.freeze({\n      project_root: '<absolute-project-root>'\n    }),\n    authority: 'HUMAN_APPLY',\n    routing: Object.freeze({\n      contract_version: 'vra-routing/1',\n      job_id: '<fresh-job-id>',\n      origin_vera: '<VERAxx>',\n      origin_session: '<vera-xx>',\n      origin_window: '<vera-xx>',\n      return_channel: 'vertex-session-portal:return-queue',\n      project_id: '<project-id>',\n      project_name: '<project-name>',\n      correlation_id: '<fresh-correlation-id>',\n      lane_policy: 'ANY'\n    }),\n    operations: Object.freeze([\n      Object.freeze({\n        op: 'copy',\n        source: 'payload/scripts/<script>',\n        destination: 'scripts/<script>',\n        sha256: '<actual-64hex-sha256>'\n      })\n    ]),\n    verification: Object.freeze([\n      Object.freeze({\n        program: 'python',\n        args: Object.freeze(['scripts/<script>'])\n      })\n    ])\n  })\n})\n\nconst EVIDENCE_READ_CONTRACT: VertexContractCatalogEntry = Object.freeze({\n  id: 'vertex.evidence.read/1',\n  version: '1.0.0',\n  status: 'ACTIVE',\n  purpose: 'Canonical Workstation Evidence interpretation contract. Never infer state meaning from LLM memory.',\n  rules: Object.freeze([\n    'First bind Evidence to the expected artifact_id, job_id, correlation_id, and immutable origin.',\n    'Interpret Workstation execution success from result, verified, verification success, command exit_code, and final_state together.',\n    'AVAILABLE means durable Evidence exists. It does not by itself prove Vera/chat delivery.',\n    'RETURN_QUEUED means the return handoff is queued or awaiting completion/ack. It is not proof that Vera/chat has not already displayed the Evidence.',\n    'RETURNED means the configured return workflow recorded completion/ack. It is not proof that a human has read the message.',\n    'Transport state and chat visibility state are distinct observations.',\n    'If verification failed, inspect rollback state before assuming production files remain modified.',\n    'A released write lock indicates the Workstation lane write lock is no longer held.',\n    'Do not blame Registry, Portal, or Workstation without locating the first boundary whose durable facts disagree.'\n  ]),\n  stateSemantics: Object.freeze({\n    'result=succeeded + verified=true': 'Workstation verification succeeded for the artifact.',\n    'result=failed OR verified=false': 'Workstation verification did not succeed; inspect command and rollback evidence.',\n    'verification.success=true': 'All verification commands in this verification evidence succeeded.',\n    'command.exit_code=0': 'That verification command exited successfully.',\n    'final_state=VERIFIED': 'Workstation stage reached VERIFIED.',\n    'final_state=FAILED': 'Workstation stage failed verification.',\n    'rollback.STATE=ROLLED_BACK': 'Workstation recovery restored/removed applied changes according to rollback evidence.',\n    'write_lock_released=true': 'Workstation released the write lock for the stage.',\n    'evidence_state=AVAILABLE': 'Evidence is durably available.',\n    'evidence_return_state=RETURN_QUEUED': 'Evidence is queued/in-flight in the return workflow; chat visibility is a separate fact.',\n    'evidence_return_state=RETURNED': 'Return workflow recorded delivery completion/ack.'\n  }),\n  readingOrder: Object.freeze([\n    '1.identity: artifact_id, job_id, correlation_id, origin',\n    '2.execution: result, verified, final_state',\n    '3.verification: command_count, program, args, exit_code, timed_out',\n    '4.recovery: rollback state and write lock release',\n    '5.evidence: evidence_state and evidence_id',\n    '6.return: evidence_return_state and evidence_returned_at',\n    '7.boundary: identify the first durable boundary that disagrees before assigning responsibility'\n  ]),\n  failureClassification: Object.freeze({\n    'IDENTITY_MISMATCH': 'artifact/job/correlation/origin does not match the expected contract.',\n    'VERIFY_FAILED': 'Workstation verification failed.',\n    'ROLLED_BACK': 'Failure occurred and recovery rolled back the stage.',\n    'EVIDENCE_AVAILABLE_RETURN_QUEUED': 'Execution produced Evidence; return workflow is queued/in-flight.',\n    'RETURNED_NOT_VISIBLE': 'Return workflow says complete but Vera/chat UI visibility is not observed.',\n    'NO_DURABLE_MISMATCH': 'Visible durable facts do not show a contract/state inconsistency.'\n  })\n})\n\nconst CATALOG: Readonly<Record<VertexContractId, VertexContractCatalogEntry>> = Object.freeze({\n  'vertex.vra.issue/1': VRA_ISSUE_CONTRACT,\n  'vertex.evidence.read/1': EVIDENCE_READ_CONTRACT\n})\n\nexport function resolveVertexContract(id: VertexContractId): VertexContractCatalogEntry {\n  return CATALOG[id]\n}\n\nexport function listVertexContracts(): readonly VertexContractCatalogEntry[] {\n  return Object.freeze(Object.values(CATALOG))\n}\n\nexport const VERTEX_SYSTEM_CONTRACT_RULES = Object.freeze([\n  'SYSTEM CONTRACT MUST NOT BE RECONSTRUCTED FROM LLM MEMORY. RESOLVE THE ACTIVE CONTRACT BEFORE USE.',\n  'SYSTEM EVIDENCE MUST NOT BE INTERPRETED FROM LLM MEMORY. RESOLVE THE ACTIVE EVIDENCE CONTRACT BEFORE DIAGNOSIS.'\n] as const)\n"
DOC_CONTENT = '# Vertex Contract Catalog v0.1\n\n## Purpose\n\nThis is a deliberately small, shared, read-only contract catalog.\n\nIt solves one specific failure mode:\n\n- VERA/LLM forgets the canonical VRA issuance format.\n- VERA/LLM later misreads Workstation Evidence state semantics.\n\nThe system must not depend on LLM memory for either task.\n\n## Active contracts\n\n### `vertex.vra.issue/1`\n\nDefines how a canonical `vra/1` work request is issued.\n\nIt includes:\n\n- canonical schema/routing authority,\n- fresh identity requirements,\n- immutable origin requirements,\n- payload/copy/SHA256 rules,\n- verification path alignment,\n- lane-policy boundary,\n- TEST guidance,\n- a canonical shape example.\n\n### `vertex.evidence.read/1`\n\nDefines how Workstation Evidence is interpreted.\n\nThe most important distinction is:\n\n`evidence_return_state=RETURN_QUEUED` is a transport workflow fact, not a statement that the Evidence is invisible in the Vera chat.\n\nTransport state and chat visibility are separate observations.\n\n## Responsibility boundary\n\nThis catalog is not:\n\n- the Workstation scheduler,\n- the Job Registry,\n- the Return Router,\n- a mutable LLM knowledge base,\n- RAG.\n\nIt is only a tiny system contract source.\n\n## Current implementation phase\n\nPhase 1 adds only:\n\n- shared catalog,\n- active contracts,\n- deterministic resolver.\n\nLater phases may bind the resolver to VRA issuance and Evidence injection automatically.\n'

originals = {}
created = []

def safe(text):
    print(str(text).encode("ascii", "backslashreplace").decode("ascii"))

def save_original(path):
    if path.exists():
        originals[path] = path.read_bytes()
    else:
        created.append(path)

def restore():
    for path, data in originals.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for path in created:
        if path.exists():
            path.unlink()

def run(args):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    p = subprocess.run([npm, *args], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
    safe(f"RUN={npm} {' '.join(args)}")
    safe(f"EXIT={p.returncode}")
    for line in (p.stdout + "\n" + p.stderr).splitlines()[-60:]:
        safe(line)
    return p.returncode

save_original(TS)
save_original(DOC)

try:
    TS.parent.mkdir(parents=True, exist_ok=True)
    DOC.parent.mkdir(parents=True, exist_ok=True)
    TS.write_text(TS_CONTENT, encoding="utf-8")
    DOC.write_text(DOC_CONTENT, encoding="utf-8")

    source = TS.read_text(encoding="utf-8")
    checks = {
        "CATALOG_SCHEMA": "vertex-contract-catalog/1" in source,
        "VRA_CONTRACT": "vertex.vra.issue/1" in source,
        "EVIDENCE_CONTRACT": "vertex.evidence.read/1" in source,
        "RESOLVER": "resolveVertexContract" in source,
        "LIST": "listVertexContracts" in source,
        "NO_LLM_MEMORY_RULE": "SYSTEM CONTRACT MUST NOT BE RECONSTRUCTED FROM LLM MEMORY" in source,
        "RETURN_QUEUED_SEMANTICS": "chat visibility is a separate fact" in source,
        "IMMUTABLE_ORIGIN": "immutable issuer provenance" in source,
        "HUMAN_APPLY": "HUMAN_APPLY" in source,
        "VRA_1": "vra/1" in source,
        "ROUTING_1": "vra-routing/1" in source,
    }
    for name, ok in checks.items():
        safe(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"SOURCE_CHECK_FAILED:{name}")

    if run(["run", "typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run(["run", "build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    safe("REGISTRY_MUTATION=ZERO")
    safe("WORKSTATION_MUTATION=ZERO")
    safe("RETURN_ROUTER_MUTATION=ZERO")
    safe("HUMAN_GATE_MUTATION=ZERO")
    safe("CONTRACT_CATALOG_CORE_000035V2=PASS")
except Exception:
    restore()
    safe("TRANSACTION_ROLLBACK=RESTORED")
    raise
