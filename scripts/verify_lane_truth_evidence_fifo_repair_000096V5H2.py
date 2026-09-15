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
        emit("STDOUT_TAIL=" + p.stdout[-24000:].replace("\r",""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-24000:].replace("\r",""))
    return p.returncode

def between(text: str, start: str, end: str) -> str:
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    if b < 0:
        return text[a:]
    return text[a:b]

def main() -> int:
    emit("=== SESSION PORTAL LANE TRUTH + EVIDENCE FIFO REPAIR 000096V5H2 ===")
    emit("H1_FAILURE_CLASS=VERIFIER_FALSE_POSITIVE")
    emit("H1_FAILED_CHECK=OLD_NULLABLE_BASENAME_RETIRED")
    emit("H2_PRODUCTION_DELTA=ZERO_FROM_H1")
    emit("PRODUCTION_SCOPE=src/main/vra/vra-dispatch-service.ts")
    emit("RENDERER_MUTATION=ZERO")
    emit("WORKSTATION_MUTATION=ZERO")

    if not SERVICE.is_file():
        emit("SERVICE=FAIL")
        return 20

    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    ok = True

    card_block = between(
        s,
        "  private cardForRenderer(",
        "  private workstationCardSyncKey("
    )
    order_block = between(
        s,
        "  private evidenceDeliveryOrderKey(",
        "  private currentExecutionLaneEntries("
    )

    # H1 type-narrowing repair, now verified only in its real owner.
    ok &= check("H1_MARKER",
                "000096V5H1: evidenceDeliveryEligible() is a runtime predicate" in card_block)
    ok &= check("CACHE_NAME_LOCAL_CAPTURE",
                "const evidenceCacheName = card.evidenceCacheName" in card_block)
    ok &= check("IDENTITY_LOCAL_CAPTURE",
                "const evidenceIdentity = card.evidenceIdentity" in card_block)
    ok &= check("CACHE_NAME_EXPLICIT_NARROW",
                "!evidenceCacheName" in card_block)
    ok &= check("IDENTITY_EXPLICIT_NARROW",
                "!evidenceIdentity" in card_block)
    ok &= check("CARD_RENDERER_BASENAME_USES_NARROWED_LOCAL",
                "basename(evidenceCacheName)" in card_block)
    ok &= check("CARD_RENDERER_OLD_NULLABLE_BASENAME_RETIRED",
                "basename(card.evidenceCacheName)" not in card_block)

    # Separate method is valid because it has an inline null guard.
    ok &= check("ORDER_KEY_INLINE_NULL_GUARD",
                "if (!card.evidenceCacheName) return" in order_block)
    ok &= check("ORDER_KEY_BASENAME_AFTER_GUARD",
                "basename(card.evidenceCacheName)" in order_block)

    # 000096 lane truth contract.
    ok &= check("ACTIVE_ZERO_ALL_OFF",
                "if (activeJobs === 0) return []" in s)
    ok &= check("SAFETY_METRICS_NORMALIZED",
                "activeLanes: this.currentExecutionLaneEntries(rawLaneStates, activeJobs)" in s)
    ok &= check("ACTIVE_LANES_CAPPED",
                "return active.slice(0, activeJobs)" in s)

    active_block = between(
        s,
        "  private currentExecutionLaneEntries(",
        "  private cardForRenderer("
    )
    ok &= check("TERMINAL_STATES_NOT_ACTIVE",
                all(x not in active_block for x in [
                    "'READY'", "'WAITING_HUMAN_APPLY'", "'VERIFIED'",
                    "'FAILED'", "'ROLLED_BACK'", "'CANCELLED'"
                ]))

    # Evidence FIFO contract.
    ok &= check("FIFO_PROJECTION",
                "cards: this.cardsForRenderer()" in s)
    ok &= check("RETURN_QUEUED_ONLY",
                "card.workstationEvidenceReturnState === 'RETURN_QUEUED'" in s)
    ok &= check("ONE_HEAD_PER_ORIGIN",
                "const heads = new Map<string, string>()" in s
                and "!heads.has(session)" in s)
    ok &= check("COMPLETION_ORDER",
                "private evidenceDeliveryOrderKey" in s
                and "timestamps.completed_at" in s)

    # Existing invariants.
    ok &= check("ACK_RETURN_QUEUED_GATE",
                "EVIDENCE_ACK_NOT_RETURN_QUEUED" in s)
    ok &= check("ACK_HUMAN_GATE",
                "EVIDENCE_ACK_HUMAN_PUBLISH_PRECONDITION_FAILED" in s)
    ok &= check("EXACT_ORIGIN",
                "EVIDENCE_ACK_ORIGIN_FAIL_CLOSED" in s)
    ok &= check("OBSERVABILITY_TAP",
                "await this.evidenceObservability.observeAndPersist({" in s)
    ok &= check("RAY_EVIDENCE_BRIDGE",
                "000082V5 — Ray Evidence optic-nerve bridge." in s)
    ok &= check("H1_STICKY_RECONCILE",
                "000093V5H1: never expose a half-successful reconcile" in s)
    ok &= check("H2_RECONCILE_SINGLE_FLIGHT",
                "private workstationReconcileInFlight: Promise<void> | null = null" in s
                and "if (this.workstationReconcileInFlight) return this.workstationReconcileInFlight" in s)
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

    emit("VERTEX_SESSION_PORTAL_000096V5H2=PASS")
    emit("EXPECTED_IDLE=00/32_ACTIVE_AND_ALL_ACTIVE_CELLS_OFF")
    emit("EXPECTED_FIFO=RETURNED_A_SUPPRESSED_THEN_B_THEN_C")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
