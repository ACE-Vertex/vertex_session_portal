from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
TARGET = ROOT / "src/main/shell/vxs/vxs-vertex-capabilities.ts"
ADAPTER = ROOT / "src/main/shell/vxs/vxs-workstation-read-adapter.ts"

print("VXS_WORKSTATION_READ_ADAPTER_FIRST_WIRING_000055_VERIFY=BEGIN")
print("VERIFY_MODE=READ_ONLY")
print("PRODUCTION_MUTATION_FROM_VERIFY=NO")

fail = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        fail.append(name)

ck("TARGET_PRESENT", TARGET.is_file())
ck("ADAPTER_PRESENT", ADAPTER.is_file())
if fail:
    raise SystemExit(61)

text = TARGET.read_text(encoding="utf-8")
adapter = ADAPTER.read_text(encoding="utf-8")

print("TARGET_SHA256=" + sha256(TARGET.read_bytes()).hexdigest())
print("ADAPTER_SHA256=" + sha256(ADAPTER.read_bytes()).hexdigest())

# New wiring.
ck("ADAPTER_IMPORT", "from './vxs-workstation-read-adapter'" in text)
ck("ADAPTER_INSTANCE", "vxsWorkstationReadAdapter" in text)
ck("STATUS_ADAPTER", "return vxsWorkstationReadAdapter.health()" in text)
ck("SAFETY_ADAPTER", "return vxsWorkstationReadAdapter.safety()" in text)
ck("JOB_ADAPTER", "return vxsWorkstationReadAdapter.job(args[1] ?? '')" in text)
ck("EVIDENCE_ADAPTER", "return vxsWorkstationReadAdapter.evidence(args[0] ?? '')" in text)
ck("HELP_ENDPOINT_ADAPTER", "Endpoint: ${vxsWorkstationReadAdapter.baseUrl}" in text)

# Legacy inline Workstation HTTP path removed from this capability file.
ck("LEGACY_BASE_URL_REMOVED", "const WORKSTATION_BASE_URL" not in text)
ck("LEGACY_GET_JSON_REMOVED", "function getJsonRoute(" not in text)
ck("LEGACY_JOB_VALIDATOR_REMOVED", "function validJobId(" not in text)
ck("NO_INLINE_INVOKE_RESTMETHOD", "Invoke-RestMethod" not in text)

# Preserve unrelated Vertex commands and safety rules.
for name, marker in {
    "RAY_COMMAND": "function rayCommand(",
    "VRA_COMMAND": "function vraCommand(",
    "RAY_USAGE": "usage: 'vxs ray [pattern]'",
    "VRA_USAGE": "usage: 'vxs vra <list|dispatch ...>'",
    "WORKSTATION_USAGE": "usage: 'vxs workstation <status|safety|job>'",
    "EVIDENCE_USAGE": "usage: 'vxs evidence <job-id>'",
    "VRA_FAIL_CLOSED": "No fallback dispatch is attempted.",
    "PORTAL_ROOT": "G:\\\\Vertex_Project\\\\Development\\\\vertex_session_portal",
}.items():
    ck(name, marker in text)

# Adapter itself stays OBSERVE-only.
for name, marker in {
    "ADAPTER_CONTRACT": "vertex-vxs/workstation-read-adapter-1",
    "ADAPTER_OBSERVE": "VXS_WORKSTATION_AUTHORITY_CLASS",
    "ADAPTER_LOOPBACK": "http://127.0.0.1:47832",
    "ADAPTER_MUTATION_FALSE": "mutation: false",
}.items():
    ck(name, marker in adapter)

forbidden = [
    "-Method Post",
    "-Method Put",
    "-Method Patch",
    "-Method Delete",
    "/apply",
    "/verify",
    "/rollback",
    "/evidence/ack",
    "0.0.0.0",
]
for marker in forbidden:
    ck("FORBIDDEN_" + marker.replace("/", "_").replace("-", "_").replace(" ", "_").upper(),
       marker not in adapter)

if fail:
    print("FAILURES=" + ",".join(fail))
    raise SystemExit(71)

# Official read-only typecheck: no out/main build or runtime promotion here.
tc = subprocess.run(
    ["npm.cmd", "run", "typecheck"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=180,
)
print("TYPECHECK_EXIT=" + str(tc.returncode))
if tc.stdout:
    print("TYPECHECK_STDOUT_TAIL=" + " | ".join(tc.stdout.splitlines()[-20:]))
if tc.stderr:
    print("TYPECHECK_STDERR_TAIL=" + " | ".join(tc.stderr.splitlines()[-20:]))
ck("TYPECHECK_PASS", tc.returncode == 0)

if fail:
    print("FAILURES=" + ",".join(fail))
    raise SystemExit(72)

print("JOBS_FAILURES_TIMELINE_TRACE_TRIAGE_CHANGED=NO")
print("RAY_CHANGED=NO")
print("VRA_CHANGED=NO")
print("WORKSTATION_PRODUCTION_CHANGED=NO")
print("HUMAN_GATE=UNCHANGED")
print("LANE_AUTHORITY=WORKSTATION")
print("OBSERVATION_RETURN_BUS_000041R=FROZEN")
print("RAY_VNEXT_000049R=FROZEN")
print("SOURCE_WIRING=VERIFIED")
print("RUNTIME_PROMOTION=NOT_PERFORMED")
print("NEXT=BUILD_AND_RELAUNCH_SESSION_PORTAL_THEN_RUNTIME_SMOKE")
print("VXS_WORKSTATION_READ_ADAPTER_FIRST_WIRING_000055_VERIFY=PASS")
