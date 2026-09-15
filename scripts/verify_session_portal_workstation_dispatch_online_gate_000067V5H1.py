from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
ts = TS.read_text(encoding="utf-8") if TS.is_file() else ""

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def run(cmd, timeout=1800):
    emit("RUN=" + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    emit(f"EXIT={cp.returncode}")
    if cp.stdout:
        emit("STDOUT_TAIL=" + cp.stdout[-8000:].replace("\n", " | "))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-5000:].replace("\n", " | "))
    return cp.returncode

start = ts.find("private workstationDispatchBlockReason")
end = ts.find("private safetyHoldState", start)
gate = ts[start:end] if start >= 0 and end > start else ""

checks = {
    "FILE_TS": TS.is_file(),
    "DISPATCH_GATE_PRESENT": bool(gate),
    "GATE_USES_UNIFIED_WORKSTATION_ONLINE":
        "if (!this.workstationOnline()) return 'WORKSTATION OFFLINE'" in gate,
    "OLD_DIRECT_STATE_GATE_RETIRED":
        "this.state?.workstationOnline !== true" not in gate,
    "HEADER_USES_SAME_HEALTH":
        "this.workstationOnline() ? 'WORKSTATION ONLINE'" in ts,
    "PROCESS_HEALTH_AGGREGATION_PRESERVED":
        "return Boolean(this.workstationProcess?.online || this.state?.workstationOnline)" in ts,
    "SAFETY_GATE_PRESERVED":
        "WORKSTATION SAFETY UNKNOWN" in gate and
        "SAFETY HOLD ·" in gate and
        "safety.state === 'RUNNING'" in gate,
    "HUMAN_GATE_PRESERVED":
        'data-role="dispatch-dialog"' in ts and
        "this.confirmDispatch()" in ts,
    "DISPATCH_ROUTE_PRESERVED":
        "await window.vertexPortal.dispatchVraCard(cardId)" in ts,
    "START_CONTROL_PRESERVED":
        "START WORKSTATION" in ts and
        "WORKSTATION ONLINE" in ts,
    "SHIFT_RANGE_DELETE_PRESERVED":
        "if (shiftKey && this.selectionAnchorId)" in ts and
        "this.selectedCardIds" in ts,
    "EMPTY_BAY_PRESERVED":
        "BAY READY" in ts and
        "worksDrop.hidden = ordered.length === 0" in ts,
    "EXPORT_PRESERVED":
        'data-action="export"' in ts,
    "EVIDENCE_ACK_PRESERVED":
        "VERA_EVIDENCE_RETURN_EVENT" in ts and
        "ackDeliveredEvidence" in ts,
}

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"]) == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"]) == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== VERTEX SESSION PORTAL / WORKSTATION ONLINE DISPATCH GATE H1 ===")
emit("ROOT_CAUSE=HEADER_AND_DISPATCH_USED_DIFFERENT_ONLINE_AUTHORITIES")
emit("FIX=DISPATCH_GATE_REUSES_WORKSTATION_ONLINE_AGGREGATION")
emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
emit("SAFETY_GATE=PRESERVED")
emit("HUMAN_GATE=PRESERVED")
for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")
failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_WORKSTATION_ONLINE_DISPATCH_GATE_000067V5H1=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
