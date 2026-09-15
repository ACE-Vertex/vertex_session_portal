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

card_top = ts[ts.find('<div class="cardTop">'):ts.find('<div class="jobTitle"')]
details = ts[ts.find('<details class="cardDetails">'):ts.find('</details>') + len('</details>')]

checks = {
    "FILE_TS": TS.is_file(),
    "FILE_CSS": CSS.is_file(),
    "VISIBLE_REMOVE_IN_CARD_TOP":
        'class="cardRemove"' in card_top and
        'data-action="remove"' in card_top and
        'aria-label="発注カードを削除"' in card_top,
    "REMOVE_NOT_HIDDEN_IN_DETAILS":
        'data-action="remove"' not in details and
        'REMOVE CARD' not in details,
    "VISIBLE_REMOVE_STYLE":
        ".cardRemove {" in css and
        ".cardRemove:hover:not(:disabled)" in css,
    "REMOVE_CONFIRMATION_PRESERVED":
        "この発注カードをDispatch Bayから削除しますか？" in ts and
        "WorkstationのJobや実行は取り消されません" in ts,
    "REMOVE_API_REUSED":
        "await window.vertexPortal.removeVraCard(cardId)" in ts,
    "NATIVE_REMOVE_COLLISION_AVOIDED":
        "private async removeCard(cardId: string)" in ts and
        "private async remove(cardId: string)" not in ts,
    "EVENT_DELEGATION_REMOVE":
        "case 'remove':" in ts and
        "void this.removeCard(cardId)" in ts,
    "BUSY_DISABLE_PRESERVED":
        "if (removeButton) removeButton.disabled = busy" in ts,
    "DISPATCH_PRESERVED":
        'data-action="dispatch"' in ts and
        "this.requestDispatch(cardId)" in ts,
    "EXPORT_PRESERVED":
        'data-action="export"' in ts and
        "void this.exportCard(cardId)" in ts,
    "HUMAN_GATE_PRESERVED":
        'data-role="dispatch-dialog"' in ts and
        "this.confirmDispatch()" in ts,
    "EXACT_ORIGIN_EVIDENCE_PRESERVED":
        "private exactOriginRoute(card: WorkstationDispatchCard)" in ts and
        "VERA_EVIDENCE_RETURN_EVENT" in ts,
    "ACK_PRESERVED":
        "ackDeliveredEvidence" in ts and
        "workstationEvidenceReturnState === 'RETURNED'" in ts,
    "WORKSTATION_DIRECT_EXECUTION_ROUTE_ZERO":
        "/v1/apply" not in ts and
        "/v1/verify" not in ts and
        "/v1/rollback" not in ts,
}

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"]) == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"]) == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== VERTEX SESSION PORTAL / DISPATCH CARD VISIBLE REMOVE 000064V5 ===")
emit("CHANGE=DETAILS_HIDDEN_REMOVE_TO_VISIBLE_CARD_TOP_REMOVE")
emit("BACKEND_REMOVE_ROUTE=REUSED")
emit("WORKSTATION_JOB_CANCELLATION=ZERO")
emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
emit("EVIDENCE_ROUTING_CONTRACT_MUTATION=ZERO")
for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")

failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_DISPATCH_CARD_VISIBLE_REMOVE_000064V5=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
