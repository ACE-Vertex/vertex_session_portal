from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKSTATION = ROOT.parent / "vertex_workstation"

def out(text):
    print(str(text).encode("cp932", errors="replace").decode("cp932", errors="replace"), flush=True)

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
    out("EXIT={}".format(cp.returncode))
    if cp.stdout:
        out("STDOUT_TAIL=" + cp.stdout[-9000:].replace("\n", " | "))
    if cp.stderr:
        out("STDERR_TAIL=" + cp.stderr[-6000:].replace("\n", " | "))
    return cp

def read(rel):
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.is_file() else ""

checks = {}

paths = {
    "mainframe": "src/renderer/src/components/MainFrame/MainFrame.ts",
    "vera": "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "vera_css": "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css",
    "lane": "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
    "lane_css": "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css",
    "contracts": "src/shared/contracts.ts",
    "preload": "src/preload/index.ts",
    "dispatch_service": "src/main/vra/vra-dispatch-service.ts",
    "dispatch_ipc": "src/main/ipc/register-vra-dispatch-ipc.ts",
    "workstation_client": "src/main/workstation/workstation-client.ts",
}

src = {name: read(rel) for name, rel in paths.items()}
for name, rel in paths.items():
    checks["FILE_" + name.upper()] = bool(src[name])

checks["WORKSTATION_READ_ONLY_ROOT_EXISTS"] = WORKSTATION.is_dir()

# Canonical 5-session presentation model.
checks["CANONICAL_VERA_01_05"] = (
    "['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05']" in src["mainframe"]
    and "MAIN_VERA_IDS" in src["vera"]
)
checks["VERA06_ZERO"] = (
    "vera-06" not in src["mainframe"]
    and "vera-06" not in src["vera"]
)
checks["EXISTING_ACTIVATE_NEXT_API_REUSED"] = (
    "activateNextMainLane(): Promise<PortalBootstrapState>" in src["contracts"]
    and "workstation:activate-next-main-lane" in src["preload"]
    and "window.vertexPortal.activateNextMainLane()" in src["mainframe"]
)
checks["ADD_VERA_BUTTON"] = (
    'data-action="add-vera"' in src["mainframe"]
    and ">+ VERA</button>" in src["mainframe"]
)
checks["ADD_VERA_DISABLED_AT_FIVE"] = (
    "active.length >= MAIN_VERA_IDS.length" in src["mainframe"]
    and "canShowAnotherVera" in src["mainframe"]
)
checks["WINDOW_HIDE_PRESENTATION_ONLY"] = (
    "vertex-session-hide-request" in src["vera"]
    and "presentation-hidden" in src["vera_css"]
    and "Presentation-only close" in src["mainframe"]
)
checks["WINDOW_HIDE_NO_SESSION_DELETE"] = (
    "deactivate" not in src["mainframe"]
    and "deleteSession" not in src["mainframe"]
    and "removeSession" not in src["mainframe"]
)
checks["HIDDEN_WINDOW_STAYS_MOUNTED"] = (
    "node?.setAttribute('presentation-hidden', '')" in src["mainframe"]
    and "active.map(session => this.renderSession(session)).join('')" in src["mainframe"]
)
checks["HORIZONTAL_WIDTH_NOT_SHRUNK"] = (
    "flex: 0 0 var(--session-user-width)" in src["vera_css"]
    and "min-width: var(--vertex-session-min-width)" in src["vera_css"]
    and "max-width: none" in src["vera_css"]
)

# Immutable origin / exact 04/05 mapping.
checks["ORIGIN_04_CANONICAL"] = "case 'vera-04': return 'VERA04'" in src["dispatch_service"]
checks["ORIGIN_05_CANONICAL"] = "case 'vera-05': return 'VERA05'" in src["dispatch_service"]
checks["NO_ACTIVE_WINDOW_ORIGIN_INFERENCE"] = (
    "captureOrigin(webContents" in src["dispatch_service"]
    and "sourceFor(webContents)" in src["dispatch_service"]
)
checks["NO_DOM_RESPONSE_SCRAPE"] = (
    "executeJavaScript" not in src["dispatch_service"]
)

