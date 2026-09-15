from __future__ import annotations
from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BRIDGE = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def emit(value):
    print(str(value).encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)

def check(name, ok):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def run_npm(*args):
    p = subprocess.run(
        [str(NPM), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        errors="replace",
        timeout=240,
        shell=False,
    )
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-22000:].replace("\r", ""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-22000:].replace("\r", ""))
    return p.returncode

def main():
    emit("=== VERTEX SESSION PORTAL / ARD AUTO DELEGATED DISPATCH 000106V5 ===")
    emit("AUTHORITY=HUMAN_AUTO_GATE")
    emit("AUTO_RESTART_POLICY=FAIL_CLOSED")
    emit("WORKSTATION_LANE_AUTHORITY=PRESERVED")

    if not all(p.is_file() for p in (BRIDGE, SERVICE, LANE)):
        return 20

    b = BRIDGE.read_text(encoding="utf-8", errors="replace")
    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    r = LANE.read_text(encoding="utf-8", errors="replace")

    ok = True

    # TASK / AUTO / ARD bridge
    ok &= check("TASK_BUS_000053_PRESERVED",
        "TARGET_READINESS_QUEUE_IS_NATIVE" in b
        and "SELECTIVE_TARGET_ROUTING_IS_NATIVE" in b
        and "STRUCTURED_RESULT_RETURN_IS_NATIVE" in b)
    ok &= check("AUTO_HUMAN_GATE_AUTHORITY_GRANT",
        "grantAutoAuthority(source)" in b
        and "AUTO Human Gate ON" in b)
    ok &= check("AUTO_DISARM_REVOKES_AUTHORITY",
        "await revokeAutoAuthority(source)" in b)
    ok &= check("AUTO_RENDERER_RELOAD_FAIL_CLOSED",
        "localStorage.removeItem(AUTO_AUTHORITY_KEY)" in b
        and "fresh Human AUTO arm" in b)
    ok &= check("ARD_PARENT_TASK_CONTEXT",
        "parent_dispatch_id" in b
        and "setAutoTaskContext(" in b
        and "clearAutoTaskContext(" in b)
    ok &= check("AUTO_TASK_REQUIRES_MAIN_AUTHORITY",
        "if (mode === 'AUTO' && !autoAuthority)" in b)
    ok &= check("DISTINCT_CHILD_ORIGIN_PRESERVED",
        "target_session=${target}" in b
        and "origin_session=${source}" in b)

    # Trusted main-process authority
    ok &= check("MAIN_PROCESS_AUTHORITY_LEDGER",
        "AUTO_AUTHORITY_LEDGER_SCHEMA" in s
        and "autoAuthorityPath" in s
        and "persistAutoAuthorities()" in s)
    ok &= check("MAIN_PROCESS_GRANT_REVALIDATION",
        "handleAutoAuthorityCommand" in s
        and "ARD_AUTO_CONTROLLER_SCOPE_REQUIRED" in s)
    ok &= check("MAIN_PROCESS_AUTO_DISPATCH_REVALIDATION",
        "handleAutoDispatchCommand" in s
        and "requireActiveAutoAuthority" in s)
    ok &= check("PREEXISTING_CARD_FAIL_CLOSED",
        "ARD_AUTO_PREEXISTING_CARD_FORBIDDEN" in s)
    ok &= check("EXACT_ORIGIN_FAIL_CLOSED",
        "ARD_AUTO_CARD_ORIGIN_MISMATCH" in s
        and "ARD_AUTO_CARD_ORIGIN_UNRESOLVED" in s)
    ok &= check("WORKSTATION_SAFETY_REQUIRED",
        "ARD_AUTO_WORKSTATION_NEW_WORK_NOT_ALLOWED" in s
        and "workstationSafety.newWorkAllowed !== true" in s)
    ok &= check("PORTAL_RESTART_REVOKES_AUTO",
        "PORTAL_PROCESS_RESTART_FAIL_CLOSED" in s
        and "revokeAutoAuthoritiesOnStartup()" in s)
    ok &= check("AUTO_AUDIT_DURABLE",
        "auto-authority-audit.jsonl" in s
        and "AUTO_VRA_DISPATCHED" in s)
    ok &= check("HUMAN_AND_AUTO_SHARE_ATOMIC_PUBLISH",
        "private publishApprovedCard(" in s
        and "publishToIncomingAtomic(card, destination)" in s)
    ok &= check("HUMAN_APPROVAL_STILL_DURABLE",
        "card.humanApproval = 'APPROVED'" in s
        and "card.dispatchPhase = 'APPROVED'" in s)
    ok &= check("LANE_ALLOCATION_AUTHORITY_UNCHANGED",
        "Never assign allocatedLane here" in s)
    ok &= check("FIRST_LANE_FAST_OBSERVATION_000105_PRESERVED",
        "observePostDispatchLaneTruth" in s
        and "POST_DISPATCH_OBSERVATION_WINDOW_MS = 1600" in s)
    ok &= check("TEST_RERUN_000102_PRESERVED",
        "VRA_TEST_RERUN_NON_TEST_DENIED" in s
        and "cardKind === VRA_TEST_CARD_KIND" in s)
    ok &= check("EVIDENCE_FIFO_000096_PRESERVED",
        "workstationEvidenceReturnState === 'RETURN_QUEUED'" in s
        and "const heads = new Map<string, string>()" in s)

    # Renderer auto dispatch
    ok &= check("AUTO_CARD_ROUTE_EXISTS",
        "routeAutoAuthorizedCards" in r
        and "AUTO_DISPATCH_COMMAND_PREFIX" in r)
    ok &= check("AUTO_ROUTE_ONLY_STAGED_PENDING",
        "card.status !== 'STAGED'" in r
        and "card.humanApproval !== 'PENDING'" in r)
    ok &= check("AUTO_ROUTE_CAPTURE_AFTER_GRANT",
        "captured >= granted" in r)
    ok &= check("AMBIGUOUS_AUTHORITY_FAIL_CLOSED",
        "Multiple controllers with overlapping scope" in r)
    ok &= check("ONE_CLICK_HUMAN_DISPATCH_000104_PRESERVED",
        "void this.dispatch(cardId)" in r
        and 'data-role="dispatch-dialog"' not in r)
    ok &= check("TEST_ONLY_RERUN_UI_PRESERVED",
        "if (!this.explicitTestCard(card)) return ''" in r)

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

    emit("ARD_AUTO_DELEGATED_DISPATCH=PASS")
    emit("HUMAN_GATE=AUTO_BUTTON_CLICK")
    emit("PER_CARD_CONFIRMATION=NOT_REQUIRED_WHILE_AUTHORITY_ACTIVE")
    emit("PROCESS_RESTART=AUTHORITY_REVOKED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
