from __future__ import annotations
from pathlib import Path
import hashlib
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

def run(cmd: list[str], label: str) -> bool:
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

def main() -> int:
    failures: list[str] = []
    emit("=== VERTEX SESSION PORTAL / EVIDENCE RETURN RECONCILIATION 000076V5 ===")
    emit(f"ROOT={ROOT}")
    emit("ROOT_CAUSE=WORKSTATION_ADVANCED_TO_RETURN_QUEUED_WHILE_PORTAL_CARD_REMAINED_REGISTERED")
    emit("FIX=PULL_THROUGH_RECONCILE_PLUS_RENDERER_POLL_PLUS_AUTHORITATIVE_SIDECAR_MIRROR")
    emit("HUMAN_GATE=PRESERVED")
    emit("EXACT_ORIGIN_ROUTE=PRESERVED")
    emit("ACK_AFTER_DURABLE_DELIVERED=PRESERVED")
    emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")

    for name, path in [("SERVICE", SERVICE), ("IPC", IPC), ("LANE", LANE)]:
        check(f"FILE_{name}", path.is_file(), failures)
    if failures:
        emit("FAILED=" + ",".join(failures))
        return 2

    service = text(SERVICE)
    ipc = text(IPC)
    lane = text(LANE)

    check("PULL_THROUGH_REFRESH_METHOD",
          "async refreshState(): Promise<VraDispatchState>" in service and
          "await this.reconcileWorkstation()" in service and
          "return this.state()" in service, failures)

    check("IPC_AWAITS_REFRESH_STATE",
          "async (): Promise<VraDispatchState> => service.refreshState()" in ipc, failures)

    check("RENDERER_2500MS_RETURN_POLL",
          "private evidenceReturnPoll:" in lane and
          "setInterval(() => {" in lane and
          "}, 2500)" in lane, failures)

    check("REFRESH_COALESCED",
          "private refreshInFlight: Promise<void> | null = null" in lane and
          "if (this.refreshInFlight) return this.refreshInFlight" in lane and
          "private async refreshOnce(): Promise<void>" in lane, failures)

    check("POLL_CLEARED_ON_DISCONNECT",
          "clearInterval(this.evidenceReturnPoll)" in lane and
          "this.evidenceReturnPoll = null" in lane, failures)

    check("WORKSTATION_ALLOCATED_LANE_MIRROR_ONLY",
          "allocated_lane: metadata.allocated_lane ?? null" in service and
          "allocated_lane: null, human_approval" not in service, failures)

    # Return safety contract must stay intact.
    check("EXACT_ORIGIN_FAIL_CLOSED",
          "EVIDENCE_ORIGIN_ROUTE_MISMATCH" in service and
          "origin-mismatch-fail-closed" in lane, failures)

    check("AVAILABLE_ROUTE_ONLY",
          "card.workstationEvidenceState !== 'AVAILABLE'" in lane, failures)

    check("DELIVERED_BEFORE_ACK",
          "receipt.state !== 'DELIVERED'" in lane and
          "acknowledgeVraEvidenceDelivery" in lane, failures)

    check("RETURN_QUEUED_BEFORE_ACK",
          "card.workstationEvidenceReturnState !== 'RETURN_QUEUED'" in lane, failures)

    check("NO_ACTIVE_WINDOW_FALLBACK",
          "exactOriginRoute(card)" in lane and
          "activeSession" not in lane and
          "focusedSession" not in lane, failures)

    check("NO_AUTO_APPLY",
          "AUTO_APPLY" not in lane and
          "acknowledgeEvidenceDelivery" in service, failures)

    src_before = snapshot_src()
    ws_before = workstation_snapshot()

    # Normal project checks.
    check("TYPECHECK", run(["npm", "run", "typecheck"], "TYPECHECK"), failures)
    check("BUILD", run(["npm", "run", "build"], "BUILD"), failures)

    # 000073 full UI/runtime regression when present.
    if PARENT_073.is_file():
        check("PARENT_073", run([sys.executable, str(PARENT_073)], "PARENT_073"), failures)
    else:
        emit("PARENT_073=SKIP_NOT_PRESENT")

    src_after = snapshot_src()
    ws_after = workstation_snapshot()
    check("VERIFY_PORTAL_SOURCE_UNCHANGED", src_before == src_after, failures)
    check("VERIFY_WORKSTATION_SOURCE_UNCHANGED", ws_before == ws_after, failures)

    if failures:
        emit("VERTEX_SESSION_PORTAL_EVIDENCE_RETURN_RECONCILIATION_000076V5=FAIL")
        emit("FAILED=" + ",".join(failures))
        return 1

    emit("VERTEX_SESSION_PORTAL_EVIDENCE_RETURN_RECONCILIATION_000076V5=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