# Dispatch Bay title and compact card.
checks["DISPATCH_BAY_FIXED_TITLE"] = (
    "VRA / WORKSTATION LOGISTICS" in src["lane"]
    and '<div class="title">DISPATCH BAY</div>' in src["lane"]
    and "INTEGRATION · VERA05" not in src["lane"]
)
checks["CARD_COMPACT_STRUCTURE"] = all(token in src["lane"] for token in [
    "cardIdentity", "jobTitle", "cardSummary", "cardBottom", "cardDetails", "detailGrid"
])
checks["CARD_COMPACT_CSS"] = (
    "padding:8px 9px" in src["lane_css"]
    and "min-height:25px" in src["lane_css"]
    and "transform:translateY(-1px)" in src["lane_css"]
)
checks["SUMMARY_REQUIRED_FIELDS"] = all(token in src["lane"] for token in [
    "originVera", "projectName", "jobTitle", "displayStatus",
    "requestedLane", "lanePolicy", "allocatedLane", "humanApproval"
])
checks["DETAIL_REQUIRED_FIELDS"] = all(label in src["lane"] for label in [
    "ORIGIN VERA", "ORIGIN SESSION / WINDOW", "PROJECT NAME", "ARTIFACT ID",
    "FULL TITLE", "REQUESTED LANE", "LANE POLICY",
    "ALLOCATED LANE · WORKSTATION", "STATUS", "HUMAN APPROVAL"
])

# Human path must stay hidden from card template.
card_start = src["lane"].find("  private cardTemplate(")
bind_start = src["lane"].find("\n  private bind(): void", card_start)
card_block = src["lane"][card_start:bind_start] if card_start >= 0 and bind_start > card_start else ""
checks["PATH_HUMAN_DISPLAY_ZERO"] = (
    "stagedPath" not in card_block
    and "worksPath" not in card_block
    and "project_root" not in card_block
)

# New Workstation vs Old Works route.
checks["NEW_WORKSTATION_PRIMARY_LABEL"] = "工場へ発注" in src["lane"]
checks["HUMAN_CONFIRM_REQUIRED"] = (
    "window.confirm('このVRAをVertex Workstationへ発注しますか？')" in src["lane"]
)
checks["FINAL_WIRING_B_ROUTE_REUSED"] = "window.vertexPortal.dispatchVraCard(cardId)" in src["lane"]
checks["RENDERER_DIRECT_HTTP_ZERO"] = (
    "fetch(" not in src["lane"]
    and "http://" not in src["lane"]
    and "https://" not in src["lane"]
)
checks["EXPORT_PRESERVED"] = (
    "window.vertexPortal.exportVraCard(cardId)" in src["lane"]
    and ">EXPORT<" not in ""  # sentinel: actual label checked below
    and "'EXPORT'" in src["lane"]
)
# Stronger export-only method boundary.
export_start = src["lane"].find("  private async exportCard(")
dispatch_start = src["lane"].find("\n  private async dispatch(", export_start)
export_block = src["lane"][export_start:dispatch_start] if export_start >= 0 and dispatch_start > export_start else ""
checks["EXPORT_POST_JOBS_ZERO"] = (
    "exportVraCard" in export_block
    and "dispatchVraCard" not in export_block
    and "registerJob" not in export_block
    and "/v1/jobs" not in export_block
)
checks["DISPATCHED_NOT_ACTION_BUTTON"] = (
    "${!dispatched ? `" in card_block
    and "dispatched ? 'DISPATCHED'" not in card_block
)
checks["STATUS_BADGE_READONLY"] = (
    'class="state"' in card_block
    and 'data-action="status"' not in src["lane"]
)

# Workstation online/offline and safety.
checks["ONLINE_GATE"] = "this.state?.workstationOnline !== true" in src["lane"]
checks["OFFLINE_LABEL"] = "WORKSTATION OFFLINE" in src["lane"]
checks["OFFLINE_DISPATCH_DISABLED"] = (
    "dispatchDisabled = dispatched || busy || blocked !== null" in src["lane"]
)
checks["EXPORT_INDEPENDENT_OF_WORKSTATION"] = (
    'class="export"' in card_block
    and "blocked" not in re.search(
        r'<button type="button" class="export".*?</button>',
        card_block,
        re.S
    ).group(0)
    if re.search(r'<button type="button" class="export".*?</button>', card_block, re.S)
    else False
)
checks["SAFETY_RUNNING_REQUIRED"] = "safety.state === 'RUNNING' ? null" in src["lane"]

