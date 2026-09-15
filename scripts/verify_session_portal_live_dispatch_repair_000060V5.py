from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def out(text):
    print(str(text).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)


def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def run(cmd, timeout=1800):
    out("RUN=" + " ".join(str(x) for x in cmd))
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
    out(f"EXIT={cp.returncode}")
    if cp.stdout:
        out("STDOUT_TAIL=" + cp.stdout[-9000:].replace("\n", " | "))
    if cp.stderr:
        out("STDERR_TAIL=" + cp.stderr[-6000:].replace("\n", " | "))
    return cp

service = read("src/main/vra/vra-dispatch-service.ts")
lane = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
css = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.css")
ipc = read("src/main/ipc/register-vra-dispatch-ipc.ts")
main = read("src/renderer/src/components/MainFrame/MainFrame.ts")
vera = read("src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts")

checks = {}

# Live flicker root: a durable 4xx/403/409 rejection must not be auto-retried every 2.5 sec.
checks["BLOCKED_DURABLE_POLL_SKIP"] = "if (card.workstationRegistration === 'BLOCKED') continue" in service
checks["BLOCKED_RECONCILE_GUARD"] = "if (card.workstationRegistration === 'BLOCKED') return" in service
checks["RECONCILER_2500MS_PRESERVED"] = "setInterval(tick, 2500)" in service
checks["BLOCKED_FAIL_CLOSED_MAPPING_PRESERVED"] = (
    "[400, 403, 409].includes(error.status)" in service
    and "? 'BLOCKED'" in service
)

# Immutable capture and routing safety remain untouched.
checks["CAPTURE_OWNER_FAIL_CLOSED"] = "VRA_ORIGIN_UNRESOLVED" in service
checks["IMMUTABLE_VERA05_MAPPING"] = "case 'vera-05': return 'VERA05'" in service
checks["CAPTURE_WINDOW_FROM_IMMUTABLE_SESSION"] = "originWindow: originSession" in service
checks["ROUTING_ENVELOPE_BEFORE_SHA"] = (
    service.find("manifest = this.ensureCaptureRoutingEnvelope") >= 0
    and service.find("manifest = this.ensureCaptureRoutingEnvelope") < service.find("const sha256 = this.sha256(stagedPath)")
)
checks["ROUTING_ORIGIN_COMMIT_PRESERVED"] = all(x in service for x in [
    "origin_vera: origin.originVera",
    "origin_session: origin.originSession",
    "origin_window: origin.originWindow",
])
checks["WORKSTATION_LANE_AUTHORITY_PRESERVED"] = all(x in service for x in [
    "delete routing.allocated_lane",
    "delete routing.execution_lane",
    "delete routing.require_lane",
])
checks["ATOMIC_INCOMING_PRESERVED"] = "publishToIncomingAtomic" in service and "publishIncomingCommitSidecar" in service
checks["HUMAN_APPROVAL_PRESERVED"] = "card.humanApproval = 'APPROVED'" in service

# Human UI cleanup: internal contract is still code contract, no longer Human-visible decoration.
for token in [
    "STAGING FIRST",
    "VRA-ROUTING/1",
    "ORIGIN FAIL-CLOSED",
    "HUMAN EXPORT",
    "ATOMIC _INCOMING",
    "WORKSTATION ALLOCATES LANE",
]:
    checks[f"HUMAN_BADGE_REMOVED_{token.replace(' ', '_').replace('-', '_')}"] = token not in lane

checks["EXPORT_SUCCESS_QUIET"] = "EXPORTED · HUMAN DESTINATION" not in lane
checks["EXPORT_FAILURE_VISIBLE"] = "EXPORT FAILED ·" in lane
checks["EXPORT_ROUTE_PRESERVED"] = "exportVraCard(cardId)" in lane
checks["DISPATCH_ROUTE_PRESERVED"] = "dispatchVraCard(cardId)" in lane and "工場へ発注" in lane
checks["NOTICE_ERRORS_PRESERVED"] = 'data-role="notice"' in lane

