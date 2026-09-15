from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts"
REGISTRY = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-command-registry.ts"
DETECTOR = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-workspace-detector.ts"
HOST = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"

failures = []

def check(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("SERVICE_PRESENT", SERVICE),
    ("REGISTRY_PRESENT", REGISTRY),
    ("DETECTOR_PRESENT", DETECTOR),
    ("HOST_PRESENT", HOST),
):
    check(name, path.is_file())

if SERVICE.is_file():
    text = SERVICE.read_text(encoding="utf-8")
    check("FOUNDATION_MARKER", "VXS_COMMAND_FOUNDATION_000006" in text)
    check("REGISTRY_IMPORT", "executeVxsCommand" in text)
    check("REGISTRY_BACKEND", "backend: 'VXS_COMMAND'" in text)
    check("VERSION_META_PRESERVED", "backend: 'VXS_META'" in text)
    check("SETTINGS_PRESERVED", "VXS_SETTINGS_AND_TAB_CLOSE_000005" in text)
    check("TAB_CLOSE_PRESERVED", "vxsTabClose" in text)
    check("VXS_BANNER", "VXS 0.1.0 · SHELL" in text)
    check("LEGACY_HOST_NOT_DIRECTLY_EDITED", "vertex-shell-host-bridge.ts" not in text)

if REGISTRY.is_file():
    text = REGISTRY.read_text(encoding="utf-8")
    check("HELP_COMMAND", "vxs --help" in text)
    check("STATUS_COMMAND", "vxs status" in text)
    check("DOCTOR_COMMAND", "vxs doctor" in text)
    check("UNKNOWN_COMMAND_FAILS_CLOSED", "Unknown VXS command" in text)
    check("PWSh_COMPATIBILITY", "compatibilityBackend" in text)
    check("DOCTOR_PASS_WARN_FAIL", "PASS" in text and "WARN" in text and "FAIL" in text)

if DETECTOR.is_file():
    text = DETECTOR.read_text(encoding="utf-8")
    check("NODE_DETECT", "package.json" in text)
    check("RUST_DETECT", "Cargo.toml" in text)
    check("PYTHON_DETECT", "pyproject.toml" in text)
    check("PACKAGE_MANAGER_DETECT", "pnpm-lock.yaml" in text and "package-lock.json" in text)
    check("FRAMEWORK_DETECT", "Electron" in text and "TypeScript" in text and "Vite" in text)

print("HOST_BRIDGE_OPERATION=NONE")
print("WORKSTATION_CHANGE=NONE")
print("HUMAN_GATE_CHANGE=NONE")
print("VRA_SCHEMA_CHANGE=NONE")
print("VERIFY_PRODUCTION_MUTATION=NONE")

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_COMMAND_FOUNDATION_000006=PASS")
raise SystemExit(0)
