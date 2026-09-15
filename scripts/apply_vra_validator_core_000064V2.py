
from pathlib import Path
import shutil, subprocess, sys, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
POLICY = ROOT / "src/shared/system-policy-registry.ts"
VALIDATOR = ROOT / "src/shared/vra-policy-validator.ts"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / "EVIDENCE" / "VRA_VALIDATOR_CORE_000064V2" / STAMP
VALIDATOR_TS = 'import { resolveActiveSystemPolicy } from \'./system-policy-registry\'\n\n// VERTEX_VRA_POLICY_VALIDATOR_CORE_000064V2\n\nexport interface VraValidationIssue {\n  readonly code: string\n  readonly path: string\n  readonly message: string\n}\n\nexport interface VraValidationResult {\n  readonly valid: boolean\n  readonly policy_id: string\n  readonly policy_version: string | null\n  readonly issues: readonly VraValidationIssue[]\n}\n\ntype JsonObject = Record<string, unknown>\n\nfunction isObject(value: unknown): value is JsonObject {\n  return typeof value === \'object\' && value !== null && !Array.isArray(value)\n}\n\nfunction isLowerHex64(value: unknown): value is string {\n  return typeof value === \'string\' && /^[0-9a-f]{64}$/.test(value)\n}\n\nfunction issue(\n  code: string,\n  path: string,\n  message: string\n): VraValidationIssue {\n  return { code, path, message }\n}\n\nexport function validateVraAgainstActivePolicy(\n  manifest: unknown\n): VraValidationResult {\n  const policy = resolveActiveSystemPolicy(\'vertex.vra.issue\')\n\n  if (!policy) {\n    return {\n      valid: false,\n      policy_id: \'vertex.vra.issue\',\n      policy_version: null,\n      issues: [\n        issue(\n          \'POLICY_NOT_AVAILABLE\',\n          \'$\',\n          \'Active vertex.vra.issue policy is not available.\'\n        )\n      ]\n    }\n  }\n\n  const issues: VraValidationIssue[] = []\n  const contract = policy.contract\n\n  if (!isObject(manifest)) {\n    issues.push(issue(\'MANIFEST_NOT_OBJECT\', \'$\', \'Manifest must be an object.\'))\n    return {\n      valid: false,\n      policy_id: policy.policy_id,\n      policy_version: policy.policy_version,\n      issues\n    }\n  }\n\n  if (manifest.schema_version !== contract.schema_version) {\n    issues.push(\n      issue(\n        \'SCHEMA_VERSION_MISMATCH\',\n        \'$.schema_version\',\n        `Expected ${contract.schema_version}.`\n      )\n    )\n  }\n\n  if (manifest.authority !== contract.authority) {\n    issues.push(\n      issue(\n        \'AUTHORITY_MISMATCH\',\n        \'$.authority\',\n        `Expected ${contract.authority}.`\n      )\n    )\n  }\n\n  const artifactId = manifest.artifact_id\n  if (typeof artifactId !== \'string\' || artifactId.trim().length === 0) {\n    issues.push(issue(\'ARTIFACT_ID_REQUIRED\', \'$.artifact_id\', \'artifact_id is required.\'))\n  }\n\n  const routing = manifest.routing\n  if (!isObject(routing)) {\n    issues.push(issue(\'ROUTING_REQUIRED\', \'$.routing\', \'routing object is required.\'))\n  } else {\n    if (routing.contract_version !== contract.routing.contract_version) {\n      issues.push(\n        issue(\n          \'ROUTING_CONTRACT_MISMATCH\',\n          \'$.routing.contract_version\',\n          `Expected ${contract.routing.contract_version}.`\n        )\n      )\n    }\n\n    for (const field of contract.routing.required) {\n      const value = routing[field]\n      if (typeof value !== \'string\' || value.trim().length === 0) {\n        issues.push(\n          issue(\n            \'ROUTING_FIELD_REQUIRED\',\n            `$.routing.${field}`,\n            `${field} is required.`\n          )\n        )\n      }\n    }\n\n    if (routing.return_channel !== contract.routing.return_channel) {\n      issues.push(\n        issue(\n          \'RETURN_CHANNEL_MISMATCH\',\n          \'$.routing.return_channel\',\n          `Expected ${contract.routing.return_channel}.`\n        )\n      )\n    }\n\n    const lanePolicy = routing.lane_policy\n    if (\n      typeof lanePolicy !== \'string\' ||\n      !contract.routing.lane_policy_allowed.includes(\n        lanePolicy as (typeof contract.routing.lane_policy_allowed)[number]\n      )\n    ) {\n      issues.push(\n        issue(\n          \'LANE_POLICY_NOT_ALLOWED\',\n          \'$.routing.lane_policy\',\n          `Allowed values: ${contract.routing.lane_policy_allowed.join(\', \')}.`\n        )\n      )\n    }\n  }\n\n  const operations = manifest.operations\n  if (!Array.isArray(operations) || operations.length === 0) {\n    issues.push(issue(\'OPERATIONS_REQUIRED\', \'$.operations\', \'operations must be non-empty.\'))\n  } else {\n    operations.forEach((raw, index) => {\n      const path = `$.operations[${index}]`\n      if (!isObject(raw)) {\n        issues.push(issue(\'OPERATION_NOT_OBJECT\', path, \'Operation must be an object.\'))\n        return\n      }\n\n      if (raw.op !== \'copy\') {\n        issues.push(issue(\'OPERATION_NOT_ALLOWED\', `${path}.op`, \'Only copy is allowed.\'))\n      }\n\n      if (\n        typeof raw.source !== \'string\' ||\n        !raw.source.startsWith(contract.operations.source_prefix) ||\n        raw.source.includes(\'\\\\\')\n      ) {\n        issues.push(\n          issue(\n            \'SOURCE_PATH_INVALID\',\n            `${path}.source`,\n            `source must start with ${contract.operations.source_prefix} and use \'/\'.`\n          )\n        )\n      }\n\n      if (typeof raw.destination !== \'string\' || raw.destination.length === 0 || raw.destination.includes(\'\\\\\')) {\n        issues.push(\n          issue(\n            \'DESTINATION_PATH_INVALID\',\n            `${path}.destination`,\n            "destination must be non-empty and use \'/\'."\n          )\n        )\n      }\n\n      if (!isLowerHex64(raw.sha256)) {\n        issues.push(\n          issue(\n            \'SHA256_INVALID\',\n            `${path}.sha256`,\n            \'sha256 must be actual lowercase 64-character hexadecimal.\'\n          )\n        )\n      }\n    })\n  }\n\n  const verification = manifest.verification\n  if (!Array.isArray(verification) || verification.length === 0) {\n    issues.push(\n      issue(\'VERIFICATION_REQUIRED\', \'$.verification\', \'verification must be non-empty.\')\n    )\n  } else {\n    const destinations = new Set<string>()\n    if (Array.isArray(operations)) {\n      for (const raw of operations) {\n        if (isObject(raw) && typeof raw.destination === \'string\') {\n          destinations.add(raw.destination)\n        }\n      }\n    }\n\n    verification.forEach((raw, index) => {\n      const path = `$.verification[${index}]`\n      if (!isObject(raw)) {\n        issues.push(issue(\'VERIFICATION_NOT_OBJECT\', path, \'Verification must be an object.\'))\n        return\n      }\n\n      if (typeof raw.program !== \'string\' || raw.program.length === 0) {\n        issues.push(issue(\'VERIFICATION_PROGRAM_REQUIRED\', `${path}.program`, \'program is required.\'))\n      }\n\n      if (!Array.isArray(raw.args) || raw.args.length === 0) {\n        issues.push(issue(\'VERIFICATION_ARGS_REQUIRED\', `${path}.args`, \'args must be non-empty.\'))\n        return\n      }\n\n      const args = raw.args.filter((arg): arg is string => typeof arg === \'string\')\n      const executesDestination = args.some(arg => destinations.has(arg))\n      if (!executesDestination) {\n        issues.push(\n          issue(\n            \'VERIFICATION_DESTINATION_MISMATCH\',\n            `${path}.args`,\n            \'verification must execute a copied destination path.\'\n          )\n        )\n      }\n    })\n  }\n\n  return {\n    valid: issues.length === 0,\n    policy_id: policy.policy_id,\n    policy_version: policy.policy_version,\n    issues\n  }\n}\n'

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
        [npm, *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True
    )
    log(f"RUN={npm} {' '.join(args)}")
    log(f"EXIT={p.returncode}")
    for line in (p.stdout + "\n" + p.stderr).splitlines()[-180:]:
        log(line)
    return p.returncode

