from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "src/main/workstation/workstation-process-controller.ts"
FRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
WORKSTATION = ROOT.parent / "vertex_workstation"

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot(base):
    if not base.is_dir():
        return {}
    return {
        p.relative_to(base).as_posix(): sha(p)
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }

def check(name, ok, failures):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def run(cmd, label):
    emit("RUN_" + label + "=" + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=1800
    )
    emit(f"{label}_EXIT={cp.returncode}")
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-9000:].replace("\n", " | "))
    return cp.returncode == 0

def main():
    failures = []
    emit("=== ROOT WORKSTATION EXE + HORIZONTAL SCROLLBAR RETIREMENT 000083V5 ===")
    emit("ROOT_EXE=vertex_workstation/vertex-workstation.exe")
    emit("ROOT_EXE_BUILD_TRIGGER=EXPLICIT_START_OR_REPLACE")
    emit("CONSOLE_WINDOW=HIDDEN_FOR_PORTAL_MANAGED_BUILD_AND_SERVER")
    emit("SCROLL_MECHANICS=PRESERVED")
    emit("HORIZONTAL_SCROLLBAR_CHROME=HIDDEN")
    emit("WORKSTATION_SOURCE_MUTATION=ZERO")
    emit("HUMAN_START_ACTION=REQUIRED")

    check("CTRL_PRESENT", CTRL.is_file(), failures)
    check("FRAME_PRESENT", FRAME.is_file(), failures)
    if failures:
        return 2

    ctrl = CTRL.read_text(encoding="utf-8-sig")
    frame = FRAME.read_text(encoding="utf-8-sig")

    checks = {
        "ROOT_RELEASE_NAME": "ROOT_RELEASE_EXE = 'vertex-workstation.exe'" in ctrl,
        "RELEASE_BUILD_METHOD": "ensureRootReleaseBinary" in ctrl,
        "RELEASE_CARGO_BUILD": "'build'," in ctrl and "'--release'," in ctrl and "'--bin'," in ctrl,
        "ROOT_DIRECT_RUNTIME_PRIORITY": "const rootRelease = join(root, ROOT_RELEASE_EXE)" in ctrl,
        "BUILD_WINDOWS_HIDDEN": "windowsHide: true" in ctrl and "stdio: 'ignore'" in ctrl,
        "SERVER_WINDOWS_HIDDEN": ctrl.count("windowsHide: true") >= 2,
        "CURRENT_SOURCE_FRESHNESS": "workstationSourcesNewerThan" in ctrl,
        "ATOMICISH_PUBLICATION": "publishRootReleaseBinary" in ctrl and ".next" in ctrl and ".previous" in ctrl,
        "OLD_CARGO_RUN_FALLBACK_PRESERVED": "'run'," in ctrl and "'SIBLING_CARGO'" in ctrl,
        "LEGACY_VALIDATION_PRESERVED": "legacyProcessAllowed" in ctrl and "WORKSTATION_LISTENER_IDENTITY_REJECTED" in ctrl,
        "SCROLLBAR_WIDTH_NONE": "scrollbar-width:none" in frame,
        "WEBKIT_SCROLLBAR_HIDDEN": "sessionViewport::-webkit-scrollbar" in frame,
        "HOST_OVERFLOW_GUARD": "overflow-x:hidden" in frame,
        "AUTOFIT_PRESERVED": "fitMainWindowToVisibleLayout" in frame and "track.scrollWidth" in frame,
    }
    for name, ok in checks.items():
        check(name, ok, failures)

    portal_before = snapshot(ROOT / "src")
    ws_before = snapshot(WORKSTATION / "headless/src") | snapshot(WORKSTATION / "src-tauri/src")

    npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
    check("NPM_RESOLVED", npm is not None, failures)
    if npm:
        check("TYPECHECK", run([npm, "run", "typecheck"], "TYPECHECK"), failures)
        check("BUILD", run([npm, "run", "build"], "BUILD"), failures)

    portal_after = snapshot(ROOT / "src")
    ws_after = snapshot(WORKSTATION / "headless/src") | snapshot(WORKSTATION / "src-tauri/src")
    check("VERIFY_PORTAL_SOURCE_UNCHANGED", portal_before == portal_after, failures)
    check("VERIFY_WORKSTATION_SOURCE_UNCHANGED", ws_before == ws_after, failures)

    if failures:
        emit("VERTEX_SESSION_PORTAL_ROOT_WORKSTATION_EXE_SCROLLBAR_RETIREMENT_000083V5=FAIL")
        emit("FAILED=" + ",".join(failures))
        return 1

    emit("VERTEX_SESSION_PORTAL_ROOT_WORKSTATION_EXE_SCROLLBAR_RETIREMENT_000083V5=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
