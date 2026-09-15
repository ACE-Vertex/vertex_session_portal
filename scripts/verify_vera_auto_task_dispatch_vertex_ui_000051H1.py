from pathlib import Path
import json

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")
BRIDGE = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
PUBLISHED = WORKSTATION / "SESSION_PORTAL_BUILDS" / "000051H1"
EXE = PUBLISHED / "Vertex Session Portal.exe"
RENDERER = PUBLISHED / "resources" / "app" / "out" / "renderer"
LAUNCHER = WORKSTATION / "START_SESSION_PORTAL_LATEST.cmd"
POINTER = WORKSTATION / "SESSION_PORTAL_LATEST.pointer.json"

def check(name, ok, failures):
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def scan(root: Path, needle: str) -> bool:
    if not root.exists():
        return False
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".js",".mjs",".cjs",".html"}:
            if needle in path.read_text(encoding="utf-8", errors="ignore"):
                return True
    return False

def main():
    print("=== VERTEX AUTO TASK DISPATCH + VERTEX UI VERIFY 000051H1 ===")
    failures = []
    text = BRIDGE.read_text(encoding="utf-8") if BRIDGE.exists() else ""

    check("SOURCE_BRIDGE", BRIDGE.exists(), failures)
    check("AUTO_DELIVERY_ONLY", "env.delivery !== 'AUTO'" in text, failures)
    check("AUTO_ARM_BUTTON", "dataset.vertexTaskAuto" in text, failures)
    check("AUTO_ARMED_LABEL", "AUTO●" in text, failures)
    check("AUTO_STATUS_MARKER", "VERTEX // AUTO ARMED" in text, failures)
    check("AUTO_OFF_BY_DEFAULT", "const armedSources = new Set<string>()" in text, failures)
    check("AUTO_STABLE_DEBOUNCE", "STABLE_POLLS_REQUIRED = 2" in text, failures)
    check("SOURCE_BUSY_GUARD", "probe.busy" in text, failures)
    check("SOURCE_SESSION_BIND", "TASK_SOURCE_SESSION_MISMATCH" in text, failures)
    check("NO_SELF_DISPATCH", "TASK_SELF_DISPATCH_FORBIDDEN" in text, failures)
    check("MAX_FOUR_TARGETS", "rows.length < 1 || rows.length > 4" in text, failures)
    check("IDEMPOTENCY_RECEIPTS", "vertex.portal.task-dispatch.receipts.v1" in text, failures)
    check("VERTEX_DIALOG_CUSTOM", "function vertexDialog" in text, failures)
    check("VERTEX_TOAST_CUSTOM", "function toast" in text, failures)
    check("VERTEX_BLUE", "#168CFF" in text and "#3AB8FF" in text, failures)
    check("VERTEX_DEEP_BACKGROUND", "#070B10" in text and "#0C121A" in text, failures)
    check("NO_NATIVE_CONFIRM", "window.confirm(" not in text, failures)
    check("NO_NATIVE_ALERT", "window.alert(" not in text, failures)

    check("PUBLISHED_EXE", EXE.exists(), failures)
    check("RUNTIME_AUTO", scan(RENDERER, "vertexTaskAuto"), failures)
    check("RUNTIME_VERTEX_HUD", scan(RENDERER, "vertexTaskHud"), failures)
    check("RUNTIME_RECEIPTS", scan(RENDERER, "vertex.portal.task-dispatch.receipts.v1"), failures)
    check("LATEST_LAUNCHER", LAUNCHER.exists(), failures)
    check("LATEST_POINTER", POINTER.exists(), failures)

    if LAUNCHER.exists():
        launcher = LAUNCHER.read_text(encoding="utf-8", errors="replace")
        check("LAUNCHER_POINTS_000051", "SESSION_PORTAL_BUILDS\\000051H1" in launcher, failures)

    if POINTER.exists():
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        check("POINTER_BUILD", pointer.get("build") == "000051H1", failures)
        check("POINTER_AUTO_TASK", pointer.get("auto_task_dispatch") is True, failures)
        check("POINTER_VERTEX_UI", pointer.get("vertex_task_ui") is True, failures)
        check("POINTER_AUTO_DEFAULT_OFF", pointer.get("auto_default") == "OFF", failures)

    if failures:
        print("FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    print("RUNTIME_TEST_FLOW=ARM_AUTO_ON_VERA2_THEN_ISSUE_delivery_AUTO_ENVELOPE")
    print("NATIVE_DIALOGS=RETIRED")
    print("VERTEX_SESSION_PORTAL_VERA_AUTO_TASK_DISPATCH_VERTEX_UI_000051H1=PASS")

if __name__ == "__main__":
    main()
