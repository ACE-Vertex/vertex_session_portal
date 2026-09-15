from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def emit(text):
    print(str(text).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""

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
        emit("STDOUT_TAIL=" + cp.stdout[-7000:].replace("\n", " | "))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-5000:].replace("\n", " | "))
    return cp

lane = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
css = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.css")

checks = {}

# Dedicated Human Gate modal replaces native confirm for Workstation dispatch.
checks["DISPATCH_MODAL_PRESENT"] = all(x in lane for x in [
    'data-role="dispatch-dialog"',
    'data-action="dispatch-cancel"',
    'data-action="dispatch-confirm"',
    "工場へ発注しますか？",
    "Human Approvalを確定し、新工場へVRAを送ります。",
])
checks["NATIVE_DISPATCH_CONFIRM_RETIRED"] = "このVRAをVertex Workstationへ発注しますか？" not in lane
checks["DISPATCH_BUTTON_OPENS_MODAL"] = "this.requestDispatch(cardId)" in lane
checks["MODAL_CONFIRM_DISPATCHES"] = "if (cardId) void this.dispatch(cardId)" in lane
checks["MODAL_CANCEL_SAFE"] = "this.closeDispatchDialog()" in lane
checks["DIALOG_CANCEL_EVENT"] = "addEventListener('cancel'" in lane
checks["DIALOG_BACKDROP_CANCEL"] = "if (event.target === dispatchDialog) this.closeDispatchDialog()" in lane

# Card removal remains available and explicitly protected.
checks["REMOVE_CARD_PRESERVED"] = 'data-action="remove"' in lane and "removeVraCard(cardId)" in lane
checks["REMOVE_CONFIRM_PRESERVED"] = "このVRAカードをDispatch Bayから削除しますか？" in lane
checks["REMOVE_NOT_JOB_CANCEL_WARNING"] = "WorkstationのJobや実行を取り消す操作ではありません" in lane
checks["REMOVE_INSIDE_DETAILS"] = 'class="removeDanger" data-action="remove"' in lane

# Human factory vocabulary.
for label in ["未発注", "発注済み", "作業中", "検証済み", "返却中", "清算済み", "要確認"]:
    checks[f"FACTORY_STAGE_{label}"] = label in lane
checks["RETURNED_MAPS_SETTLED"] = "if (card.workstationEvidenceReturnState === 'RETURNED') return '清算済み'" in lane
checks["EXECUTING_MAPS_WORKING"] = "if (systemStatus === 'EXECUTING') return '作業中'" in lane
checks["EVIDENCE_MAPS_VERIFIED"] = "return '検証済み'" in lane
checks["ACK_PENDING_MAPS_RETURNING"] = "if (systemStatus === 'ACK_PENDING') return '返却中'" in lane

# Human surface is factory-state; system status remains auditable in DETAILS.
checks["FACTORY_BADGE_VISIBLE"] = 'data-factory-stage="${escapeHtml(factoryStage)}"' in lane
checks["SYSTEM_STATUS_TOOLTIP"] = 'title="SYSTEM STATUS · ${escapeHtml(displayStatus)}"' in lane
checks["DETAIL_FACTORY_STATE"] = "this.field('FACTORY STATE', factoryStage)" in lane
checks["DETAIL_SYSTEM_STATUS"] = "this.field('SYSTEM STATUS', displayStatus)" in lane
checks["PATCH_FACTORY_STATE_IN_PLACE"] = "status.dataset.factoryStage = factoryStage" in lane
checks["STABLE_DOM_IDENTITY_PRESERVED"] = "card.jobId?.trim() || card.artifactId?.trim() || card.id" in lane
checks["KEYED_RECONCILE_PRESERVED"] = "private reconcileCards(): void" in lane
checks["SCROLL_PRESERVED"] = "queue.scrollTop = scrollTop" in lane

# Footer becomes factory counts.
checks["FOOTER_UNDISPATCHED"] = '未発注 <strong data-role="staged-count">' in lane
checks["FOOTER_DISPATCHED"] = '発注済み <strong data-role="dispatched-count">' in lane
checks["FOOTER_SETTLED"] = '清算済み <strong data-role="settled-count">' in lane
checks["SETTLED_COUNT_PATCH"] = "settledCount.textContent = String(settled.length)" in lane

# Modal styling follows Portal theme.
checks["DIALOG_STYLE_PRESENT"] = ".dispatchDialog {" in css
checks["DIALOG_BACKDROP_STYLE"] = ".dispatchDialog::backdrop" in css
checks["DIALOG_CONFIRM_STYLE"] = ".dialogConfirm" in css
checks["FACTORY_STAGE_STYLE"] = 'data-factory-stage="清算済み"' in css

# 000060 protections must remain.
checks["EXPORT_SUCCESS_QUIET"] = "EXPORTED · HUMAN DESTINATION" not in lane
checks["EXPORT_FAILURE_VISIBLE"] = "EXPORT FAILED ·" in lane
checks["EVIDENCE_RETURN_PRESERVED"] = "VERA_EVIDENCE_RETURN_EVENT" in lane
checks["EVIDENCE_ACK_PRESERVED"] = "acknowledgeVraEvidenceDelivery" in lane
checks["PATH_HIDDEN"] = all(x not in lane[lane.find("private cardTemplate"):lane.find("private bind")]
                            for x in ["stagedPath", "worksPath", "project_root"])

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"], 1800).returncode == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"], 1800).returncode == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== VERTEX SESSION PORTAL / FACTORY CARD HUMAN GATE 000061V5 ===")
emit("HOT_UPDATE=YES")
emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
for name, ok in checks.items():
    emit(f"{name}={'PASS' if ok else 'FAIL'}")

failed = [name for name, ok in checks.items() if not ok]
emit("VERTEX_SESSION_PORTAL_FACTORY_CARD_HUMAN_GATE_000061V5=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
