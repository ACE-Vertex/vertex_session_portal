from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
CONTEXT = PORTAL / "src/main/shell/vxs/vxs-agent-context-capabilities.ts"
DECISION = PORTAL / "src/main/shell/vxs/vxs-agent-decision-capabilities.ts"
JOB = PORTAL / "src/main/shell/vxs/vxs-job-intelligence-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, p in (
    ("REGISTRY", REGISTRY),
    ("CONTEXT", CONTEXT),
    ("DECISION", DECISION),
    ("JOB", JOB),
):
    ck(name + "_PRESENT", p.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
ct = CONTEXT.read_text(encoding="utf-8") if CONTEXT.is_file() else ""
dt = DECISION.read_text(encoding="utf-8") if DECISION.is_file() else ""
jt = JOB.read_text(encoding="utf-8") if JOB.is_file() else ""

ck("REGISTRY_MARKER", "VXS_AGENT_DECISION_CAPABILITY_PACK_000022" in rt)
ck("CONTEXT_MARKER", "VXS_AGENT_DECISION_CAPABILITY_PACK_000022" in ct)
ck("DECISION_MARKER", "VXS_AGENT_DECISION_CAPABILITY_PACK_000022" in dt)
ck("CONTEXT_EXPORT", "export interface AgentContextSnapshot" in ct)
ck("CONTEXT_BUILDER_EXPORT", "export function buildVxsAgentContextSnapshot" in ct)
ck("DECISION_REUSES_CONTEXT", "buildVxsAgentContextSnapshot" in dt)
ck("MODULE_IMPORT", "createVxsAgentDecisionCommands" in rt)

for token in (
    "vxs readiness",
    "vxs readiness --json",
    "vxs recommend",
    "vxs recommend --json",
):
    ck("HELP_" + token.replace(" ", "_").replace("-", "_").upper(), token in rt)

for token in (
    "vxs-agent-readiness/1",
    "vxs-agent-recommendations/1",
    "TRIAGE_LATEST_FAILURE",
    "CHECK_RUNTIME",
    "CHECK_WORKSTATION",
    "PLAN_CHANGED_VERIFY",
    "RUN_CHANGED_VERIFY",
    "PREFLIGHT",
    "RAY_WORKSPACE",
    "READINESS_EXECUTION=NONE",
    "RECOMMENDATION_EXECUTION=NONE",
):
    ck("DECISION_" + token.replace(" ", "_").replace("-", "_").replace("/", "_").upper(), token in dt)

ck("NO_SPAWN_IN_DECISION", "spawnSync" not in dt)
ck("NO_WRITE_FILE", "writeFile" not in dt)
ck("NO_APPEND_FILE", "appendFile" not in dt)
ck("NO_UNLINK", "unlink" not in dt)
ck("NO_RM", "rmSync" not in dt)
ck("NO_HTTP_POST", "POST" not in dt)
ck("NO_REEXECUTION", "reexecute" not in dt.lower())
ck("000021_PRESERVED", "VXS_AGENT_CONTEXT_CAPABILITY_PACK_000021" in ct)
ck("000020_PRESERVED", "VXS_JOB_INTELLIGENCE_CAPABILITY_PACK_000020" in jt)

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

print("VXS_AGENT_DECISION_CAPABILITY_PACK_000022=PASS")
raise SystemExit(0)