policy = read(POLICY)
if "resolveActiveSystemPolicy" not in policy:
    raise SystemExit("PHASE2_POLICY_RESOLVER_MISSING")
if "vertex.vra.issue" not in policy or "1.0.0" not in policy:
    raise SystemExit("ACTIVE_VRA_POLICY_MISSING")

if VALIDATOR.exists():
    raise SystemExit("VRA_POLICY_VALIDATOR_ALREADY_PRESENT")

BACKUP.mkdir(parents=True, exist_ok=True)

try:
    write(VALIDATOR, VALIDATOR_TS)

    now = read(VALIDATOR)
    checks = {
        "POLICY_RESOLUTION": "resolveActiveSystemPolicy('vertex.vra.issue')" in now,
        "SCHEMA_CHECK": "SCHEMA_VERSION_MISMATCH" in now,
        "AUTHORITY_CHECK": "AUTHORITY_MISMATCH" in now,
        "ROUTING_CHECK": "ROUTING_CONTRACT_MISMATCH" in now,
        "RETURN_CHANNEL_CHECK": "RETURN_CHANNEL_MISMATCH" in now,
        "LANE_POLICY_CHECK": "LANE_POLICY_NOT_ALLOWED" in now,
        "COPY_ONLY_CHECK": "OPERATION_NOT_ALLOWED" in now,
        "PAYLOAD_PREFIX_CHECK": "SOURCE_PATH_INVALID" in now,
        "SHA_CHECK": "SHA256_INVALID" in now,
        "VERIFY_DESTINATION_CHECK": "VERIFICATION_DESTINATION_MISMATCH" in now,
        "NO_MUTATION": "writeFile" not in now and "ipcMain" not in now,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    if run_npm(["run", "typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")

    if run_npm(["run", "build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("PHASE=DETERMINISTIC_VRA_VALIDATOR_CORE")
    log("POLICY_SOURCE=vertex.vra.issue/1.0.0")
    log("LIVE_DISPATCH_ENFORCEMENT=NOT_YET")
    log("WRITE_API=ZERO")
    log("REGISTRAR=ZERO")
    log("HUMAN_GATE_CHANGE=ZERO")
    log("VRA_REGISTRY_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("VRA_VALIDATOR_CORE_000064V2=PASS")

except Exception:
    try:
        if VALIDATOR.exists():
            VALIDATOR.unlink()
    except Exception:
        pass
    log("TRANSACTION_ROLLBACK=REMOVED_VALIDATOR_CORE")
    raise
