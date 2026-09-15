from __future__ import annotations
from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
BRIDGE = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def emit(v):
    print(str(v).encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)

def check(name, ok):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def run_npm(*args):
    p = subprocess.run(
        [str(NPM), *args], cwd=ROOT, text=True, capture_output=True,
        errors="replace", timeout=240, shell=False
    )
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-18000:].replace("\r", ""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-18000:].replace("\r", ""))
    return p.returncode

def main():
    emit("=== AUTO FULL EXECUTION AUTHORITY 000109V5H1 ===")
    emit("H1_FIX=AUTO_BUTTON_TITLE_ANCHOR")
    emit("AUTO_HUMAN_GATE=TASK_PLUS_VRA_EXECUTION")
    emit("LANE_ALLOCATION_AUTHORITY=WORKSTATION")

    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    b = BRIDGE.read_text(encoding="utf-8", errors="replace")
    l = LANE.read_text(encoding="utf-8", errors="replace")

    ok = True
    ok &= check("MAIN_AUTO_SCAN_OWNER",
        "private reconcileAutoAuthorizedStagedCards(): void" in s)
    ok &= check("FAST_CAPTURE_SCAN",
        "this.scheduleAutoAuthorizedDispatchScan()" in s
        and "private scheduleAutoAuthorizedDispatchScan(delayMs = 220): void" in s)
    ok &= check("HEALTH_RECONCILE_AUTO_SCAN",
        "this.reconcileAutoAuthorizedStagedCards()" in s
        and "if (!(await this.probeWorkstationHealth())) return" in s)
    ok &= check("WORKSTATION_SAFETY_GATE",
        "this.workstationSafety.online !== true" in s
        and "this.workstationSafety.state !== 'RUNNING'" in s
        and "this.workstationSafety.newWorkAllowed !== true" in s)
    ok &= check("CAPTURE_AFTER_GRANT_ONLY",
        "captured >= granted" in s)
    ok &= check("EXACT_SELF_AUTHORITY_PRECEDENCE",
        "lease.controller_session === card.originSession" in s
        and "if (self.length === 1) return self[0]" in s)
    ok &= check("DELEGATED_UNAMBIGUOUS_ONLY",
        "if (candidates.length === 1) return candidates[0]" in s
        and "Multiple overlapping controllers without an exact owner are ambiguous" in s)
    ok &= check("SHARED_PUBLISH_PATH",
        "const result = this.publishApprovedCard(card)" in s)
    ok &= check("AUTO_IPC_IDEMPOTENT",
        "AUTO_VRA_DISPATCH_IDEMPOTENT" in s
        and "card.dispatchPhase === 'PUBLISHED'" in s)
    ok &= check("HUMAN_AUTO_GRANT_TRIGGERS_SCAN",
        "AUTO_AUTHORITY_GRANTED" in s
        and "Human AUTO arm is the execution authority grant" in s)
    ok &= check("RESTART_FAIL_CLOSED_PRESERVED",
        "PORTAL_PROCESS_RESTART_FAIL_CLOSED" in s)
    ok &= check("AUTO_OFF_REVOKE_PRESERVED",
        "HUMAN_AUTO_DISARM" in s)
    ok &= check("LANE_AUTHORITY_NOT_ASSIGNED_BY_PORTAL",
        "Never assign allocatedLane here. Final Lane Allocation Authority is Workstation." in s)

    ok &= check("AUTO_SCOPE_ALL_FIVE_FOR_DELEGATION",
        "allowed_sessions: Array.from(VALID_SESSIONS).sort()" in b)
    ok &= check("AUTO_STATUS_FULL_EXECUTION_SEMANTICS",
        "AUTO● · FULL EXECUTION AUTHORITY ON · TASK + VRA" in b)
    ok &= check("AUTO_BUTTON_TITLE_FULL_EXECUTION_SEMANTICS",
        "autoButton.title = 'Vertex AUTO · Task Dispatch + VRA Execution Authority'" in b)
    ok &= check("TASK_RECEIVE_RULE_PRESERVED",
        "TARGET_READINESS_QUEUE_IS_NATIVE" in b
        and "STRUCTURED_RESULT_RETURN_IS_NATIVE" in b)

    ok &= check("SHIFT_SELECTION_000107_PRESERVED",
        "queue?.addEventListener('mousedown', event => {" in l
        and "window.getSelection()?.removeAllRanges()" in l)
    ok &= check("TEST_RERUN_GATE_PRESERVED",
        "if (!this.explicitTestCard(card)) return ''" in l)

    if not ok:
        return 21

    emit("RUN=npm run typecheck")
    if run_npm("run", "typecheck") != 0:
        return 30

    emit("RUN=npm run build")
    if run_npm("run", "build") != 0:
        return 31

    emit("AUTO_FULL_EXECUTION_AUTHORITY=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
