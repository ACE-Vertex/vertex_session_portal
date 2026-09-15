
from pathlib import Path
import json, subprocess, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
DEV = Path(r"G:\Vertex_Project\Development")
CATALOG = ROOT / "src/shared/vertex-contract-catalog.ts"
POLICY = ROOT / "src/shared/system-policy-registry.ts"
DOC = ROOT / "docs/ARCHITECTURE/VERTEX_SYSTEM_POLICY_LAYER_PHASE1.md"

def log(v=""):
    print(str(v).encode("ascii","backslashreplace").decode("ascii"))

def read(p):
    if not p.exists():
        raise RuntimeError(f"MISSING:{p}")
    return p.read_text(encoding="utf-8-sig", errors="replace")

def write(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def run_npm(args):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    p = subprocess.run(
        [npm,*args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True
    )
    log(f"RUN={npm} {' '.join(args)}")
    log(f"EXIT={p.returncode}")
    for line in (p.stdout+"\n"+p.stderr).splitlines()[-140:]:
        log(line)
    return p.returncode

def valid_manifest(path: Path):
    try:
        if not path.is_file() or path.stat().st_size > 2_000_000:
            return None
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("schema_version") != "vra/1":
            return None
        if data.get("authority") != "HUMAN_APPLY":
            return None
        routing = data.get("routing") or {}
        if routing.get("contract_version") != "vra-routing/1":
            return None
        if not isinstance(data.get("operations"), list):
            return None
        if not isinstance(data.get("verification"), list):
            return None
        return data
    except Exception:
        return None

# Resolve the unique valid canonical manifest exactly as the verified locator did.
strong_names = {
    "VRA_CANONICAL_MANIFEST_vra-1_000150V5.json",
    "VRA_CANONICAL_MANIFEST_vra-1.json",
    "vra-canonical-manifest-vra-1.json",
    "vra_canonical_manifest_vra-1.json",
}

plausible = []
for p in DEV.rglob("*.json"):
    try:
        if not p.is_file():
            continue
        name_lower = p.name.lower()
        path_lower = str(p).lower()
        strong = p.name in strong_names
        semantic = (
            ("canonical" in name_lower and "vra" in name_lower) or
            ("vra_manifest" in path_lower and "manifest" in name_lower) or
            ("vra-manifest" in path_lower and "canonical" in name_lower)
        )
        if strong or semantic:
            plausible.append(p)
    except Exception:
        pass

dedup = []
seen = set()
for p in plausible:
    k = str(p).lower()
    if k not in seen:
        seen.add(k)
        dedup.append(p)

valid = []
for p in dedup:
    data = valid_manifest(p)
    if data is not None:
        valid.append((p, data))

if len(valid) != 1:
    raise SystemExit(f"CANONICAL_MANIFEST_UNIQUE_RESOLUTION_FAILED:{len(valid)}")

CANONICAL, canonical = valid[0]
canonical_path_forward = str(CANONICAL).replace("\\", "/")
log(f"CANONICAL_MANIFEST={canonical_path_forward}")

catalog_text = read(CATALOG)
if "vertex.vra.issue/1" not in catalog_text:
    raise SystemExit("ACTIVE_CONTRACT_CATALOG_VRA_ISSUE_MISSING")

if POLICY.exists() or DOC.exists():
    raise SystemExit("PHASE1_TARGET_ALREADY_EXISTS")

policy_ts = f"""// Vertex System Policy Layer — Phase 1 Foundation
// Source of truth: unique valid Canonical VRA Manifest resolved at install time.
// This file does not grant mutation authority.

export const SYSTEM_POLICY_REGISTRY_SCHEMA = 'vertex-system-policy-registry/1' as const

export type SystemPolicyApprovalState =
  | 'ACTIVE_CANONICAL_BASELINE'
  | 'PROPOSED'
  | 'REJECTED'
  | 'SUPERSEDED'

export interface SystemPolicyProvenance {{
  readonly kind: 'CANONICAL_IMPORT'
  readonly canonical_manifest: string
  readonly contract_catalog_id: 'vertex.vra.issue/1'
}}

export interface VraIssuePolicyContract {{
  readonly schema_version: 'vra/1'
  readonly authority: 'HUMAN_APPLY'
  readonly routing: {{
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
  }}
  readonly identity: {{
    readonly fresh_per_issuance: readonly ['artifact_id', 'job_id', 'correlation_id']
    readonly immutable_origin: readonly ['origin_vera', 'origin_session', 'origin_window']
  }}
  readonly operations: {{
    readonly allowed: readonly ['copy']
    readonly source_prefix: 'payload/'
    readonly path_separator: '/'
    readonly sha256: 'actual-64hex-lowercase'
  }}
  readonly verification: {{
    readonly execute_copied_destination: true
  }}
  readonly test_work: {{
    readonly card_kind: 'TEST'
    readonly prefer_disposable_read_only: true
  }}
  readonly forbidden: readonly [
    'unknown_schema_fields',
    'custom_execution_envelopes',
    'custom_evidence_formats',
    'invented_operations'
  ]
}}

export interface SystemPolicyRecord<TContract> {{
  readonly policy_id: string
  readonly policy_version: string
  readonly active_version: string
  readonly approval_state: SystemPolicyApprovalState
  readonly compatibility: readonly string[]
  readonly provenance: SystemPolicyProvenance
  readonly contract: TContract
}}

export const VRA_ISSUE_POLICY_1_0_0 = {{
  policy_id: 'vertex.vra.issue',
  policy_version: '1.0.0',
  active_version: '1.0.0',
  approval_state: 'ACTIVE_CANONICAL_BASELINE',
  compatibility: ['vra/1', 'vra-routing/1'] as const,
  provenance: {{
    kind: 'CANONICAL_IMPORT',
    canonical_manifest: {json.dumps(canonical_path_forward)},
    contract_catalog_id: 'vertex.vra.issue/1'
  }},
  contract: {{
    schema_version: 'vra/1',
    authority: 'HUMAN_APPLY',
    routing: {{
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
    }},
    identity: {{
      fresh_per_issuance: ['artifact_id', 'job_id', 'correlation_id'] as const,
      immutable_origin: ['origin_vera', 'origin_session', 'origin_window'] as const
    }},
    operations: {{
      allowed: ['copy'] as const,
      source_prefix: 'payload/',
      path_separator: '/',
      sha256: 'actual-64hex-lowercase'
    }},
    verification: {{
      execute_copied_destination: true
    }},
    test_work: {{
      card_kind: 'TEST',
      prefer_disposable_read_only: true
    }},
    forbidden: [
      'unknown_schema_fields',
      'custom_execution_envelopes',
      'custom_evidence_formats',
      'invented_operations'
    ] as const
  }}
}} as const satisfies SystemPolicyRecord<VraIssuePolicyContract>

const POLICY_RECORDS = [VRA_ISSUE_POLICY_1_0_0] as const

export type KnownSystemPolicyRecord = (typeof POLICY_RECORDS)[number]

export function listSystemPolicyRecords(): readonly KnownSystemPolicyRecord[] {{
  return POLICY_RECORDS
}}

export function getSystemPolicyRecord(
  policyId: string,
  policyVersion: string
): KnownSystemPolicyRecord | null {{
  return POLICY_RECORDS.find(
    record => record.policy_id === policyId && record.policy_version === policyVersion
  ) ?? null
}}

export const SYSTEM_POLICY_PHASE1_GUARDS = [
  'POLICY_NOT_OWNED_BY_LLM',
  'NO_POLICY_MUTATION_API_IN_PHASE1',
  'VRA_REGISTRY_RESPONSIBILITY_REMAINS_SEPARATE',
  'WORKSTATION_EXECUTION_AUTHORITY_REMAINS_SEPARATE',
  'HUMAN_FINAL_AUTHORITY'
] as const
"""

doc_md = f"""# Vertex System Policy Layer — Phase 1

Status: Foundation

## Responsibility boundary

- System Policy Registry: rules authority
- Vertex VRA Registry: responsibility / identity / lifecycle ledger
- Vertex Workstation: execution authority
- VRA: transport ticket
- Evidence: proof
- VERA: reasoning / proposal
- Human: final authority

## Active baseline

Policy:

`vertex.vra.issue/1.0.0`

Resolved canonical source:

`{canonical_path_forward}`

Existing Contract Catalog identity:

`vertex.vra.issue/1`

## Phase 1 scope

Phase 1 is read-only. It intentionally does not provide:

- Policy Resolver IPC
- Deterministic VRA Validator
- Deterministic VRA Builder
- Policy Change Proposal flow
- Policy Registrar
- Policy activation writer
- migration engine
- System Change Gate

The System Policy Registry remains logically separate from the VRA Registry.
"""

try:
    write(POLICY, policy_ts)
    write(DOC, doc_md)

    now = read(POLICY)
    checks = {
        "POLICY_SCHEMA": "vertex-system-policy-registry/1" in now,
        "POLICY_ID": "vertex.vra.issue" in now,
        "POLICY_VERSION": "1.0.0" in now,
        "CANONICAL_PROVENANCE": canonical_path_forward in now,
        "VRA_SCHEMA": "vra/1" in now,
        "AUTHORITY": "HUMAN_APPLY" in now,
        "ROUTING": "vra-routing/1" in now,
        "COPY_ONLY": "allowed: ['copy'] as const" in now,
        "PAYLOAD_PREFIX": "payload/" in now,
        "RETURN_CHANNEL": "vertex-session-portal:return-queue" in now,
        "LANE_AUTHORITY": "Vertex Workstation" in now,
        "LITERAL_TUPLES": "lane_policy_allowed: ['ANY', 'PREFER'] as const" in now,
        "NO_MUTATOR": "NO_POLICY_MUTATION_API_IN_PHASE1" in now,
        "SEPARATE_REGISTRY": "VRA_REGISTRY_RESPONSIBILITY_REMAINS_SEPARATE" in now,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    if run_npm(["run","typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")

    if run_npm(["run","build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("PHASE=SYSTEM_POLICY_REGISTRY_FOUNDATION")
    log("POLICY_COUNT=1")
    log("ACTIVE_POLICY=vertex.vra.issue/1.0.0")
    log("TYPE_MODEL=LITERAL_TUPLES_AS_CONST")
    log("POLICY_RESOLVER=NOT_YET")
    log("POLICY_VALIDATOR=NOT_YET")
    log("POLICY_BUILDER=NOT_YET")
    log("POLICY_REGISTRAR=NOT_YET")
    log("VRA_REGISTRY_SCHEMA_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("HUMAN_GATE_CHANGE=ZERO")
    log("SYSTEM_POLICY_REGISTRY_FOUNDATION_000055V2=PASS")

except Exception:
    for p in (POLICY, DOC):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
    log("TRANSACTION_ROLLBACK=REMOVED_PHASE1_FILES")
    raise
