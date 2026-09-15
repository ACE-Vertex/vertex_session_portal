from pathlib import Path
import hashlib
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CTRL = ROOT / "src/main/workstation/workstation-process-controller.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
CONTRACTS = ROOT / "src/shared/contracts.ts"
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
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-10000:].replace("\n", " | "))
    return cp.returncode == 0

def main():
    failures = []
    emit("=== ROOT WORKSTATION EXE MIGRATION H1 000083V5H1 ===")
    emit("ROOT_CAUSE=COMPATIBLE_ONLINE_LISTENER_RETURNED_BEFORE_RELEASE_BUILD")
    emit("SECONDARY=ONLINE_UI_HID_START_BUTTON")
    emit("FIX=EXPLICIT_ONLINE_MIGRATE_ROOT_EXE_PATH")
    emit("BLACK_CONSOLE_RETIREMENT=PRESERVED")
    emit("HUMAN_ACTION=REQUIRED")
    emit("BLIND_KILL=ZERO")

    for name, p in [("CTRL", CTRL), ("LANE", LANE), ("CONTRACTS", CONTRACTS)]:
        check(f"{name}_PRESENT", p.is_file(), failures)
    if failures:
        return 2

    ctrl = CTRL.read_text(encoding="utf-8-sig")
    lane = LANE.read_text(encoding="utf-8-sig")
    contracts = CONTRACTS.read_text(encoding="utf-8-sig")

    checks = {
        "EARLY_RETURN_BUG_RETIRED":
            "const rootRelease = await this.ensureRootReleaseBinary(false)" in ctrl and
            ctrl.find("const rootRelease = await this.ensureRootReleaseBinary(false)") <
            ctrl.find("if (await this.listenerUsesExecutable(rootRelease))"),
        "ONLINE_EXTERNAL_VALIDATED_REPLACE":
            "await this.replaceValidatedLegacyListener()" in ctrl and
            "WORKSTATION_ROOT_MIGRATION_BLOCKED" in ctrl,
        "ROOT_LISTENER_IDENTITY_CHECK":
            "listenerUsesExecutable" in ctrl and
            "resolve(identity.executablePath).toLowerCase()" in ctrl,
        "ROOT_RELEASE_STATE_EXPOSED":
            "rootReleaseReady:" in ctrl and
            "rootReleasePath," in ctrl,
        "CONTRACT_ROOT_RELEASE_READY":
            "rootReleaseReady: boolean" in contracts and
            "rootReleasePath: string | null" in contracts,
        "ONLINE_MIGRATION_GUARD":
            "workstationRootMigrationNeeded" in lane and
            "this.workstationOnline() && !this.workstationRootMigrationNeeded()" in lane,
        "MIGRATE_BUTTON_VISIBLE":
            "MIGRATE ROOT EXE" in lane and
            "button.hidden = online && !migrationNeeded" in lane,
        "MIGRATION_HUMAN_EXPLICIT":
            "data-action=\"start-workstation\"" in lane,
        "HIDDEN_BUILD_PRESERVED":
            ctrl.count("windowsHide: true") >= 2 and
            "stdio: 'ignore'" in ctrl,
        "ROOT_EXE_PATH_PRESERVED":
            "ROOT_RELEASE_EXE = 'vertex-workstation.exe'" in ctrl,
        "VALIDATED_PROCESS_GATE_PRESERVED":
            "legacyProcessAllowed" in ctrl and
            "WORKSTATION_LISTENER_IDENTITY_REJECTED" in ctrl,
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
        emit("VERTEX_SESSION_PORTAL_ROOT_WORKSTATION_EXE_MIGRATION_000083V5H1=FAIL")
        emit("FAILED=" + ",".join(failures))
        return 1

    emit("VERTEX_SESSION_PORTAL_ROOT_WORKSTATION_EXE_MIGRATION_000083V5H1=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
