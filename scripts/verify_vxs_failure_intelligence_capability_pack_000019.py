from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
FAILURE = PORTAL / "src/main/shell/vxs/vxs-failure-intelligence-capabilities.ts"
ORCH = PORTAL / "src/main/shell/vxs/vxs-orchestration-capabilities.ts"
RUNTIME = PORTAL / "src/main/shell/vxs/vxs-runtime-diagnostics-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("FAILURE", FAILURE),
    ("ORCH", ORCH),
    ("RUNTIME", RUNTIME),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
ft = FAILURE.read_text(encoding="utf-8") if FAILURE.is_file() else ""
ot = ORCH.read_text(encoding="utf-8") if ORCH.is_file() else ""
xt = RUNTIME.read_text(encoding="utf-8") if RUNTIME.is_file() else ""

ck("REGISTRY_MARKER", "VXS_FAILURE_INTELLIGENCE_CAPABILITY_PACK_000019" in rt)
ck("FAILURE_MARKER", "VXS_FAILURE_INTELLIGENCE_CAPABILITY_PACK_000019" in ft)
ck("MODULE_IMPORT", "createVxsFailureIntelligenceCommands" in rt)
ck("HELP_TRIAGE", "vxs triage <job-id>" in rt)
ck("COMMAND_TRIAGE", "name: 'triage'" in ft)

for token in (
    "INSPECTOR_REJECT",
    "SHA_MISMATCH",
    "APPROVAL_REJECT",
    "ROUTING_REJECT",
    "IDENTITY_CONFLICT",
    "VERIFY_FAILED",
    "REGISTERED",
    "ALLOCATED",
    "RETURN_QUEUED",
    "RETURNED",
    "NOT_FOUND",
):
    ck("CLASS_" + token, token in ft)

ck("PORTAL_METADATA_SCAN", "vra-dispatch" in ft)
ck("JOB_REGISTRY_SCAN", "headless\\\\job-registry" in ft)
ck("EVIDENCE_SCAN", "runtime\\\\lanes" in ft)
ck("BOUNDED_REGISTRY", ".slice(-1000)" in ft)
ck("BOUNDED_EVIDENCE", "maxFiles = 1600" in ft)
ck("JOB_ID_VALIDATION", "JOB_ID_PATTERN" in ft)
ck("NO_WRITE_FILE", "writeFile" not in ft)
ck("NO_APPEND_FILE", "appendFile" not in ft)
ck("NO_UNLINK", "unlink" not in ft)
ck("NO_RM", "rmSync" not in ft)
ck("NO_HTTP_MUTATION", "POST" not in ft)
ck("000018_PRESERVED", "VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018" in ot)
ck("000016_PRESERVED", "VXS_RUNTIME_DIAGNOSTICS_CAPABILITY_PACK_000016" in xt)

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

cp = subprocess.run(
    ["npm.cmd", "run", "typecheck"],
    cwd=PORTAL,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=180,
)
print("TYPECHECK_EXIT=" + str(cp.returncode))
if cp.stdout:
    print("TYPECHECK_STDOUT_TAIL=" + " | ".join(cp.stdout.splitlines()[-20:]))
if cp.stderr:
    print("TYPECHECK_STDERR_TAIL=" + " | ".join(cp.stderr.splitlines()[-20:]))

if cp.returncode != 0:
    raise SystemExit(cp.returncode)

print("VXS_FAILURE_INTELLIGENCE_CAPABILITY_PACK_000019=PASS")
raise SystemExit(0)
