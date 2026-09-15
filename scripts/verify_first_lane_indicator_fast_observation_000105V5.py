from __future__ import annotations
from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def emit(value: object) -> None:
    print(str(value).encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)

def check(name: str, ok: bool) -> bool:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def section(text: str, start: str, end: str) -> str:
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:] if b < 0 else text[a:b]

def run_npm(*args: str) -> int:
    p = subprocess.run(
        [str(NPM), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        errors="replace",
        timeout=180,
        shell=False,
    )
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-18000:].replace("\r", ""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-18000:].replace("\r", ""))
    return p.returncode

def main() -> int:
    emit("=== FIRST LANE INDICATOR FAST OBSERVATION 000105V5 ===")
    emit("POLICY=OBSERVE_REAL_WORKSTATION_TRUTH_ONLY")
    emit("OPTIMISTIC_FAKE_LANE=NO")
    emit("NORMAL_POLL_2500MS=PRESERVED")

    if not SERVICE.is_file():
        return 20

    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    dispatch = section(s, "  dispatch(cardId: string): VraDispatchCard {", "  remove(cardId: string)")
    observe = section(s, "  private async observePostDispatchLaneTruth(", "  private startWorkstationReconciler():")
    periodic = section(s, "  private startWorkstationReconciler():", "  private async probeWorkstationHealth():")

    ok = True
    ok &= check("DISPATCH_KICKS_POST_OBSERVATION",
        "void this.observePostDispatchLaneTruth(card.id)" in dispatch)
    ok &= check("CARD_REGISTRATION_PRECEDES_SAFETY_BURST",
        "await this.reconcileWorkstationCard(cardId)" in observe
        and observe.find("await this.reconcileWorkstationCard(cardId)") <
            observe.find("this.kickPostDispatchSafetyProbe()"))
    ok &= check("SAFETY_TRUTH_IS_SOURCE",
        "await this.probeWorkstationHealth()" in observe)
    ok &= check("SHORT_OBSERVATION_WINDOW",
        "POST_DISPATCH_OBSERVATION_WINDOW_MS = 1600" in observe
        and "POST_DISPATCH_OBSERVATION_INTERVAL_MS = 180" in observe)
    ok &= check("BURST_COALESCED",
        "workstationPostDispatchProbeInFlight" in s
        and "if (this.workstationPostDispatchProbeInFlight) return" in observe)
    ok &= check("RAPID_DISPATCH_EXTENDS_DEADLINE",
        "Math.max(" in observe
        and "workstationPostDispatchProbeDeadlineMs" in observe)
    ok &= check("NO_OPTIMISTIC_ALLOCATED_LANE",
        "allocatedLane =" not in observe
        and "allocated_lane =" not in observe)
    ok &= check("WORKSTATION_LANE_AUTHORITY_PRESERVED",
        "Never assign allocatedLane here" in dispatch)
    ok &= check("PERIODIC_2500MS_PRESERVED",
        "setInterval(tick, 2500)" in periodic)
    ok &= check("RECONCILE_COALESCING_000093_PRESERVED",
        "workstationReconcileInFlight" in s)
    ok &= check("HEADER_TRUTH_000098_PRESERVED",
        "000098V5: Header Lane Pulse is observation-only" in s)
    ok &= check("EVIDENCE_FIFO_000096_PRESERVED",
        "const heads = new Map<string, string>()" in s
        and "workstationEvidenceReturnState === 'RETURN_QUEUED'" in s)
    ok &= check("TEST_RERUN_000102_PRESERVED",
        "VRA_TEST_RERUN_NON_TEST_DENIED" in s
        and "cardKind === VRA_TEST_CARD_KIND" in s)
    ok &= check("HUMAN_GATE_PRESERVED",
        "card.humanApproval = 'APPROVED'" in dispatch)
    ok &= check("ATOMIC_PUBLISH_PRESERVED",
        "publishToIncomingAtomic(card, destination)" in dispatch)

    if not ok:
        return 21

    emit("RUN=npm run typecheck")
    rc = run_npm("run", "typecheck")
    if rc != 0:
        return 30

    emit("RUN=npm run build")
    rc = run_npm("run", "build")
    if rc != 0:
        return 31

    emit("FIRST_LANE_INDICATOR_FAST_OBSERVATION=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
