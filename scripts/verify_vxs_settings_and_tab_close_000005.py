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

    check("FEATURE_MARKER", "VXS_SETTINGS_AND_TAB_CLOSE_000005" in text)
    check("VXS_VERSION_PRESERVED", "const VXS_VERSION = '0.1.0' as const" in text)
    check("VXS_META_PRESERVED", "backend: 'VXS_META'" in text)
    check("WINDOW_TITLE_PRESERVED", "window.setTitle('Vertex eXecution Shell')" in text)

    check("SETTINGS_KEY", "vxs:editor-settings:v1" in text)
    check("SETTINGS_GEAR", "vxsSettingsButton" in text and "⚙" in text)
    check("SETTINGS_POPOVER", "vxsSettingsPopover" in text)
    check("DEFAULT_MODE", "Default Mode" in text)
    check("OLD_MODE", "OLD Mode" in text)
    check("FONT_SIZE", "Font Size" in text and "vxs-font-size" in text)

    check("DEFAULT_WHITE_INFO", "White = Standard / Info" in text)
    check("DEFAULT_GREEN_SUCCESS", "Green = Success / Ready" in text)
    check("DEFAULT_ORANGE_WARNING", "Orange = Warning / Caution" in text)
    check("DEFAULT_RED_ERROR", "Red = Error / Failed" in text)
    check("OLD_GREEN_DEFAULT", "Green = Default text" in text)
    check("OLD_RED_ERROR", "Red = Error only" in text)

    check("OUTPUT_CLASSIFIER", "const classifyLine = line =>" in text)
    check("OLD_MODE_STYLE", '[data-vxs-editor-mode="old"] .vxsLine' in text)
    check("DEFAULT_MODE_STYLE", '[data-vxs-editor-mode="default"] .vxsLine.success' in text)
    check("SETTINGS_PERSISTENCE", "localStorage.setItem(SETTINGS_KEY" in text)

    check("TAB_CLOSE_X", "close.textContent = '×'" in text)
    check("TAB_CLOSE_HANDLER", "const dismissTab = tab =>" in text)
    check("RUNNING_TAB_GUARD", "Running shell cannot be closed" in text)
    check("LAST_TAB_REPLACEMENT", "q('.tabAdd')?.click()" in text)
    check("CLOSED_TAB_SUPPRESSION", "vxsTabClosed" in text and "closedTabs.has" in text)

    check("LEGACY_BUSY_CONTRACT", "VERTEX_SHELL_BUSY" in text)

print("HOST_BRIDGE_OPERATION=NONE")
print("HOST_BRIDGE_SOURCE_REPLACEMENT=NO")
print("WORKSTATION_CHANGE=NONE")
print("HUMAN_GATE_CHANGE=NONE")
print("VRA_SCHEMA_CHANGE=NONE")
print("VERIFY_PRODUCTION_MUTATION=NONE")

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_SETTINGS_AND_TAB_CLOSE_000005=PASS")
raise SystemExit(0)
