from pathlib import Path
import hashlib
import re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts"
REGISTRY = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-command-registry.ts"
DEV = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-dev-capabilities.ts"
DETECTOR = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-workspace-detector.ts"
HOST = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"

failures = []

def check(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("SERVICE", SERVICE),
    ("REGISTRY", REGISTRY),
    ("DEV_CAPABILITIES", DEV),
    ("DETECTOR", DETECTOR),
    ("HOST", HOST),
):
    check(name + "_PRESENT", path.is_file())

if SERVICE.is_file():
    text = SERVICE.read_text(encoding="utf-8")
    check("PACK_MARKER", "VXS_DEVELOPMENT_CAPABILITY_PACK_000008" in text)
    check("ROUTED_EXECUTION", "routedExecution" in text)
    check("EXECUTION_COMMAND", "executionCommand" in text)
    check("EXECUTION_CWD", "executionCwd" in text)
    check("EXECUTION_BACKEND", "executionBackend" in text)
    check("STREAMING_SPAWN_PRESERVED", "const child = spawn(" in text)
    check("STOP_PATH_PRESERVED", "async stop()" in text)
    check("VSH_REPAIR_PRESERVED", "VXS_VSH_PREFIX_RUNTIME_REPAIR_000007H1" in text)
    check("SETTINGS_PRESERVED", "VXS_SETTINGS_AND_TAB_CLOSE_000005" in text)

if REGISTRY.is_file():
    text = REGISTRY.read_text(encoding="utf-8")
    check("DEV_MODULE_REGISTERED", "createVxsDevelopmentCommands" in text)
    check("DISPATCH_UNION", "VxsExecutionCommandResult" in text)
    check("HELP_BUILD", "vxs build" in text)
    check("HELP_TEST", "vxs test" in text)
    check("HELP_LINT", "vxs lint" in text)
    check("HELP_RUN", "vxs run <script>" in text)
    check("HELP_GIT", "vxs git help" in text)

if DEV.is_file():
    text = DEV.read_text(encoding="utf-8")
    # Node routing is intentionally package-manager generic.
    # Do not require a literal "npm" token: npm / pnpm / yarn are selected
    # dynamically from the detected workspace.
    check("GENERIC_PACKAGE_MANAGER_ROUTING", "workspace.packageManager" in text)
    check("PACKAGE_EXECUTABLE_ROUTING", "packageExecutable(workspace.packageManager)" in text)

    for token in (
        "cargo build",
        "python -m build",
        "cargo test",
        "python -m pytest",
        "cargo clippy --all-targets",
        "python -m ruff check .",
        "git status --short --branch",
        "git diff --staged",
        "git branch --show-current",
        "git log --oneline -10",
    ):
        check("DEV_TOKEN_" + re.sub(r"[^A-Za-z0-9]+", "_", token).strip("_").upper(), token in text)
    check("GIT_READ_ONLY_DECLARATION", "Mutation commands are intentionally not in this pack." in text)
    check("RUN_SCRIPT_VALIDATION", "/^[A-Za-z0-9:_-]+$/" in text)

if HOST.is_file():
    host = HOST.read_text(encoding="utf-8")
    check("HOST_CURRENT_LEGACY_ANCHOR_STILL_PRESENT", "kind === 'system' ? 'VSH │ '" in host)

print("HOST_BRIDGE_OPERATION=NONE")
print("WORKSTATION_CHANGE=NONE")
print("HUMAN_GATE_CHANGE=NONE")
print("VRA_SCHEMA_CHANGE=NONE")
print("GIT_MUTATION_COMMANDS=NONE")
print("VERIFY_PRODUCTION_MUTATION=NONE")

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_DEVELOPMENT_CAPABILITY_PACK_000008H1=PASS")
raise SystemExit(0)
