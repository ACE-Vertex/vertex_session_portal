from pathlib import Path
import json

WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")
PUBLISHED = WORKSTATION / "SESSION_PORTAL_BUILDS" / "000050H1"
EXE = PUBLISHED / "Vertex Session Portal.exe"
APP_RENDERER = PUBLISHED / "resources" / "app" / "out" / "renderer"
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
        if path.is_file() and path.suffix.lower() in {".js", ".mjs", ".cjs", ".html"}:
            if needle in path.read_text(encoding="utf-8", errors="ignore"):
                return True
    return False

def main():
    print("=== TASK DISPATCH RUNTIME VERIFY 000050H1 ===")
    failures = []

    check("PUBLISHED_DIR", PUBLISHED.exists(), failures)
    check("PUBLISHED_EXE", EXE.exists(), failures)
    check("TASK_ENVELOPE_IN_RUNTIME", scan(APP_RENDERER, "VERTEX_TASK_DISPATCH/1"), failures)
    check("TASK_RECEIPTS_IN_RUNTIME", scan(APP_RENDERER, "vertex.portal.task-dispatch.receipts.v1"), failures)
    check("TASK_BUTTON_IN_RUNTIME", scan(APP_RENDERER, "data-vertex-task-dispatch"), failures)
    check("LATEST_LAUNCHER", LAUNCHER.exists(), failures)
    check("LATEST_POINTER", POINTER.exists(), failures)

    if LAUNCHER.exists():
        launcher = LAUNCHER.read_text(encoding="utf-8", errors="replace")
        check("LAUNCHER_POINTS_000050H1", "SESSION_PORTAL_BUILDS\\000050H1" in launcher, failures)

    if POINTER.exists():
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        check("POINTER_BUILD_000050H1", pointer.get("build") == "000050H1", failures)
        check("POINTER_TASK_DISPATCH", pointer.get("task_dispatch") is True, failures)

    if failures:
        print("FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    print("CANONICAL_HUMAN_LAUNCHER=" + str(LAUNCHER))
    print("RUNTIME_EXE=" + str(EXE))
    print("NEXT=RESTART_SESSION_PORTAL_USING_LAUNCHER_AND_RUNTIME_TEST_TASK")
    print("VERTEX_SESSION_PORTAL_TASK_DISPATCH_RUNTIME_VERIFY_000050H1=PASS")

if __name__ == "__main__":
    main()
