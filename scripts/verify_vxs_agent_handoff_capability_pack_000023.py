from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
CONTEXT = PORTAL / "src/main/shell/vxs/vxs-agent-context-capabilities.ts"
DECISION = PORTAL / "src/main/shell/vxs/vxs-agent-decision-capabilities.ts"
HANDOFF = PORTAL / "src/main/shell/vxs/vxs-agent-handoff-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("CONTEXT", CONTEXT),
    ("DECISION", DECISION),
    ("HANDOFF", HANDOFF),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
ct = CONTEXT.read_text(encoding="utf-8") if CONTEXT.is_file() else ""
dt = DECISION.read_text(encoding="utf-8") if DECISION.is_file() else ""
ht = HANDOFF.read_text(encoding="utf-8") if HANDOFF.is_file() else ""

ck("REGISTRY_MARKER", "VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023" in rt)
ck("DECISION_MARKER", "VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023" in dt)
ck("HANDOFF_MARKER", "VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023" in ht)
ck("MODULE_IMPORT", "createVxsAgentHandoffCommands" in rt)

ck("DECISION_READINESS_EXPORT", "export function assessVxsReadiness" in dt)
ck("DECISION_RECOMMEND_EXPORT", "export function recommendVxsNextCommands" in dt)
ck("DECISION_TYPE_EXPORT", "export interface ReadinessAssessment" in dt)
ck("CONTEXT_REUSED", "buildVxsAgentContextSnapshot" in ht)
ck("DECISION_REUSED", "assessVxsReadiness" in ht and "recommendVxsNextCommands" in ht)

for token in (
    "vxs handoff",
    "vxs handoff --json",
):
    ck("HELP_" + token.replace(" ", "_").replace("-", "_").upper(), token in rt)

for token in (
    "vxs-agent-handoff/1",
    "name: 'handoff'",
    "aliases: ['brief']",
    "advisory_only: true",
    "human_gate_required_for_vra_execution: true",
    "workstation_lane_authority_preserved: true",
    "automatic_execution: false",
    "HANDOFF_MUTATION=NONE",
):
    ck("HANDOFF_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("-", "_").replace("/", "_").upper(), token in ht)

ck("NO_SPAWN", "spawnSync" not in ht)
ck("NO_WRITE_FILE", "writeFile" not in ht)
ck("NO_APPEND_FILE", "appendFile" not in ht)
ck("NO_UNLINK", "unlink" not in ht)
ck("NO_RM", "rmSync" not in ht)
ck("NO_HTTP_POST", "POST" not in ht)
ck("NO_REEXECUTION", "reexecute" not in ht.lower())
ck("000022_PRESERVED", "VXS_AGENT_DECISION_CAPABILITY_PACK_000022" in dt)
ck("000021_PRESERVED", "VXS_AGENT_CONTEXT_CAPABILITY_PACK_000021" in ct)

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

print("VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023=PASS")
raise SystemExit(0)
