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
            cmd, cwd=ROOT, text=True, capture_output=True,
            errors="replace", timeout=180, shell=False
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
        emit("STDOUT_TAIL=" + p.stdout[-22000:].replace("\r",""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-22000:].replace("\r",""))
    return p.returncode

def section(text: str, start: str, end: str) -> str:
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:] if b < 0 else text[a:b]

def main() -> int:
    emit("=== SESSION PORTAL HEADER LANE PULSE TRUTH REPAIR 000098V5 ===")
    emit("PRODUCTION_SCOPE=src/main/vra/vra-dispatch-service.ts")
    emit("RENDERER_SOURCE_MUTATION=ZERO")
    emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
    emit("SAFETY_DURABLE_HISTORY_MUTATION=ZERO")

    if not SERVICE.is_file():
        return 20

    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    state_block = section(s, "  state(): VraDispatchState {", "  async refreshState()")
    active_block = section(
        s,
        "  private currentExecutionLaneEntries(",
        "  private cardForRenderer("
    )

    ok = True
    ok &= check("000098_MARKER",
        "000098V5: Header Lane Pulse is observation-only" in state_block)
    ok &= check("METRICS_ACTIVE_LANES_CURRENT",
        "activeLanes: [...this.workstationSafety.metrics.activeLanes]" in state_block)
    ok &= check("LAST_TRANSITION_NO_RAW_HISTORY",
        "activeLanes: [...this.workstationSafety.lastTransition.activeLanes]" not in state_block)
    ok &= check("LAST_TRANSITION_PROJECTS_CURRENT_METRICS",
        "activeLanes: this.workstationSafety.metrics" in state_block
        and "? [...this.workstationSafety.metrics.activeLanes]" in state_block
        and ": []" in state_block)
    ok &= check("ACTIVE_ZERO_ALL_OFF_PRESERVED",
        "if (activeJobs === 0) return []" in s)
    ok &= check("TERMINAL_LANES_NOT_CURRENT_ACTIVE",
        all(x not in active_block for x in [
            "'READY'", "'WAITING_HUMAN_APPLY'", "'VERIFIED'",
            "'FAILED'", "'ROLLED_BACK'", "'CANCELLED'"
        ]))
    ok &= check("ACTIVE_LANES_CAPPED_TO_ACTIVE_JOBS",
        "return active.slice(0, activeJobs)" in active_block)

    # 000096 FIFO and prior repair invariants remain untouched.
    ok &= check("EVIDENCE_FIFO_PRESERVED",
        "cards: this.cardsForRenderer()" in s
        and "card.workstationEvidenceReturnState === 'RETURN_QUEUED'" in s
        and "const heads = new Map<string, string>()" in s)
    ok &= check("OBSERVABILITY_TAP_PRESERVED",
        "await this.evidenceObservability.observeAndPersist({" in s)
    ok &= check("RECONCILE_SINGLE_FLIGHT_PRESERVED",
        "private workstationReconcileInFlight: Promise<void> | null = null" in s
        and "if (this.workstationReconcileInFlight) return this.workstationReconcileInFlight" in s)
    ok &= check("HUMAN_GATE_PRESERVED",
        "EVIDENCE_ACK_HUMAN_PUBLISH_PRECONDITION_FAILED" in s)
    ok &= check("EXACT_ORIGIN_PRESERVED",
        "EVIDENCE_ACK_ORIGIN_FAIL_CLOSED" in s)
    ok &= check("NO_DOM_SCRAPE",
        "executeJavaScript" not in s and "webContents.executeJavaScript" not in s)

    if not ok:
        return 21

    rc = run_npm("run", "typecheck")
    if rc != 0:
        return 30 if rc < 124 else rc

    rc = run_npm("run", "build")
    if rc != 0:
        return 31 if rc < 124 else rc

    emit("HEADER_LANE_PULSE_TRUTH_REPAIR=PASS")
    emit("ABSOLUTE_CONTRACT=ACTIVE_JOBS_ZERO_IMPLIES_BOTH_RENDERER_LANE_ARRAYS_EMPTY")
    emit("EXPECTED_UI=00/32_ACTIVE_AND_ZERO_LIT_CELLS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
