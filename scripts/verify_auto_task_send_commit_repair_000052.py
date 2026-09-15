from pathlib import Path
import json

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")
BRIDGE = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
PUBLISHED = WORKSTATION / "SESSION_PORTAL_BUILDS" / "000052"
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
    print("=== VERTEX AUTO TASK SEND COMMIT REPAIR VERIFY 000052 ===")
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
    check("ASYNC_SEND_INJECTION", "return `(async () => {" in text, failures)
    check("SEND_CONTROL_RETRY", "for(let attempt=0; attempt<40; attempt+=1)" in text, failures)
    check("SEND_CONTROL_TIMEOUT", "TARGET_SEND_CONTROL_TIMEOUT" in text, failures)
    check("SEND_COMMIT_CLICKED", "SEND_COMMIT_CLICKED" in text, failures)
    check("FORM_SCOPED_SUBMIT_FALLBACK", "form button[type=\"submit\"]" in text, failures)
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
    check("RUNTIME_SEND_WAIT", scan(RENDERER, "TARGET_SEND_CONTROL_TIMEOUT"), failures)
    check("RUNTIME_SEND_COMMIT", scan(RENDERER, "SEND_COMMIT_CLICKED"), failures)
    check("LATEST_LAUNCHER", LAUNCHER.exists(), failures)
    check("LATEST_POINTER", POINTER.exists(), failures)

    if LAUNCHER.exists():
        launcher = LAUNCHER.read_text(encoding="utf-8", errors="replace")
        check("LAUNCHER_POINTS_000051", "SESSION_PORTAL_BUILDS\\000052" in launcher, failures)

    if POINTER.exists():
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        check("POINTER_BUILD", pointer.get("build") == "000052", failures)
        check("POINTER_AUTO_TASK", pointer.get("auto_task_dispatch") is True, failures)
        check("POINTER_VERTEX_UI", pointer.get("vertex_task_ui") is True, failures)
        check("POINTER_AUTO_DEFAULT_OFF", pointer.get("auto_default") == "OFF", failures)

    if failures:
        print("FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    print("RUNTIME_TEST_FLOW=ARM_AUTO_ON_VERA2_THEN_ISSUE_delivery_AUTO_ENVELOPE")
    print("NATIVE_DIALOGS=RETIRED")
    print("VERTEX_SESSION_PORTAL_VERA_AUTO_TASK_DISPATCH_VERTEX_UI_000052=PASS")

if __name__ == "__main__":
    main()
