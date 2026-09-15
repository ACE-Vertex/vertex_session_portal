from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
DISCOVERY = PORTAL / "src/main/shell/vxs/vxs-capability-discovery.ts"
HANDOFF = PORTAL / "src/main/shell/vxs/vxs-agent-handoff-capabilities.ts"
DECISION = PORTAL / "src/main/shell/vxs/vxs-agent-decision-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("DISCOVERY", DISCOVERY),
    ("HANDOFF", HANDOFF),
    ("DECISION", DECISION),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
dt = DISCOVERY.read_text(encoding="utf-8") if DISCOVERY.is_file() else ""
ht = HANDOFF.read_text(encoding="utf-8") if HANDOFF.is_file() else ""
at = DECISION.read_text(encoding="utf-8") if DECISION.is_file() else ""

ck("REGISTRY_MARKER", "VXS_CAPABILITY_DISCOVERY_PACK_000024" in rt)
ck("DISCOVERY_MARKER", "VXS_CAPABILITY_DISCOVERY_PACK_000024" in dt)
ck("MODULE_IMPORT", "createVxsCapabilityDiscoveryCommands" in rt)
ck("REGISTRY_PROVIDER", "createVxsCapabilityDiscoveryCommands(() => COMMANDS)" in rt)

for token in (
    "vxs capabilities",
    "vxs capabilities --json",
    "vxs describe <command>",
):
    ck("HELP_" + token.replace(" ", "_").replace("<", "").replace(">", "").replace("-", "_").upper(), token in rt)

for token in (
    "vxs-capabilities/1",
    "vxs-capability/1",
    "OBSERVE",
    "EXECUTE_LOCAL",
    "HUMAN_GATED",
    "name: 'capabilities'",
    "name: 'describe'",
    "CAPABILITY_DISCOVERY_EXECUTION=NONE",
):
    ck("DISCOVERY_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace("/", "_").replace("-", "_").upper(), token in dt)

ck("VRA_HUMAN_GATED", "HUMAN_GATED.has(command.name)" in dt)
ck("EXECUTE_LOCAL_SET", "'build'" in dt and "'verify'" in dt and "'run'" in dt)
ck("AUTOMATIC_EXECUTION_FALSE", "automaticExecution: false" in dt)
ck("NO_SPAWN", "spawnSync" not in dt)
ck("NO_WRITE_FILE", "writeFile" not in dt)
ck("NO_APPEND_FILE", "appendFile" not in dt)
ck("NO_UNLINK", "unlink" not in dt)
ck("NO_HTTP_POST", "POST" not in dt)
ck("000023_PRESERVED", "VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023" in ht)
ck("000022_PRESERVED", "VXS_AGENT_DECISION_CAPABILITY_PACK_000022" in at)

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

print("VXS_CAPABILITY_DISCOVERY_PACK_000024=PASS")
raise SystemExit(0)
