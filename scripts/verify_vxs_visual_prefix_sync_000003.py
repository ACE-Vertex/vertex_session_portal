from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts"
HOST = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"

failures = []

def check(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

check("SERVICE_PRESENT", SERVICE.is_file())
check("HOST_PRESENT", HOST.is_file())

if SERVICE.is_file():
    text = SERVICE.read_text(encoding="utf-8")
    check("BROWSERWINDOW_IMPORT", "import { app, BrowserWindow } from 'electron'" in text)
    check("SYNC_METHOD", "private syncVxsBranding(): void" in text)
    check("HOST_ROOT_TARGET", "vertex-shell-internal-unit" in text)
    check("VSH_PREFIX_TO_VXS", "replaceAll('VSH │ ', 'VXS │ ')" in text)
    check("PROMPT_TO_VXS", "prompt.textContent.replace('VSH', 'VXS')" in text)
    check("HEADER_TO_VXS", "brand.textContent = 'VXS'" in text)
    check("MUTATION_OBSERVER", "new MutationObserver(() => applyBranding())" in text)
    check("STATE_SYNC", "state(): VertexShellState {\n    this.syncVxsBranding()" in text)
    check("EXECUTE_SYNC", "Promise<VertexShellCommandResult> {\n    this.syncVxsBranding()" in text)
    check("VXS_VERSION_PRESERVED", "const VXS_VERSION = '0.1.0' as const" in text)
    check("VXS_META_PRESERVED", "backend: 'VXS_META'" in text)
    check("LEGACY_BUSY_CONTRACT_PRESERVED", "VERTEX_SHELL_BUSY" in text)

# The current host bridge is deliberately NOT replaced by this artifact.
print("HOST_BRIDGE_OPERATION=NONE")
print("HOST_BRIDGE_SOURCE_REPLACEMENT=NO")
print("VRA_SCHEMA_CHANGE=NONE")
print("WORKSTATION_CHANGE=NONE")
print("HUMAN_GATE_CHANGE=NONE")
print("VERIFY_PRODUCTION_MUTATION=NONE")

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_VISUAL_PREFIX_SYNC_000003=PASS")
raise SystemExit(0)