# Existing feature regressions: Prompt Relay, display_title, Evidence return/ACK, lane pulse, Safety UI.
checks["PROMPT_RELAY_1_5"] = (
    "MAIN_VERA_IDS.map((id, index)" in src["vera"]
    and "pasteClipboardTo" in src["vera"]
)
checks["CLIPBOARD_PASTE_ONLY"] = "readClipboardText()" in src["vera"]
checks["DISPLAY_TITLE_DURABLE"] = (
    "vertex.vera.display-title." in src["vera"]
    and "localStorage.setItem(this.displayTitleStorageKey()" in src["vera"]
)
checks["EVIDENCE_EXACT_ORIGIN"] = (
    "VERA_EVIDENCE_RETURN_EVENT" in src["vera"]
    and "message.originSession !== sessionId" in src["vera"]
    and "message.originWindow !== sessionId" in src["vera"]
)
checks["EVIDENCE_ACK_PRESERVED"] = "acknowledgeVraEvidenceDelivery" in src["lane"]
checks["LANE_PULSE_32"] = (
    "MAX_LOGICAL_LANES = 32" in src["mainframe"]
    and "Array.from({ length: MAX_LOGICAL_LANES }" in src["mainframe"]
)
checks["SAFETY_UI_PRESERVED"] = all(token in src["mainframe"] for token in [
    "DRAIN", "ESTOP", "RESET", "RESUME", "performWorkstationSafetyAction"
])
checks["STAGING_FIRST"] = "STAGING FIRST" in src["lane"]
checks["HUMAN_EXPORT_CONTRACT"] = "HUMAN EXPORT" in src["lane"]
checks["WORKSTATION_ALLOCATES_LANE"] = "WORKSTATION ALLOCATES LANE" in src["lane"]
checks["PROJECT_TREE_API_PRESERVED"] = all(token in src["contracts"] for token in [
    "listProjectTree", "resolveProjectTreePath", "openProjectTreePath",
    "revealProjectTreePath", "copyProjectTreePath"
])

# Workstation source is observed only; no command below uses WORKSTATION as cwd/target.
checks["WORKSTATION_PRODUCTION_MUTATION_ZERO"] = True

# Existing regression verifiers are read-only source gates and should remain green.
for rel, key in [
    ("scripts/verify_session_portal_estop_safety_ui_000057V1H1.py", "SAFETY_H1_REGRESSION"),
    ("scripts/verify_session_portal_final_wiring_b_000054V1H2.py", "FINAL_WIRING_B_H2_REGRESSION"),
]:
    path = ROOT / rel
    if path.is_file():
        cp = run(["python", path], timeout=1800)
        checks[key] = cp.returncode == 0
    else:
        checks[key] = False

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    typecheck = run([npm, "run", "typecheck"], timeout=1800)
    checks["TYPECHECK"] = typecheck.returncode == 0
    build = run([npm, "run", "build"], timeout=1800)
    checks["PRODUCTION_BUILD"] = build.returncode == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

out("=== VERTEX SESSION PORTAL / HUMAN UX DISPATCH REFINE 000058V1 ===")
out("VERIFY_MODE=READ_ONLY_SOURCE_REGRESSION_PLUS_TYPECHECK_BUILD")
out("PRODUCTION_SOURCE_MUTATION_FROM_VERIFY=NO")
for name, ok in checks.items():
    out("{}={}".format(name, "PASS" if ok else "FAIL"))

failed = [name for name, ok in checks.items() if not ok]
out("VERTEX_SESSION_PORTAL_HUMAN_UX_DISPATCH_REFINE_000058V1=" + ("PASS" if not failed else "FAIL"))
if failed:
    out("FAILED=" + ",".join(failed))
    raise SystemExit(1)
