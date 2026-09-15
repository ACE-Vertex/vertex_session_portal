from __future__ import annotations
from pathlib import Path
import subprocess, traceback

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def safe(v: object) -> str:
    return str(v).encode("ascii", errors="backslashreplace").decode("ascii")

def emit(v: object) -> None:
    print(safe(v), flush=True)

def check(name: str, ok: bool) -> bool:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def run_npm(*args: str) -> int:
    cmd = [str(NPM), *args]
    emit("RUN=" + " ".join(cmd))
    try:
        p = subprocess.run(
            cmd, cwd=ROOT, text=True, capture_output=True, errors="replace",
            timeout=180, shell=False
        )
    except subprocess.TimeoutExpired:
        emit("NPM_TIMEOUT=180")
        return 124
    except Exception as exc:
        emit(f"NPM_EXCEPTION={type(exc).__name__}:{exc}")
        emit(traceback.format_exc())
        return 125
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-16000:].replace("\r",""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-16000:].replace("\r",""))
    return p.returncode

def main() -> int:
    emit("=== DISPATCH CARD / PRODUCTION LANE SNAPSHOT OSCILLATION REPAIR 000093V5H2 ===")
    emit("ROOT_CAUSE=DUAL_2500MS_RECONCILE_ENTRIES_WITHOUT_SERVICE_WIDE_SINGLE_FLIGHT")
    emit("FIX=COALESCE_MAIN_TIMER_AND_RENDERER_PULL_THROUGH_RECONCILE")
    emit("HUMAN_UI_MUTATION=NONE")
    emit("WORKSTATION_MUTATION=NONE")
    emit("HUMAN_GATE=UNCHANGED")
    emit("EXACT_ORIGIN=UNCHANGED")
    emit("OBSERVABILITY_H2=UNCHANGED")

    if not SERVICE.is_file():
        emit("SERVICE_FILE=FAIL")
        return 20

    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    ok = True

    ok &= check("H2_MARKER", "000093V5H2: both the main 2500 ms timer and the renderer pull-through poll" in s)
    ok &= check("SERVICE_WIDE_SINGLE_FLIGHT_FIELD",
                "private workstationReconcileInFlight: Promise<void> | null = null" in s)
    ok &= check("REFRESH_STATE_STILL_AWAITS_RECONCILE",
                "async refreshState(): Promise<VraDispatchState>" in s
                and "await this.reconcileWorkstation()" in s)
    ok &= check("MAIN_TIMER_STILL_USES_RECONCILE",
                "const tick = (): void => { void this.reconcileWorkstation() }" in s
                and "setInterval(tick, 2500)" in s)
    ok &= check("RECONCILE_REUSES_ACTIVE_CYCLE",
                "if (this.workstationReconcileInFlight) return this.workstationReconcileInFlight" in s)
    ok &= check("RECONCILE_TRACKS_CYCLE",
                "this.workstationReconcileInFlight = tracked" in s)
    ok &= check("RECONCILE_RELEASES_AFTER_COMPLETION",
                "if (this.workstationReconcileInFlight === tracked)" in s
                and "this.workstationReconcileInFlight = null" in s)

    ok &= check("PER_CARD_SINGLE_FLIGHT_PRESERVED",
                "if (this.workstationInFlight.has(cardId)) return" in s
                and "this.workstationInFlight.add(cardId)" in s)
    ok &= check("H1_FULL_RECONCILE_ERROR_CLEAR_PRESERVED",
                "000093V5H1: never expose a half-successful reconcile" in s)
    h1 = s.find("000093V5H1: never expose a half-successful reconcile")
    pickup = s.find("if (evidenceNeedsPickup) await this.retrieveEvidence(card)", h1)
    clear = s.find("card.workstationLastError = null", pickup)
    ok &= check("H1_ERROR_CLEAR_AFTER_EVIDENCE", h1 >= 0 and pickup > h1 and clear > pickup)

    ok &= check("OBSERVABILITY_TAP_PRESERVED",
                "await this.evidenceObservability.observeAndPersist({" in s)
    ok &= check("RAY_EVIDENCE_BRIDGE_PRESERVED",
                "000082V5 — Ray Evidence optic-nerve bridge." in s)
    ok &= check("ACK_HUMAN_GATE_PRESERVED",
                "EVIDENCE_ACK_HUMAN_PUBLISH_PRECONDITION_FAILED" in s)
    ok &= check("NO_DOM_SCRAPE",
                "executeJavaScript" not in s and "webContents.executeJavaScript" not in s)

    if not ok:
        return 21

    tc = run_npm("run", "typecheck")
    if tc != 0:
        return 30 if tc < 124 else tc

    build = run_npm("run", "build")
    if build != 0:
        return 31 if build < 124 else build

    emit("DISPATCH_SNAPSHOT_OSCILLATION_REPAIR=PASS")
    emit("EXPECTED_RUNTIME=timer and renderer pull-through share one completed reconciliation snapshot")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
