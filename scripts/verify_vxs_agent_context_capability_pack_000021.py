from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
AGENT = PORTAL / "src/main/shell/vxs/vxs-agent-context-capabilities.ts"
JOB = PORTAL / "src/main/shell/vxs/vxs-job-intelligence-capabilities.ts"
FAILURE = PORTAL / "src/main/shell/vxs/vxs-failure-intelligence-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("AGENT", AGENT),
    ("JOB", JOB),
    ("FAILURE", FAILURE),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
at = AGENT.read_text(encoding="utf-8") if AGENT.is_file() else ""
jt = JOB.read_text(encoding="utf-8") if JOB.is_file() else ""
ft = FAILURE.read_text(encoding="utf-8") if FAILURE.is_file() else ""

ck("REGISTRY_MARKER", "VXS_AGENT_CONTEXT_CAPABILITY_PACK_000021" in rt)
ck("AGENT_MARKER", "VXS_AGENT_CONTEXT_CAPABILITY_PACK_000021" in at)
ck("MODULE_IMPORT", "createVxsAgentContextCommands" in rt)

for token in (
    "vxs context",
    "vxs context --json",
):
    ck("HELP_" + token.replace(" ", "_").replace("-", "_").upper(), token in rt)

for token in (
    "name: 'context'",
    "usage: 'vxs context [--json]'",
    "vxs-agent-context/1",
    "secret_env_values_included: false",
    "full_log_bodies_included: false",
    "filesystem_mutation: false",
    "network_mutation: false",
    "workstation_47832",
    "recentJobs",
):
    ck("AGENT_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("-", "_").replace("[", "").replace("]", "").upper(), token in at)

ck("BOUNDED_JOB_FILES", ".slice(-800)" in at)
ck("BOUNDED_RECENT_JOBS", ".slice(0, 12)" in at)
ck("BOUNDED_FAILURES", ".slice(0, 8)" in at)
ck("BOUNDED_CHANGED", ".slice(0, 120)" in at)
ck("NO_ENV_DUMP", "Object.entries(process.env)" not in at)
ck("NO_WRITE_FILE", "writeFile" not in at)
ck("NO_APPEND_FILE", "appendFile" not in at)
ck("NO_UNLINK", "unlink" not in at)
ck("NO_RM", "rmSync" not in at)
ck("NO_HTTP_POST", "POST" not in at)
ck("000020_PRESERVED", "VXS_JOB_INTELLIGENCE_CAPABILITY_PACK_000020" in jt)
ck("000019_PRESERVED", "VXS_FAILURE_INTELLIGENCE_CAPABILITY_PACK_000019" in ft)

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

print("VXS_AGENT_CONTEXT_CAPABILITY_PACK_000021=PASS")
raise SystemExit(0)
