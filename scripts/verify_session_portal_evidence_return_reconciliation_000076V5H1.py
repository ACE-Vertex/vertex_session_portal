from __future__ import annotations
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
WORKSTATION = ROOT.parent / "vertex_workstation"
PARENT_073 = ROOT / "scripts/verify_session_portal_final_ux_wordmark_autofit_000073V5.py"

def emit(v: str) -> None:
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot_src() -> dict[str, str]:
    base = ROOT / "src"
    return {
        p.relative_to(ROOT).as_posix(): sha(p)
        for p in sorted(base.rglob("*"))
        if p.is_file()
    }

def workstation_snapshot() -> dict[str, str]:
    roots = [
        WORKSTATION / "headless/src",
        WORKSTATION / "src-tauri/src",
    ]
    out: dict[str, str] = {}
    for base in roots:
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_file():
                out[p.relative_to(WORKSTATION).as_posix()] = sha(p)
    return out

def check(name: str, ok: bool, failures: list[str]) -> None:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def run_process(cmd: list[str], label: str) -> bool:
    emit("RUN_" + label + "=" + " ".join(cmd))
    p = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    emit(p.stdout)
    emit(f"{label}_EXIT={p.returncode}")
    return p.returncode == 0

def resolve_npm() -> str | None:
    # On Windows the executable is normally npm.cmd, not npm.exe.
    # Python CreateProcess cannot rely on PATHEXT resolution for a bare "npm".
    candidates = [
        shutil.which("npm.cmd"),
        shutil.which("npm.exe"),
        shutil.which("npm"),
    ]
    for c in candidates:
        if c:
            return c
    return None

def run_npm(script_name: str, label: str, npm: str) -> bool:
    # .cmd must be launched through cmd.exe for deterministic Windows behavior.
    if npm.lower().endswith((".cmd", ".bat")):
        comspec = os.environ.get("COMSPEC") or shutil.which("cmd.exe") or "cmd.exe"
        cmdline = f'"{npm}" run {script_name}'
        return run_process([comspec, "/d", "/s", "/c", cmdline], label)
    return run_process([npm, "run", script_name], label)

def main() -> int:
    failures: list[str] = []
    emit("=== VERTEX SESSION PORTAL / EVIDENCE RETURN RECONCILIATION 000076V5H1 ===")
    emit(f"ROOT={ROOT}")
    emit("H1_CAUSE=PYTHON_CREATEPROCESS_COULD_NOT_RESOLVE_BARE_NPM_ON_WINDOWS")
    emit("H1_FIX=RESOLVE_NPM_CMD_AND_LAUNCH_VIA_COMSPEC")
    emit("PRODUCTION_PORTAL_CODE_CHANGE=ZERO")
    emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")

    for name, path in [("SERVICE", SERVICE), ("IPC", IPC), ("LANE", LANE)]:
        check(f"FILE_{name}", path.is_file(), failures)
    if failures:
        emit("FAILED=" + ",".join(failures))
        return 2

    service = text(SERVICE)
    ipc = text(IPC)
    lane = text(LANE)

    # Re-assert 000076 production semantics already applied by parent VRA.
    check("PULL_THROUGH_REFRESH_METHOD",
          "async refreshState(): Promise<VraDispatchState>" in service and
          "await this.reconcileWorkstation()" in service and
          "return this.state()" in service, failures)

    check("IPC_AWAITS_REFRESH_STATE",
          "async (): Promise<VraDispatchState> => service.refreshState()" in ipc, failures)

    check("RENDERER_RETURN_POLL",
          "private evidenceReturnPoll:" in lane and
          "}, 2500)" in lane, failures)

    check("REFRESH_COALESCED",
          "private refreshInFlight: Promise<void> | null = null" in lane and
          "if (this.refreshInFlight) return this.refreshInFlight" in lane, failures)

    check("EXACT_ORIGIN_FAIL_CLOSED",
          "EVIDENCE_ORIGIN_ROUTE_MISMATCH" in service and
          "origin-mismatch-fail-closed" in lane, failures)

    check("DELIVERED_BEFORE_ACK",
          "receipt.state !== 'DELIVERED'" in lane and
          "acknowledgeVraEvidenceDelivery" in lane, failures)

    check("RETURN_QUEUED_BEFORE_ACK",
          "card.workstationEvidenceReturnState !== 'RETURN_QUEUED'" in lane, failures)

    check("WORKSTATION_ALLOCATED_LANE_MIRROR_ONLY",
          "allocated_lane: metadata.allocated_lane ?? null" in service, failures)

    portal_before = snapshot_src()
    ws_before = workstation_snapshot()

    npm = resolve_npm()
    check("NPM_RESOLVED", npm is not None, failures)
    if npm:
        emit(f"NPM={npm}")
        check("TYPECHECK", run_npm("typecheck", "TYPECHECK", npm), failures)
        check("BUILD", run_npm("build", "BUILD", npm), failures)

    if PARENT_073.is_file():
        check("PARENT_073", run_process([sys.executable, str(PARENT_073)], "PARENT_073"), failures)
    else:
        emit("PARENT_073=SKIP_NOT_PRESENT")

    portal_after = snapshot_src()
    ws_after = workstation_snapshot()

    check("VERIFY_PORTAL_SOURCE_UNCHANGED", portal_before == portal_after, failures)
    check("VERIFY_WORKSTATION_SOURCE_UNCHANGED", ws_before == ws_after, failures)

    if failures:
        emit("VERTEX_SESSION_PORTAL_EVIDENCE_RETURN_RECONCILIATION_000076V5H1=FAIL")
        emit("FAILED=" + ",".join(failures))
        return 1

    emit("VERTEX_SESSION_PORTAL_EVIDENCE_RETURN_RECONCILIATION_000076V5H1=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
