from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
JOB = PORTAL / "src/main/shell/vxs/vxs-job-intelligence-capabilities.ts"
FAILURE = PORTAL / "src/main/shell/vxs/vxs-failure-intelligence-capabilities.ts"
ORCH = PORTAL / "src/main/shell/vxs/vxs-orchestration-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("JOB", JOB),
    ("FAILURE", FAILURE),
    ("ORCH", ORCH),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
jt = JOB.read_text(encoding="utf-8") if JOB.is_file() else ""
ft = FAILURE.read_text(encoding="utf-8") if FAILURE.is_file() else ""
ot = ORCH.read_text(encoding="utf-8") if ORCH.is_file() else ""

ck("REGISTRY_MARKER", "VXS_JOB_INTELLIGENCE_CAPABILITY_PACK_000020" in rt)
ck("JOB_MARKER", "VXS_JOB_INTELLIGENCE_CAPABILITY_PACK_000020" in jt)
ck("MODULE_IMPORT", "createVxsJobIntelligenceCommands" in rt)

for token in (
    "vxs jobs [n]",
    "vxs failures [n]",
    "vxs timeline <job-id>",
):
    ck("HELP_" + token.replace(" ", "_").replace("[", "").replace("]", "").replace("<", "").replace(">", "").replace("-", "_").upper(), token in rt)

for token in (
    "name: 'jobs'",
    "name: 'failures'",
    "name: 'timeline'",
    "JOB_REGISTRY_ROOT",
    ".slice(-1500)",
    "limit > 100",
    "collectRecordsWithJobId",
    "TIMELINE_MUTATION=NONE",
):
    ck("JOB_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("<", "").replace(">", "").replace("-", "_").upper(), token in jt)

ck("NO_WRITE_FILE", "writeFile" not in jt)
ck("NO_APPEND_FILE", "appendFile" not in jt)
ck("NO_UNLINK", "unlink" not in jt)
ck("NO_RM", "rmSync" not in jt)
ck("NO_HTTP_POST", "POST" not in jt)
ck("NO_REEXECUTION", "reexecute" not in jt.lower())
ck("000019_PRESERVED", "VXS_FAILURE_INTELLIGENCE_CAPABILITY_PACK_000019" in ft)
ck("000018_PRESERVED", "VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018" in ot)

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

print("VXS_JOB_INTELLIGENCE_CAPABILITY_PACK_000020=PASS")
raise SystemExit(0)
