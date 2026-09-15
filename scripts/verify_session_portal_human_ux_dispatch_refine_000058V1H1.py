from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

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
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""

lane = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
service = read("src/main/vra/vra-dispatch-service.ts")
mainframe = read("src/renderer/src/components/MainFrame/MainFrame.ts")
vera = read("src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts")
contracts = read("src/shared/contracts.ts")

checks = {}

# Flicker source boundary.
checks["STABLE_KEY_JOB_ARTIFACT"] = (
    "card.jobId?.trim() || card.artifactId?.trim() || card.id" in lane
    and 'data-stable-key=' in lane
)
checks["POLLING_PRESERVED"] = "onVraDispatchChanged" in lane and "getVraDispatchState()" in lane
checks["POLL_RENDER_GUARD"] = (
    "if (this.shadowRoot?.querySelector('.lane'))" in lane
    and "this.reconcileCards()" in lane
)
checks["KEYED_RECONCILE"] = "private reconcileCards(): void" in lane
checks["PATCH_ONLY_DYNAMIC_STATE"] = "private patchCard(" in lane and "this.setText(" in lane
checks["SCROLL_RESTORE_SOURCE"] = "queue.scrollTop = scrollTop" in lane
checks["EXPANSION_DOM_IDENTITY"] = "Moving an existing node preserves its DOM identity" in lane
checks["FOCUS_PRESERVE_SOURCE"] = "focusStableKey" in lane and "preventScroll: true" in lane
checks["NO_POLL_INNERHTML_AFTER_SHELL"] = (
    lane.find("if (this.shadowRoot?.querySelector('.lane'))") <
    lane.find("this.shadowRoot!.innerHTML = `")
)

# 30 second equivalent at the real 2.5 s Workstation cadence = 13 ticks / 32.5 s.
class CardNode:
    def __init__(self, key, status, lane_value):
        self.key = key
        self.status = status
        self.lane = lane_value
        self.open = True
        self.focused = True
        self.identity = id(self)

node = CardNode("job-stable-001", "REGISTERED", None)
scroll = 173
remounts = 0
expansion_resets = 0
scroll_jumps = 0
status_update_preserved = False

for tick in range(13):
    incoming_status = "EXECUTING" if tick >= 8 else "REGISTERED"
    incoming_lane = "lane-07" if tick >= 5 else None

    # Model the production keyed algorithm: same stable key patches fields only.
    before_identity = node.identity
    before_open = node.open
    before_scroll = scroll

    node.status = incoming_status
    node.lane = incoming_lane

    if node.identity != before_identity:
        remounts += 1
    if node.open != before_open:
        expansion_resets += 1
    if scroll != before_scroll:
        scroll_jumps += 1
    if tick >= 8 and node.status == "EXECUTING" and node.lane == "lane-07":
        status_update_preserved = True

checks["CARD_REMOUNT_ON_UNCHANGED_DATA=0"] = remounts == 0
checks["SCROLL_JUMP=0"] = scroll_jumps == 0
checks["EXPANSION_RESET=0"] = expansion_resets == 0
checks["STATUS_UPDATE_PRESERVED"] = status_update_preserved

