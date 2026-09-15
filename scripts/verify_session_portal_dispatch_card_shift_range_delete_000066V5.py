from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"
ts = TS.read_text(encoding="utf-8") if TS.is_file() else ""
css = CSS.read_text(encoding="utf-8") if CSS.is_file() else ""

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
        emit("STDOUT_TAIL=" + cp.stdout[-9000:].replace("\n", " | "))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-6000:].replace("\n", " | "))
    return cp.returncode

checks = {
    "FILE_TS": TS.is_file(),
    "FILE_CSS": CSS.is_file(),
    "SELECTION_SET_PRESENT": "selectedCardIds = new Set<string>()" in ts,
    "SELECTION_ANCHOR_PRESENT": "selectionAnchorId = ''" in ts,
    "PLAIN_CLICK_SINGLE_SELECT":
        "this.selectedCardIds.clear()" in ts and
        "this.selectedCardIds.add(cardId)" in ts,
    "SHIFT_RANGE_SELECTION":
        "if (shiftKey && this.selectionAnchorId)" in ts and
        "Math.min(anchorIndex, targetIndex)" in ts and
        "Math.max(anchorIndex, targetIndex)" in ts,
    "VISIBLE_ORDER_RANGE":
        "private orderedCards()" in ts and
        "return [...staged, ...dispatched]" in ts,
    "CARD_BODY_SELECTION":
        "this.selectCard(cardId, mouse.shiftKey)" in ts,
    "INTERACTIVE_CONTROLS_EXCLUDED":
        "target?.closest('.cardDetails, .cardActions')" in ts,
    "MULTISELECT_ARIA":
        'aria-multiselectable="true"' in ts and
        'role="option"' in ts and
        "aria-selected" in ts,
    "SELECTED_VISUAL":
        '.vraCard[data-selected="true"]' in css,
    "SELECTION_COUNT_VISIBLE":
        'data-role="selection-count"' in ts and
        ".selectionCount" in css,
    "SELECTED_X_BATCH_COUNT":
        "batch ? `× ${selectedCount}` : '×'" in ts,
    "BATCH_REMOVE_FROM_SELECTION":
        "this.selectedCardIds.has(cardId) && this.selectedCardIds.size > 1" in ts and
        ".filter(card => this.selectedCardIds.has(card.id))" in ts,
    "ONE_CONFIRM_FOR_BATCH":
        "this.pendingRemoveCardIds = ids" in ts and
        "confirmRemove()" in ts,
    "SEQUENTIAL_EXISTING_REMOVE_API":
        "for (const cardId of cardIds)" in ts and
        "await window.vertexPortal.removeVraCard(cardId)" in ts,
    "WORKSTATION_JOB_CANCEL_ZERO":
        "cancelWorkstation" not in ts and
        "/v1/cancel" not in ts,
    "NATIVE_CONFIRM_RETIRED":
        "window.confirm" not in ts,
    "THEMED_REMOVE_DIALOG":
        'data-role="remove-dialog"' in ts and
        ".removeDialog" in css and
        "WorkstationのJobや実行は取り消されません" in ts,
    "REMOVE_DIALOG_ESC_BACKDROP":
        "removeDialog?.addEventListener('cancel'" in ts and
        "if (event.target === removeDialog) this.closeRemoveDialog()" in ts,
    "VISIBLE_REMOVE_PRESERVED":
        'class="cardRemove"' in ts and
        'data-action="remove"' in ts,
    "EMPTY_BAY_LAYOUT_PRESERVED":
        "BAY READY" in ts and
        "worksDrop.hidden = ordered.length === 0" in ts and
        "grid-template-areas:" in css,
    "HUMAN_DISPATCH_PRESERVED":
        "NEW WORKSTATION · HUMAN DISPATCH" in ts and
        "this.requestDispatch(cardId)" in ts,
    "EXPORT_PRESERVED":
        'data-action="export"' in ts and
        "void this.exportCard(cardId)" in ts,
    "EVIDENCE_RETURN_ACK_PRESERVED":
        "VERA_EVIDENCE_RETURN_EVENT" in ts and
        "ackDeliveredEvidence" in ts,
    "DIRECT_EXECUTION_HTTP_ZERO":
        "/v1/apply" not in ts and "/v1/verify" not in ts and "/v1/rollback" not in ts,
}

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"]) == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"]) == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== VERTEX SESSION PORTAL / SHIFT RANGE MULTI DELETE 000066V5 ===")
emit("SELECTION=PLAIN_CLICK_ANCHOR_PLUS_SHIFT_CONTIGUOUS_RANGE")
emit("BATCH_DELETE=SELECTED_X_ONE_CONFIRM")
emit("DELETE_BACKEND=EXISTING_REMOVE_VRA_CARD_SEQUENTIAL")
emit("NATIVE_CONFIRM=RETIRED")
emit("REMOVE_DIALOG=PORTAL_THEMED")
emit("WORKSTATION_JOB_CANCELLATION=ZERO")
emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")
failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_SHIFT_RANGE_MULTI_DELETE_000066V5=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
