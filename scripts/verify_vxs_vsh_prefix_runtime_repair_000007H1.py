from pathlib import Path
import hashlib

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
    check("REPAIR_MARKER", "VXS_VSH_PREFIX_RUNTIME_REPAIR_000007H1" in text)
    check("NORMALIZER_PRESENT", "normalizeVxsBrandText" in text)
    check("SYNC_TEXT_PATCH", "installSynchronousOutputBranding" in text)
    check("TEXT_CONTENT_GUARD", "__VXS_TEXT_CONTENT_PATCHED__" in text)
    check("VSH_TO_VXS", ".replaceAll('VSH │ ', 'VXS │ ')" in text)
    check("PROMPT_TO_VXS", ".replaceAll('VSH ›', 'VXS ›')" in text)
    check("BANNER_TO_VXS", "'VXS 0.1.0 · SHELL'" in text)
    check("COMMAND_FOUNDATION_PRESERVED", "VXS_COMMAND_FOUNDATION_000006" in text)
    check("SETTINGS_PRESERVED", "VXS_SETTINGS_AND_TAB_CLOSE_000005" in text)
    check("VXS_COMMAND_BACKEND_PRESERVED", "backend: 'VXS_COMMAND'" in text)

if HOST.is_file():
    host = HOST.read_text(encoding="utf-8")
    # Fail closed unless the current production Host still has the exact
    # legacy system-prefix semantics we are compensating for.
    check(
        "CURRENT_HOST_LEGACY_SYSTEM_PREFIX_ANCHOR",
        "kind === 'system' ? 'VSH │ '" in host
    )
    check(
        "CURRENT_HOST_APPEND_ANCHOR",
        "const prefix =" in host and "const rendered = prefix + clean" in host
    )

print("HOST_BRIDGE_OPERATION=NONE")
print("HOST_BRIDGE_REPLACEMENT=NO")
print("WORKSTATION_CHANGE=NONE")
print("HUMAN_GATE_CHANGE=NONE")
print("VRA_SCHEMA_CHANGE=NONE")
print("VERIFY_PRODUCTION_MUTATION=NONE")

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_VSH_PREFIX_RUNTIME_REPAIR_000007H1=PASS")
raise SystemExit(0)