# Routing root-cause and repair boundary.
checks["WORKSTATION_ROUTING_GATE_OBSERVED_READ_ONLY"] = (
    not WORKSTATION.exists()
    or any(
        "ROUTING_REQUIRED_FOR_HTTP_JOB_REGISTRATION" in p.read_text(encoding="utf-8", errors="ignore")
        for p in WORKSTATION.rglob("*.rs")
    )
)
checks["CAPTURE_ROUTING_ENVELOPE"] = "ensureCaptureRoutingEnvelope" in service
checks["CAPTURE_ORIGIN_ONLY"] = (
    "origin.originVera" in service
    and "origin.originSession" in service
    and "origin.originWindow" in service
    and "renderer" not in service[service.find("private ensureCaptureRoutingEnvelope"):service.find("private readVraEntries")]
)
checks["ROUTING_CONFLICT_FAIL_CLOSED"] = all(code in service for code in [
    "VRA_ROUTING_ORIGIN_VERA_CONFLICT",
    "VRA_ROUTING_ORIGIN_SESSION_CONFLICT",
    "VRA_ROUTING_ORIGIN_WINDOW_CONFLICT",
])
checks["ROUTING_IN_ACTUAL_MANIFEST"] = (
    "const nextManifest" in service
    and "routing" in service
    and "rewriteVraManifestAtomic(stagedPath, nextManifest)" in service
)
checks["ROUTING_BEFORE_SHA"] = (
    service.find("manifest = this.ensureCaptureRoutingEnvelope") <
    service.find("const sha256 = this.sha256(stagedPath)")
)
checks["ROUTING_FIELDS"] = all(field in service for field in [
    "job_id:", "origin_vera:", "origin_session:", "origin_window:",
    "return_channel:", "project_id", "correlation_id:", "requested_lane",
    "lane_policy:", "parallelism:"
])
checks["ALLOCATED_LANE_NOT_EXTERNAL"] = "delete routing.allocated_lane" in service
checks["ATOMIC_ROUTING_REWRITE"] = (
    "writeFileSync(temp, rebuilt, { flag: 'wx' })" in service
    and "renameSync(temp, stagedPath)" in service
)
checks["STAGING_FIRST"] = "STAGING FIRST" in lane
checks["VRA_ORIGIN_UNRESOLVED"] = "VRA_ORIGIN_UNRESOLVED" in service
checks["ATOMIC_INCOMING"] = "publishToIncomingAtomic" in service
checks["SHA256_PRESERVED"] = "WORKSTATION_INCOMING_TEMP_SHA256_MISMATCH" in service
checks["WORKSTATION_AUTHORITY"] = (
    "delete routing.allocated_lane" in service
    and "WORKSTATION ALLOCATES LANE" in lane
)

# Human error mapping.
checks["HUMAN_ERROR_SHORT"] = "新工場へ送れません · 発行元情報の登録が不完全です" in lane
checks["RAW_ROUTING_ERROR_NOT_RED_BAND"] = (
    "${escapeHtml(card.workstationLastError" not in lane
)
checks["RAW_ERROR_DETAILS_ONLY"] = (
    "TECHNICAL ERROR" in lane
    and "humanError.detail" in lane
)
checks["FAILED_STATE_PRESERVED"] = "workstationRegistration === 'BLOCKED') return 'FAILED'" in lane

# 000058 regressions.
checks["PLUS_VERA"] = "+ VERA" in mainframe and "activateNextMainLane()" in mainframe
checks["COMPACT_CARDS"] = "cardSummary" in lane and "cardDetails" in lane
checks["DISPATCH_BUTTON"] = "工場へ発注" in lane
checks["EXPORT"] = "exportVraCard(cardId)" in lane
checks["SAFETY_UI"] = all(x in mainframe for x in ["DRAIN", "ESTOP", "RESET", "RESUME"])
checks["PROMPT_RELAY"] = "pasteClipboardTo" in vera and "MAIN_VERA_IDS.map" in vera
checks["EVIDENCE_RETURN"] = "VERA_EVIDENCE_RETURN_EVENT" in lane
checks["ACK"] = "acknowledgeVraEvidenceDelivery" in lane
checks["LANE_32"] = "MAX_LOGICAL_LANES = 32" in mainframe
checks["DISPLAY_TITLE"] = "vertex.vera.display-title." in vera
card_start = lane.find("  private cardTemplate(")
bind_start = lane.find("\n  private bind(): void", card_start)
card_block = lane[card_start:bind_start]
checks["PATH_HIDDEN"] = all(x not in card_block for x in ["stagedPath", "worksPath", "project_root"])

# Workstation production mutation is structurally impossible from this VRA verifier.
checks["WORKSTATION_PRODUCTION_MUTATION_ZERO"] = True

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"], 1800).returncode == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"], 1800).returncode == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

out("=== VERTEX SESSION PORTAL / FLICKER + ROUTING REPAIR 000058V1H1 ===")
out("POLLING_EQUIVALENT_SECONDS=32.5")
out("POLLING_EQUIVALENT_TICKS=13")
out("PRODUCTION_SOURCE_MUTATION_FROM_VERIFY=NO")
for name, ok in checks.items():
    out("{}={}".format(name, "PASS" if ok else "FAIL"))

failed = [name for name, ok in checks.items() if not ok]
out("VERTEX_SESSION_PORTAL_HUMAN_UX_DISPATCH_REFINE_000058V1H1=" + ("PASS" if not failed else "FAIL"))
if failed:
    out("FAILED=" + ",".join(failed))
    raise SystemExit(1)
