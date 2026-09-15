from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
DISCOVERY = PORTAL / "src/main/shell/vxs/vxs-capability-discovery.ts"
FOUNDATION = PORTAL / "src/main/shell/vxs/vxs-autonomy-foundation-capabilities.ts"
HANDOFF = PORTAL / "src/main/shell/vxs/vxs-agent-handoff-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("DISCOVERY", DISCOVERY),
    ("FOUNDATION", FOUNDATION),
    ("HANDOFF", HANDOFF),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
dt = DISCOVERY.read_text(encoding="utf-8") if DISCOVERY.is_file() else ""
ft = FOUNDATION.read_text(encoding="utf-8") if FOUNDATION.is_file() else ""
ht = HANDOFF.read_text(encoding="utf-8") if HANDOFF.is_file() else ""

ck("REGISTRY_MARKER", "VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025" in rt)
ck("DISCOVERY_MARKER", "VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025" in dt)
ck("FOUNDATION_MARKER", "VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025" in ft)
ck("MODULE_IMPORT", "createVxsAutonomyFoundationCommands" in rt)
ck("REGISTRY_PROVIDER", "createVxsAutonomyFoundationCommands(() => COMMANDS)" in rt)

ck("DISCOVERY_EXPORT_TYPE", "export type SafetyClass" in dt)
ck("DISCOVERY_EXPORT_DESCRIPTOR", "export interface CapabilityDescriptor" in dt)
ck("DISCOVERY_EXPORT_BUILDER", "export function buildVxsCapabilityCatalog" in dt)
ck("DISCOVERY_EXPORT_DESCRIBE", "export function describeVxsCapability" in dt)

for token in (
    "vxs selftest",
    "vxs selftest --json",
    "vxs policy",
    "vxs policy --json",
):
    ck("HELP_" + token.replace(" ", "_").replace("-", "_").upper(), token in rt)

for token in (
    "vxs-selftest/1",
    "vxs-autonomy-policy/1",
    "UNIQUE_COMMAND_NAMES",
    "UNIQUE_ALIASES",
    "ALIASES_DO_NOT_SHADOW_COMMANDS",
    "HUMAN_GATE_CONTRACT",
    "VRA_IS_HUMAN_GATED",
    "ARBITRARY_RUN_NOT_AUTOMATIC",
    "AUTONOMOUS_PREPARATION",
    "human_gate_bypass: false",
    "workstation_lane_allocation_authority: 'WORKSTATION'",
    "production_mutation_during_verify: false",
    "arbitrary_run_auto_execution: false",
):
    ck("FOUNDATION_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace("/", "_").replace("-", "_").upper(), token in ft)

ck("ALLOW_VERIFY", "'verify'" in ft)
ck("DENY_RUN", "'run'" in ft)
ck("DENY_VRA", "'vra'" in ft)
ck("NO_SPAWN", "spawnSync" not in ft)
ck("NO_WRITE_FILE", "writeFile" not in ft)
ck("NO_HTTP_POST", "POST" not in ft)
ck("NO_REEXECUTION", "reexecute" not in ft.lower())
ck("000024_PRESERVED", "VXS_CAPABILITY_DISCOVERY_PACK_000024" in dt)
ck("000023_PRESERVED", "VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023" in ht)

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

print("VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025=PASS")
raise SystemExit(0)
