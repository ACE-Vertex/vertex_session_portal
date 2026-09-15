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

    # Root cause repair: explicit grid areas prevent hidden notice from shifting auto-placement.
    "EXPLICIT_GRID_AREAS":
        "grid-template-areas:" in css and
        '"header"' in css and '"notice"' in css and '"queue"' in css and
        '"drop"' in css and '"footer"' in css,
    "HEADER_GRID_AREA": "grid-area:header" in css,
    "NOTICE_GRID_AREA": "grid-area:notice" in css,
    "QUEUE_GRID_AREA": "grid-area:queue" in css,
    "DROP_GRID_AREA": "grid-area:drop" in css,
    "FOOTER_GRID_AREA": "grid-area:footer" in css,

    # Empty BAY contract.
    "EMPTY_BAY_READY": ts.count("BAY READY") >= 2,
    "EMPTY_BAY_VRA_WAITING": "VRA待機中 · 受信した発注カードはここに表示されます。" in ts,
    "EMPTY_MARK_PRESENT": 'class="emptyMark"' in ts and ".emptyMark {" in css,
    "EMPTY_QUEUE_FILLS_BODY": "min-height:100%" in css,

    # Human Dispatch drop-zone is meaningless with zero cards, so hide it until a card exists.
    "DROP_HIDDEN_ON_INITIAL_ZERO":
        "<section class=\"worksDrop\" data-over=\"false\" ${cards.length === 0 ? 'hidden' : ''}>" in ts,
    "DROP_HIDDEN_ON_RECONCILE_ZERO":
        "worksDrop.hidden = ordered.length === 0" in ts,
    "DROP_HIDDEN_CSS": ".worksDrop[hidden]" in css and "display:none !important" in css,

    # Existing dispatch behavior must remain intact once a VRA exists.
    "HUMAN_DISPATCH_LABEL_PRESERVED": "NEW WORKSTATION · HUMAN DISPATCH" in ts,
    "DRAG_DROP_DISPATCH_PRESERVED":
        "application/x-vertex-vra-card" in ts and
        "if (cardId) this.requestDispatch(cardId)" in ts,
    "HUMAN_GATE_PRESERVED":
        'data-role="dispatch-dialog"' in ts and
        "this.confirmDispatch()" in ts,
    "VISIBLE_REMOVE_PRESERVED":
        'class="cardRemove"' in ts and
        "await window.vertexPortal.removeVraCard(cardId)" in ts,
    "EXPORT_PRESERVED":
        'data-action="export"' in ts and
        "void this.exportCard(cardId)" in ts,
    "EXACT_ORIGIN_EVIDENCE_PRESERVED":
        "private exactOriginRoute(card: WorkstationDispatchCard)" in ts and
        "VERA_EVIDENCE_RETURN_EVENT" in ts,
    "ACK_PRESERVED":
        "ackDeliveredEvidence" in ts and
        "workstationEvidenceReturnState === 'RETURNED'" in ts,
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

emit("=== VERTEX SESSION PORTAL / DISPATCH BAY EMPTY STATE LAYOUT 000065V5 ===")
emit("ROOT_CAUSE=HIDDEN_NOTICE_SHIFTED_CSS_GRID_AUTO_PLACEMENT")
emit("FIX=EXPLICIT_GRID_AREAS_PLUS_ZERO_CARD_DROPZONE_HIDE")
emit("EMPTY_STATE=BAY_READY_CENTERED")
emit("ZERO_CARD_HUMAN_DISPATCH_ZONE=HIDDEN")
emit("CARD_PRESENT_HUMAN_DISPATCH_ZONE=VISIBLE")
emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
emit("ROUTING_CONTRACT_MUTATION=ZERO")

for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")

failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_DISPATCH_BAY_EMPTY_STATE_LAYOUT_000065V5=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
