from __future__ import annotations
from pathlib import Path
import subprocess, traceback

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def emit(v: object) -> None:
    print(str(v).encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)

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
        emit("STDOUT_TAIL=" + p.stdout[-18000:].replace("\r",""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-18000:].replace("\r",""))
    return p.returncode

def main() -> int:
    emit("=== SESSION PORTAL TEST CARD RE-RUN GATE 000102V5 ===")
    emit("NORMAL_CARD_RERUN_UI=ZERO")
    emit("RERUN_RESULT=NEW_STAGED_TEST_CARD")
    emit("HUMAN_APPROVAL_RESET=PENDING")

    if not SERVICE.is_file() or not LANE.is_file():
        return 20

    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    r = LANE.read_text(encoding="utf-8", errors="replace")
    export_block = section(s, "  exportCard(cardId: string): string {", "  private explicitTestCard(")
    backend_gate = section(s, "  private requireTestRerunSource(", "  private stageTestCardRerun(")
    backend_rerun = section(s, "  private stageTestCardRerun(", "  /**\n   * Explicit Human dispatch boundary.")
    renderer_button = section(r, "  private testRerunButton(", "  private async rerunTestCard(")
    renderer_rerun = section(r, "  private async rerunTestCard(", "  private requestDispatch(")
    card_template = section(r, "  private cardTemplate(", "  private bind():")

    ok = True
    ok &= check("CANONICAL_TEST_MARKER_EXACT",
        "const VRA_TEST_CARD_KIND = 'TEST' as const" in s
        and "this.scalar(manifest.card_kind) === VRA_TEST_CARD_KIND" in s)
    ok &= check("NON_TEST_BACKEND_FAIL_CLOSED",
        "VRA_TEST_RERUN_NON_TEST_DENIED" in backend_gate
        and "this.explicitTestCard(card)" in backend_gate)
    ok &= check("MANIFEST_TEST_MARKER_REVALIDATED",
        "VRA_TEST_RERUN_MANIFEST_TEST_MARKER_REQUIRED" in backend_gate)
    ok &= check("SETTLED_TEST_REQUIRED",
        "VRA_TEST_RERUN_SOURCE_NOT_SETTLED" in backend_gate
        and "workstationEvidenceReturnState === 'RETURNED'" in s)
    ok &= check("PENDING_CHILD_DUPLICATE_GUARD",
        "VRA_TEST_RERUN_CHILD_ALREADY_PENDING" in backend_gate)
    ok &= check("NEW_IDENTITIES",
        "nextArtifactId" in backend_rerun
        and "nextJobId" in backend_rerun
        and "nextCorrelationId" in backend_rerun
        and "testRunId = randomUUID()" in backend_rerun)
    ok &= check("ORIGIN_PRESERVED",
        "origin_vera: source.originVera" in backend_rerun
        and "origin_session: source.originSession" in backend_rerun
        and "origin_window: source.originWindow" in backend_rerun)
    ok &= check("LANE_AUTHORITY_PRESERVED",
        "delete nextRouting.allocated_lane" in backend_rerun
        and "delete nextRouting.execution_lane" in backend_rerun
        and "delete nextRouting.require_lane" in backend_rerun)
    ok &= check("NEW_CARD_HUMAN_GATE_RESET",
        "humanApproval: 'PENDING'" in backend_rerun
        and "dispatchPhase: 'STAGED'" in backend_rerun
        and "workstationRegistration: 'NOT_READY'" in backend_rerun)
    ok &= check("NO_AUTO_DISPATCH_FROM_RERUN",
        "this.dispatch(" not in backend_rerun
        and "publishToIncomingAtomic" not in backend_rerun)
    ok &= check("ATOMIC_TEST_ARCHIVE_COMMIT",
        "rewriteVraManifestAtomic(tempPath, nextManifest)" in backend_rerun
        and "renameSync(tempPath, stagedPath)" in backend_rerun)
    ok &= check("PRELOAD_IPC_CONTRACT_UNCHANGED",
        "TEST_RERUN_EXPORT_PREFIX" in export_block
        and "window.vertexPortal.exportVraCard(`vertex-test-rerun:${cardId}`)" in renderer_rerun)
    ok &= check("PRODUCTION_CARD_GETS_NO_RERUN_DOM",
        "if (!this.explicitTestCard(card)) return ''" in renderer_button)
    ok &= check("RERUN_BUTTON_TEST_HELPER_ONLY",
        "${this.testRerunButton(card, busy)}" in card_template
        and "data-action=\"rerun-test\"" not in card_template)
    ok &= check("RENDERER_EXPLICIT_TEST",
        "card.cardKind === 'TEST'" in r)
    ok &= check("HUMAN_GATE_PRESERVED",
        "data-human-gate=\"APPROVE + DISPATCH\"" in r
        and "card.humanApproval = 'APPROVED'" in s)
    ok &= check("EVIDENCE_FIFO_000096_PRESERVED",
        "const heads = new Map<string, string>()" in s
        and "workstationEvidenceReturnState === 'RETURN_QUEUED'" in s)
    ok &= check("HEADER_TRUTH_000098_PRESERVED",
        "000098V5: Header Lane Pulse is observation-only" in s)
    ok &= check("NO_DOM_SCRAPE",
        "executeJavaScript" not in s and "executeJavaScript" not in r)

    if not ok:
        return 21

    rc = run_npm("run", "typecheck")
    if rc != 0:
        return 30 if rc < 124 else rc

    rc = run_npm("run", "build")
    if rc != 0:
        return 31 if rc < 124 else rc

    emit("TEST_CARD_RERUN_GATE=PASS")
    emit("ABSOLUTE_UI_CONTRACT=NON_TEST_CARD_HAS_ZERO_RERUN_DOM")
    emit("RERUN_CONTRACT=TEST_ONLY_NEW_IDS_NEW_STAGING_NEW_HUMAN_APPROVAL")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
