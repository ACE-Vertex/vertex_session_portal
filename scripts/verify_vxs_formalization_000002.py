from pathlib import Path
import hashlib

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts"
UI = ROOT / "src" / "renderer" / "src" / "components" / "VertexShellUnit" / "VertexShellUnit.ts"
HOST = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"

failures = []

def check(name, value):
    print(name + "=" + ("PASS" if value else "FAIL"))
    if not value:
        failures.append(name)

check("SERVICE_PRESENT", SERVICE.is_file())
check("UI_PRESENT", UI.is_file())
check("HOST_BRIDGE_PRESENT", HOST.is_file())

if SERVICE.is_file():
    s = SERVICE.read_text(encoding="utf-8")
    check("VXS_VERSION_CONST", "const VXS_VERSION = '0.1.0' as const" in s)
    check("VXS_CANONICAL_NAME", "Vertex eXecution Shell" in s)
    check("VXS_VERSION_META_REGEX", r"/^(?:vxs\s+)?--version$/i" in s)
    check("VXS_META_BACKEND", "backend: 'VXS_META'" in s)
    check("VXS_HOST_TEXT", "Host: Vertex Session Portal" in s)
    check("LEGACY_GENERATION_PRESERVED", "const GENERATION = '000080V4A' as const" in s)
    check("LEGACY_BUSY_CONTRACT_PRESERVED", "VERTEX_SHELL_BUSY" in s)
    check("COMPOUND_COMMAND_FIX_PRESERVED", "hasCommandSeparator" in s)

if UI.is_file():
    u = UI.read_text(encoding="utf-8")
    check("UI_VXS_BRAND", "<strong>VXS</strong>" in u)
    check("UI_EXPANDED_NAME", "VERTEX eXecution Shell" in u)
    check("UI_PROMPT_VXS", '<span class="prompt">VXS ›</span>' in u)
    check("UI_SYSTEM_PREFIX_VXS", "? 'VXS │ '" in u)
    check("UI_VERSION_HINT", "Type --version or vxs --version for identity." in u)
    check("UI_OLD_BRAND_REMOVED", "<strong>VERTEX SHELL</strong>" not in u)
    check("UI_OLD_PROMPT_REMOVED", '<span class="prompt">VSH ›</span>' not in u)
    check("VERTEX_SHELL_BRIDGE_COMPAT", "api?.vertexShell" in u)
    check("VERTEX_SHELL_CUSTOM_ELEMENT_COMPAT", "vertex-shell-unit" in u)

# This VRA intentionally does not operate on the host bridge.
print("HOST_BRIDGE_OPERATION=NONE")
print("VRA_SCHEMA_CHANGE=NONE")
print("WORKSTATION_CHANGE=NONE")
print("HUMAN_GATE_CHANGE=NONE")

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_FORMALIZATION_000002=PASS")
raise SystemExit(0)
