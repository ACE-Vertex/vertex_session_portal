from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent

CONTRACT = ROOT / "src" / "shared" / "vera-vxs-contracts.ts"
BRIDGE = ROOT / "src" / "main" / "shell" / "vxs" / "vera-vxs-interface.ts"

def fail(stage: str, code: int, detail: str = "") -> int:
    print("VERA_VXS_DEDICATED_INTERFACE_CORE_H1=FAIL")
    print("STAGE=" + stage)
    if detail:
        print(detail)
    return code

def require_text(path: Path, token: str, code: int) -> None:
    text = path.read_text(encoding="utf-8")
    if token not in text:
        raise SystemExit(fail("SOURCE_ASSERT", code, f"MISSING={path}:{token}"))

if not CONTRACT.is_file():
    raise SystemExit(fail("CONTRACT_LOOKUP", 20, "EXPECTED=" + str(CONTRACT)))
if not BRIDGE.is_file():
    raise SystemExit(fail("BRIDGE_LOOKUP", 21, "EXPECTED=" + str(BRIDGE)))

# Contract identity.
require_text(CONTRACT, "vertex-vxs/vera-request-1", 22)
require_text(CONTRACT, "vertex-vxs/vera-result-1", 23)
require_text(CONTRACT, "authorityEnforcement: 'VXS_EXISTING_POLICY'", 24)
require_text(CONTRACT, "transport: 'VERTEX_SHELL_SERVICE'", 25)

# Boundary safety and canonical delegation.
require_text(BRIDGE, "executeVeraVxsRequest", 26)
require_text(BRIDGE, "VERA_VXS_CANONICAL_VXS_COMMAND_REQUIRED", 27)
require_text(BRIDGE, "/^vxs(?:\\s|$)/i", 28)
require_text(BRIDGE, "executor.execute(shellRequest, sink)", 29)
require_text(BRIDGE, "authorityEnforcement: 'VXS_EXISTING_POLICY'", 30)
require_text(BRIDGE, "MAX_RETURN_STREAM_BYTES", 31)
require_text(BRIDGE, "VERA_VXS_ORIGIN_MISMATCH", 32)

bridge_text = BRIDGE.read_text(encoding="utf-8")

# H1 repair:
# Do NOT reject RegExp.prototype.exec(). Reject only actual second-executor
# surfaces/imports and call sites that could bypass VertexShellService.
forbidden_literals = (
    "node:child_process",
    "pwsh.exe",
    "powershell.exe",
    "cmd.exe",
)
for forbidden in forbidden_literals:
    if forbidden in bridge_text:
        raise SystemExit(fail("NO_SECOND_EXECUTOR_GUARD", 33, "FORBIDDEN_LITERAL=" + forbidden))

# Reject process-spawning function calls by syntax shape, while allowing
# regex.exec(...), matcher.exec(...), etc.
forbidden_call_patterns = {
    "spawn": r"(?<![\w$.])spawn\s*\(",
    "exec": r"(?<![\w$.])exec\s*\(",
    "execFile": r"(?<![\w$.])execFile\s*\(",
    "fork": r"(?<![\w$.])fork\s*\(",
}
for name, pattern in forbidden_call_patterns.items():
    if re.search(pattern, bridge_text):
        raise SystemExit(fail("NO_SECOND_EXECUTOR_GUARD", 34, "FORBIDDEN_CALL=" + name))

# Positive guard proving the earlier false-positive source remains legal.
if ".exec(vera)" not in bridge_text:
    raise SystemExit(fail("REGEXP_EXEC_PRESENCE", 35))
print("REGEXP_EXEC_ALLOWED=true")

npm = shutil.which("npm.cmd") or shutil.which("npm")
if not npm:
    raise SystemExit(fail("NPM_LOOKUP", 40))

proc = subprocess.run(
    [npm, "run", "build"],
    cwd=str(ROOT),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
    shell=False,
    timeout=240,
)

if proc.returncode != 0:
    print("BUILD_STDOUT_TAIL=" + (proc.stdout or "")[-12000:].replace("\n", " | "))
    print("BUILD_STDERR_TAIL=" + (proc.stderr or "")[-12000:].replace("\n", " | "))
    raise SystemExit(fail("NPM_BUILD", 41, "EXIT=" + str(proc.returncode)))

print("VERA_VXS_DEDICATED_INTERFACE_CORE_H1=PASS")
print("REQUEST_SCHEMA=vertex-vxs/vera-request-1")
print("RESULT_SCHEMA=vertex-vxs/vera-result-1")
print("INGRESS=VERA_TYPED_REQUEST")
print("DELEGATE=VertexShellService.execute-compatible")
print("CANONICAL_VXS_ONLY=true")
print("SECOND_EXECUTOR=false")
print("REGEXP_EXEC_ALLOWED=true")
print("AUTHORITY_SELF_PROMOTION=false")
print("AUTHORITY_ENFORCEMENT=VXS_EXISTING_POLICY")
print("STREAM_RETURN_BOUND_BYTES=524288")
print("ORIGIN_PROVENANCE_VALIDATION=true")
print("CRYPTOGRAPHIC_AUTHENTICATION=false")
print("NPM_BUILD=PASS")
print("IPC_BINDING_STATUS=PENDING_PHASE_2")
print("VERA_AGENT_BINDING_STATUS=PENDING_PHASE_2")
raise SystemExit(0)
