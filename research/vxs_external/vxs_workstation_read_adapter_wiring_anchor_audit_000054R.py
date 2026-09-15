from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
TARGET = ROOT / "src/main/shell/vxs/vxs-vertex-capabilities.ts"
ADAPTER = ROOT / "src/main/shell/vxs/vxs-workstation-read-adapter.ts"

print("VXS_WORKSTATION_READ_ADAPTER_WIRING_ANCHOR_AUDIT_000054R=BEGIN")
print("MODE=READ_ONLY")
print("PRODUCTION_MUTATION=NONE")

if not TARGET.is_file():
    print("TARGET_MISSING")
    raise SystemExit(61)
if not ADAPTER.is_file():
    print("ADAPTER_MISSING")
    raise SystemExit(62)

text = TARGET.read_text(encoding="utf-8", errors="strict")
adapter = ADAPTER.read_text(encoding="utf-8", errors="strict")

target_sha = sha256(TARGET.read_bytes()).hexdigest()
adapter_sha = sha256(ADAPTER.read_bytes()).hexdigest()

print(f"TARGET={TARGET}")
print(f"TARGET_SHA256={target_sha}")
print(f"TARGET_BYTES={TARGET.stat().st_size}")
print(f"ADAPTER={ADAPTER}")
print(f"ADAPTER_SHA256={adapter_sha}")
print(f"ADAPTER_BYTES={ADAPTER.stat().st_size}")

required = {
    "BASE_URL": "const WORKSTATION_BASE_URL = 'http://127.0.0.1:47832'",
    "GET_JSON_ROUTE": "function getJsonRoute(",
    "WORKSTATION_COMMAND": "function workstationCommand(",
    "EVIDENCE_COMMAND": "function evidenceCommand(",
    "WORKSTATION_HEALTH": "return getJsonRoute(\n      '/v1/health'",
    "WORKSTATION_SAFETY": "return getJsonRoute(\n      '/v1/safety'",
    "WORKSTATION_JOB": "return getJsonRoute(\n      `/v1/jobs/${encodeURIComponent(jobId)}`",
    "EVIDENCE_JOB": "return getJsonRoute(\n    `/v1/jobs/${encodeURIComponent(jobId)}/evidence`",
    "VALID_JOB_ID": "function validJobId(",
    "PORTAL_ROOT": "const PORTAL_ROOT = 'G:\\\\Vertex_Project\\\\Development\\\\vertex_session_portal'",
}

failed = []
for name, marker in required.items():
    count = text.count(marker)
    print(f"ANCHOR_{name}_COUNT={count}")
    if count != 1:
        failed.append(f"{name}:{count}")

already = {
    "ADAPTER_IMPORT": "vxs-workstation-read-adapter" in text,
    "ADAPTER_INSTANCE": "vxsWorkstationReadAdapter" in text,
}
for name, present in already.items():
    print(f"{name}={'PRESENT' if present else 'ABSENT'}")

if any(already.values()):
    print("WIRING_ALREADY_PRESENT_OR_PARTIAL")
    raise SystemExit(51)

adapter_required = {
    "CONTRACT": "vertex-vxs/workstation-read-adapter-1",
    "HEALTH_METHOD": "health(): VxsCommandDispatchResult",
    "SAFETY_METHOD": "safety(): VxsCommandDispatchResult",
    "JOB_METHOD": "job(jobId: string): VxsCommandDispatchResult",
    "EVIDENCE_METHOD": "evidence(jobId: string): VxsCommandDispatchResult",
}
for name, marker in adapter_required.items():
    count = adapter.count(marker)
    print(f"ADAPTER_{name}_COUNT={count}")
    if count != 1:
        failed.append(f"ADAPTER_{name}:{count}")

# Capture bounded function signatures, not whole source.
for fn in ("workstationCommand", "evidenceCommand", "getJsonRoute", "validJobId"):
    m = re.search(rf"function\s+{fn}\s*\([^)]*\)", text, re.S)
    print(f"SIGNATURE_{fn}=" + (re.sub(r"\s+", " ", m.group(0)) if m else "MISSING"))

if failed:
    print("FAILED=" + ",".join(failed))
    raise SystemExit(71)

print("CURRENT_WIRING=LEGACY_INLINE_HTTP_READ")
print("TARGET_PATCH_SCOPE=IMPORT_PLUS_WORKSTATION_COMMAND_PLUS_EVIDENCE_COMMAND")
print("REMOVE_DUPLICATE_HELPERS_AFTER_REWIRE=GET_JSON_ROUTE_VALID_JOB_ID_BASE_URL_ONLY_IF_UNREFERENCED")
print("PRESERVE=RAY,VRA,COMMAND_REGISTRY,WORKSPACE_DETECTOR,PWSH_COMPATIBILITY")
print("NEXT=HASH_GUARDED_LIMITED_REWIRE")
print("VXS_WORKSTATION_READ_ADAPTER_WIRING_ANCHOR_AUDIT_000054R=PASS")
raise SystemExit(0)