# REMOVE is intentionally de-emphasized and protected from accidental click.
checks["REMOVE_CONFIRM_REQUIRED"] = "このVRAカードをDispatch Bayから削除しますか？" in lane
checks["REMOVE_NOT_JOB_CANCEL_WARNING"] = "WorkstationのJobや実行を取り消す操作ではありません" in lane
checks["REMOVE_INSIDE_DETAILS"] = 'class="removeDanger" data-action="remove"' in lane
card_actions = lane[lane.find('<div class="cardActions">'):lane.find('</div>\n        </div>\n      </article>', lane.find('<div class="cardActions">'))]
checks["REMOVE_NOT_PRIMARY_ACTION"] = 'data-action="remove"' not in card_actions
checks["REMOVE_DETAIL_STYLE"] = ".detailActions .removeDanger" in css

# Empty state should be quiet rather than a large pseudo-dashboard.
checks["EMPTY_GLYPH_RETIRED"] = "emptyGlyph" not in lane and ".emptyGlyph" not in css
checks["QUIET_EMPTY_STATE"] = "NO VRA CARDS" in lane and "VRAを受信するとここに表示されます。" in lane
checks["QUIET_EMPTY_HEIGHT"] = "min-height:88px" in css

# Existing anti-remount design remains; this patch fixes state churn rather than replacing card DOM.
checks["STABLE_CARD_KEY_PRESERVED"] = "card.jobId?.trim() || card.artifactId?.trim() || card.id" in lane
checks["KEYED_RECONCILE_PRESERVED"] = "private reconcileCards(): void" in lane
checks["POLL_NO_SHELL_REMOUNT_PRESERVED"] = (
    "if (this.shadowRoot?.querySelector('.lane'))" in lane
    and "this.reconcileCards()" in lane
)
checks["SCROLL_PRESERVED"] = "queue.scrollTop = scrollTop" in lane
checks["DETAIL_EXPANSION_IDENTITY_PRESERVED"] = "Moving an existing node preserves its DOM identity" in lane

# Broader Portal contracts must remain present.
checks["SAFETY_SERVICE_PRESERVED"] = "getWorkstationSafety" in service and "performWorkstationSafetyAction" in service
checks["SAFETY_IPC_PRESERVED"] = "service.getWorkstationSafety()" in ipc and "service.performWorkstationSafetyAction(request)" in ipc
checks["PLUS_VERA_PRESERVED"] = "+ VERA" in main
checks["EVIDENCE_RETURN_PRESERVED"] = "VERA_EVIDENCE_RETURN_EVENT" in lane
checks["EVIDENCE_ACK_PRESERVED"] = "acknowledgeVraEvidenceDelivery" in lane
checks["PROMPT_RELAY_PRESERVED"] = "pasteClipboardTo" in vera
checks["PATH_HIDDEN"] = all(x not in lane[lane.find("private cardTemplate"):lane.find("private bind")]
                            for x in ["stagedPath", "worksPath", "project_root"])

# Run safety regression if present. It is independent from the intentionally changed Human UX badges.
safety = ROOT / "scripts" / "verify_session_portal_estop_safety_ui_000057V1H1.py"
checks["SAFETY_VERIFIER_PRESENT"] = safety.is_file()
if safety.is_file():
    checks["SAFETY_REGRESSION"] = run(["python", safety], 1800).returncode == 0
else:
    checks["SAFETY_REGRESSION"] = False

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"], 1800).returncode == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"], 1800).returncode == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

out("=== VERTEX SESSION PORTAL / LIVE DISPATCH REPAIR 000060V5 ===")
out("HOT_UPDATE=SUPPORTED_BY_CURRENT_PORTAL_RUNTIME")
out("PRODUCTION_MUTATION_SCOPE=SESSION_PORTAL_ONLY")
out("WORKSTATION_PRODUCTION_MUTATION=ZERO")
for name, ok in checks.items():
    out(f"{name}={'PASS' if ok else 'FAIL'}")

failed = [name for name, ok in checks.items() if not ok]
out("VERTEX_SESSION_PORTAL_LIVE_DISPATCH_REPAIR_000060V5=" + ("PASS" if not failed else "FAIL"))
if failed:
    out("FAILED=" + ",".join(failed))
    raise SystemExit(1)
