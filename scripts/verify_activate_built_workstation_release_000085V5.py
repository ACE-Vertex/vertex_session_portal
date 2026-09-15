from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "src/main/workstation/workstation-process-controller.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
WORKSTATION = ROOT.parent / "vertex_workstation"
EXPECTED = WORKSTATION / "release" / "vertex-workstation.exe"

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
        timeout=1800,
    )
    emit(f"{label}_EXIT={cp.returncode}")
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-8000:].replace("\n", " | "))
    return cp.returncode == 0

def main():
    failures = []
    emit("=== ACTIVATE BUILT WORKSTATION RELEASE 000085V5 ===")
    emit(f"EXPECTED_RELEASE_EXE={EXPECTED}")
    emit("BUILD_ALREADY_COMPLETED_BY=000084V5")
    emit("PORTAL_MANAGED_CONSOLE=HIDDEN")
    emit("WORKSTATION_SOURCE_MUTATION=ZERO")
    emit("HUMAN_ACTIVATION_REQUIRED=YES")

    check("CTRL_PRESENT", CTRL.is_file(), failures)
    check("LANE_PRESENT", LANE.is_file(), failures)
    check("BUILT_RELEASE_EXE_PRESENT", EXPECTED.is_file(), failures)

    if CTRL.is_file():
        ctrl = CTRL.read_text(encoding="utf-8-sig")
        check(
            "RELEASE_PATH_WIRED",
            "ROOT_RELEASE_EXE = join('release', 'vertex-workstation.exe')" in ctrl,
            failures,
        )
        check("DIRECT_EXE_PRIORITY", "const rootRelease = join(root, ROOT_RELEASE_EXE)" in ctrl, failures)
        check("WINDOWS_HIDDEN", ctrl.count("windowsHide: true") >= 2, failures)
        check("SHELL_FALSE", "shell: false" in ctrl, failures)
        check("LEGACY_VALIDATION_PRESERVED", "legacyProcessAllowed" in ctrl, failures)
        check("NO_BLIND_KILL", "WORKSTATION_LISTENER_IDENTITY_REJECTED" in ctrl, failures)

    if LANE.is_file():
        lane = LANE.read_text(encoding="utf-8-sig")
        check("ACTIVATE_BUTTON", "ACTIVATE RELEASE EXE" in lane, failures)
        check("ONLINE_MIGRATION_PATH", "workstationRootMigrationNeeded" in lane, failures)

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
        emit("VERTEX_SESSION_PORTAL_ACTIVATE_BUILT_WORKSTATION_RELEASE_000085V5=FAIL")
        emit("FAILED=" + ",".join(failures))
        return 1

    emit("VERTEX_SESSION_PORTAL_ACTIVATE_BUILT_WORKSTATION_RELEASE_000085V5=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
