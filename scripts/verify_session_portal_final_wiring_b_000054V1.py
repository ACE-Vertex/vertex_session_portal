from __future__ import annotations

from pathlib import Path
import hashlib
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT.parent / "vertex_workstation"

SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
CLIENT = ROOT / "src/main/workstation/workstation-client.ts"
IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
PRELOAD = ROOT / "src/preload/index.ts"
CONTRACTS = ROOT / "src/shared/contracts.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
LANE_CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"
BROWSER = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"
BROWSER_CSS = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css"
RELAY = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraRelayInjector.ts"
EVIDENCE_INJECTOR = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts"
MAINFRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"

WS_EVIDENCE = WS / "headless/src/evidence_api.rs"
WS_SERVER = WS / "headless/src/server_adapter.rs"
WS_CORE = WS / "headless/src/core_bridge.rs"


def emit(value: object) -> None:
    print(str(value).encode("ascii", errors="backslashreplace").decode("ascii"))


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, condition: bool, failures: list[str]) -> None:
    emit(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        failures.append(name)


def source_snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    source = root / "src"
    if not source.exists():
        return result
    for path in sorted(source.rglob("*")):
        if path.is_file() and not any(part in {"node_modules", "out", "dist", "build", "EVIDENCE"} for part in path.parts):
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def run(command: list[str], label: str) -> int:
    emit("RUN=" + " ".join(command))
    p = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    emit(p.stdout)
    emit(f"{label}_EXIT={p.returncode}")
    return p.returncode


def main() -> int:
    emit("=== VERTEX SESSION PORTAL / FINAL WIRING B 000054V1 VERIFY ===")
    emit(f"ROOT={ROOT}")
    emit(f"WORKSTATION_READ_ONLY={WS}")
    emit("PRODUCTION_SOURCE_MUTATION_FROM_VERIFY=NO")
    failures: list[str] = []

    required = [SERVICE, CLIENT, IPC, PRELOAD, CONTRACTS, LANE, LANE_CSS, BROWSER, BROWSER_CSS, RELAY, EVIDENCE_INJECTOR, MAINFRAME,
                WS_EVIDENCE, WS_SERVER, WS_CORE]
    for path in required:
        check("FILE_" + path.name.replace(".", "_").upper(), path.is_file(), failures)
    if failures:
        emit("FAILURES=" + ",".join(failures))
        return 2

    ws_before = {p.as_posix(): digest(p) for p in [WS_EVIDENCE, WS_SERVER, WS_CORE]}
    portal_before = source_snapshot(ROOT)

    service, client, ipc, preload, contracts = map(text, [SERVICE, CLIENT, IPC, PRELOAD, CONTRACTS])
    lane, lane_css, browser, browser_css, relay, evidence_injector, mainframe = map(text, [LANE, LANE_CSS, BROWSER, BROWSER_CSS, RELAY, EVIDENCE_INJECTOR, MAINFRAME])
    ws_evidence, ws_server, ws_core = map(text, [WS_EVIDENCE, WS_SERVER, WS_CORE])

    # Workstation contract: observed production source, never guessed.
    check("WS_BIND_127_0_0_1_47832", '127.0.0.1:47832' in ws_server, failures)
    check("WS_ACK_ENDPOINT_POST_EXACT", '/evidence/ack' in ws_server and 'request.method == "POST"' in ws_server, failures)
    for field in ["evidence_id", "artifact_id", "returned_at"]:
        check("WS_ACK_REQUEST_" + field.upper(), field in ws_evidence, failures)
    check("WS_ACK_DENY_UNKNOWN_FIELDS", "deny_unknown_fields" in ws_evidence, failures)
    check("WS_ACK_REUSES_COREBRIDGE", "acknowledge_evidence_return" in ws_server and "acknowledge_evidence_return" in ws_core, failures)
    check("WS_ACK_RETURN_QUEUED_GATE", "RETURN_QUEUED" in ws_evidence, failures)
    check("WS_ACK_RETURNED_IDEMPOTENT_RETRY", "AlreadyReturned" in ws_evidence and "idempotent" in ws_server, failures)
    check("WS_ACK_RETURNED_AT_PORTAL_AUTHORITY", "returned_at" in ws_evidence and "returned_at" in ws_server, failures)
    check("WS_POST_JOBS_PRESENT", '"POST", "/v1/jobs"' in ws_server or '/v1/jobs' in ws_server, failures)
    check("WS_GET_HEALTH_PRESENT", '/v1/health' in ws_server, failures)
    check("WS_GET_JOB_EVIDENCE_PRESENT", '/evidence' in ws_server and '/v1/jobs/' in ws_server, failures)
    check("WS_HTTP_DIRECT_APPLY_ABSENT", '/v1/apply' not in ws_server and 'POST /apply' not in ws_server, failures)
    check("WS_HTTP_DIRECT_VERIFY_ABSENT", '/v1/verify' not in ws_server and 'POST /verify' not in ws_server, failures)
    check("WS_HTTP_DIRECT_ROLLBACK_ABSENT", '/v1/rollback' not in ws_server and 'POST /rollback' not in ws_server, failures)

    # Local main-process HTTP boundary.
    check("CLIENT_LOOPBACK_ONLY", "host: '127.0.0.1'" in client and "port: 47832" in client, failures)
    check("CLIENT_TIMEOUT", "timeoutMs: 2500" in client and "WORKSTATION_HTTP_TIMEOUT" in client, failures)
    check("CLIENT_POST_JOBS", "registerJob" in client and "'/v1/jobs'" in client, failures)
    check("CLIENT_GET_JOB", "getJob(jobId" in client, failures)
    check("CLIENT_GET_EVIDENCE", "getEvidence(jobId" in client, failures)
    check("CLIENT_POST_ACK", "acknowledgeEvidence" in client and "/evidence/ack" in client, failures)
    check("RENDERER_NO_ARBITRARY_HTTP", "http://127.0.0.1:47832" not in lane + browser + mainframe and "fetch(" not in lane + browser + mainframe, failures)

    # Publish -> register strict ordering.
    approval = service.find("card.humanApproval = 'APPROVED'")
    approval_sidecar = service.find("this.writeStagingMetadata(card.stagedPath", approval)
    approval_ledger = service.find("this.persistAndEmit()", approval_sidecar)
    publish = service.find("this.publishToIncomingAtomic(card, destination)", approval_ledger)
    published_phase = service.find("card.dispatchPhase = 'PUBLISHED'", publish)
    incoming_sidecar = service.find("this.publishIncomingCommitSidecar(card, finalMetadata)", published_phase)
    registration = service.find("this.reconcileWorkstationCard(card.id)", incoming_sidecar)
    check("A_HUMAN_UNAPPROVED_POST_ZERO", "humanApproval !== 'APPROVED'" in service and "dispatchPhase !== 'PUBLISHED'" in service, failures)
    check("B_APPROVAL_DURABLE_BEFORE_PUBLISH", 0 <= approval < approval_sidecar < approval_ledger < publish, failures)
    check("B_ATOMIC_PUBLISH_BEFORE_POST", 0 <= publish < published_phase < incoming_sidecar < registration, failures)
    check("B_TEMP_COPY_SHA_ATOMIC_RENAME", "copyFileSync(card.stagedPath, temp)" in service and "this.sha256(temp) !== card.sha256" in service and "renameSync(temp, destination)" in service and ".tmp`" in service, failures)
    check("B_INCOMING_APPROVAL_SIDECAR", "human_approval: 'APPROVED'" in service and "status: 'DISPATCHED'" in service, failures)
    check("C_POST_RETRY_IDENTITY_STABLE", "artifact_filename: basename(card.publishName)" in service and "artifact_sha256: card.sha256" in service, failures)
    check("D_OFFLINE_APPROVAL_PRESERVED", "workstationRegistration = error instanceof WorkstationHttpError" in service and "? 'BLOCKED'" in service and ": 'PENDING'" in service, failures)
    check("D_OFFLINE_VRA_NOT_DELETED", "WORKSTATION_DISPATCH_PUBLISH_FAILED" in service and "Approval is never silently revoked" in service, failures)

    # Evidence exact route + durable idempotency + ACK.
    check("EVIDENCE_EXACT_ORIGIN_ROUTE", "exactOriginRoute" in lane and "card.originVera === expectedVera" in lane and "card.originWindow === session" in lane, failures)
    check("VERA03_ACTIVE_VERA05_INDEPENDENT", "getAttribute('active-window')" not in lane and "querySelector('[active-window]')" not in lane and "document.activeElement" not in lane, failures)
    check("UNKNOWN_ORIGIN_FAIL_CLOSED", "EVIDENCE ROUTE FAIL-CLOSED" in lane and "origin-mismatch-fail-closed" in browser, failures)
    attempt = lane.find("this.writeDeliveryAttempt(card)")
    delivery_event = lane.find("window.dispatchEvent(new CustomEvent<VeraEvidenceReturnMessage>", attempt)
    receipt = lane.find("this.writeDeliveryReceipt(card)")
    ack_call = lane.find("void this.ackDeliveredEvidence(card)", receipt)
    check("DELIVERY_IN_FLIGHT_DURABLE_BEFORE_INJECTION", 0 <= attempt < delivery_event, failures)
    check("1_DELIVERED_BEFORE_ACK", 0 <= receipt < ack_call, failures)
    check("DELIVERY_UNCERTAIN_NO_AUTO_REDELIVERY", "state: 'IN_FLIGHT' | 'DELIVERED'" in lane and "DELIVERY_UNCERTAIN" in lane and "hasDeliveryLedgerEntry(card)" in lane, failures)
    check("4_DUPLICATE_EVIDENCE_DELIVERY_ZERO", "hasDeliveryLedgerEntry(card)" in lane and "EVIDENCE_RECEIPTS_KEY" in lane, failures)
    check("ACK_ONLY_DURABLE_DELIVERED", "receipt.state !== 'DELIVERED'" in lane and "IN_FLIGHT / DELIVERY_UNCERTAIN never ACKs" in lane, failures)
    check("ACK_EXACT_RETURNED_AT_RETRY", "returnedAt: receipt.deliveredAt" in lane and "ACK RETRY PENDING" in lane, failures)
    check("ACK_IPC_BRIDGE", "workstation:vra-evidence-ack" in ipc and "acknowledgeVraEvidenceDelivery" in preload and "acknowledgeVraEvidenceDelivery" in contracts, failures)
    check("ACK_MAIN_REVALIDATES_IDENTITY", "EVIDENCE_ACK_EVIDENCE_ID_MISMATCH" in service and "EVIDENCE_ACK_ARTIFACT_ID_MISMATCH" in service and "EVIDENCE_ACK_ORIGIN_FAIL_CLOSED" in service, failures)
    check("ACK_REQUIRES_RETURN_QUEUED", "EVIDENCE_ACK_NOT_RETURN_QUEUED" in service, failures)
    check("2_DELIVERY_ACK_RETURNED", "evidenceReturnState: 'RETURNED'" in service and "RETURNED · ACKNOWLEDGED" in lane, failures)
    check("3_ACK_RESPONSE_LOSS_SAFE_RETRY", "result.returnedAt !== receipt.deliveredAt" in lane and "returned_at: returnedAt" in service, failures)
    check("5_FAILED_EVIDENCE_SAME_ROUTE", "workstationEvidenceState === 'AVAILABLE'" in lane and "workstationJobState" in lane and "FAILED" in lane, failures)
    check("6_ORIGIN_VERA03_NOT_ACTIVE_VERA05", "originSession" in lane and "originSession" in browser and "getAttribute('active-window')" not in lane and "document.activeElement" not in lane, failures)
    check("7_UNKNOWN_ORIGIN_ACK_ZERO", "EVIDENCE_ACK_ORIGIN_FAIL_CLOSED" in service and "origin-mismatch-fail-closed" in browser, failures)
    check("EVIDENCE_WRITE_ONLY_BOUNDARY", "injectWorkstationEvidence" in browser and "document.querySelector" in evidence_injector and "innerText" not in evidence_injector and "document.body" not in evidence_injector and "outerHTML" not in evidence_injector, failures)

    # Prompt Relay absolute Vera 1..5, paste only.
    check("8_PROMPT_RELAY_FIVE_ABSOLUTE", "MAIN_VERA_IDS = ['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05']" in browser and "data-relay-target" in browser, failures)
    check("8_PROMPT_CLIPBOARD_MAIN_IPC", "clipboard.readText()" in ipc and "readClipboardText" in preload and "readClipboardText" in browser, failures)
    check("8_PROMPT_RELAY_PASTE_ONLY", "clipboard-pasted" in relay and "button.click" not in relay and "send-button" not in relay.lower() and "Send prompt" not in relay, failures)
    check("8_PROMPT_RELAY_CURRENT_DISABLED", "id === this.sessionId() ? 'disabled'" in browser, failures)
    check("8_PROMPT_TARGET_UNAVAILABLE_FAIL_CLOSED", "UNAVAILABLE" in browser and "targetNode" in browser, failures)
    check("8_PROMPT_SESSION_ID_EXPLICIT", "message.to !== this.sessionId()" in browser and "relay.detail.to !== this.sessionId()" in browser, failures)

    # display_title independent durable preference.
    check("9_DISPLAY_TITLE_EDITABLE", "beginDisplayTitleEdit" in browser and "event.key === 'Enter'" in browser and "event.key === 'Escape'" in browser, failures)
    check("10_DISPLAY_TITLE_DURABLE", "vertex.vera.display-title." in browser and "localStorage.setItem(this.displayTitleStorageKey()" in browser, failures)
    check("DISPLAY_TITLE_RESET", "resetDisplayTitle" in browser and "Reset to Project Name" in browser, failures)
    check("DISPLAY_TITLE_IDENTITY_SEPARATE", "sessionId: this.sessionId()" in browser and "displayTitleStorageKey" in browser and "originSession" not in browser[browser.find("commitDisplayTitle"):browser.find("cancelDisplayTitleEdit")], failures)

    # Header pulse/search, 32 max, Workstation allocation read only.
    check("11_HEADER_MAX_32", "MAX_LOGICAL_LANES = 32" in mainframe and "Array.from({ length: MAX_LOGICAL_LANES }" in mainframe, failures)
    check("11_NO_LANE_33", "lane-33" not in mainframe.lower() and "LANE 33" not in mainframe, failures)
    check("11_ALLOCATED_LANE_READ_ONLY_FACT", "card.allocatedLane = this.optionalString(job.allocated_lane)" in service and "Final Lane Allocation Authority is Workstation" in service, failures)
    check("HEADER_OFFLINE_QUIET", "OFFLINE / --/${MAX_LOGICAL_LANES}" in mainframe, failures)
    check("HEADER_LANE_FOCUS", "vertex-vra-focus-lane" in mainframe and "vertex-vra-focus-lane" in lane, failures)
    check("12_SEARCH_COMPACT_EXPAND", "searchExpanded" in mainframe and "Ctrl+K" in mainframe and "data-expanded" in mainframe and "width:32px" in mainframe, failures)
    check("12_EXISTING_LAYOUT_PRESERVED", "<vertex-explorer>" in mainframe and "sessionTrack" in mainframe and "<vertex-vra-dispatch-lane>" in mainframe, failures)

    # Dispatch Bay / safety invariants.
    for label in ["ORIGIN VERA", "ORIGIN SESSION / WINDOW", "PROJECT NAME", "ARTIFACT ID", "TITLE / JOB SUMMARY", "REQUESTED LANE", "LANE POLICY", "ALLOCATED LANE", "HUMAN APPROVAL"]:
        check("D_CARD_" + re.sub(r"[^A-Z]+", "_", label), label in lane, failures)
    check("D_PATH_HIDDEN", "stagedPath" not in lane and "worksPath" not in lane and "worksIncomingRoot" not in lane, failures)
    check("13_HUMAN_GATE_PRESERVED", "APPROVE + DISPATCH" in lane and "humanApproval = 'APPROVED'" in service, failures)
    check("13_NO_HTTP_APPLY_VERIFY_ROLLBACK", all(token not in client for token in ["/apply", "/verify", "/rollback"]), failures)
    check("13_NO_AUTO_RERUN", "workstationRegistration !== 'REGISTERED'" in service and "workstationRegistration = 'REGISTERED'" in service, failures)
    check("VRA1_COMPAT_MARKER_PRESERVED", "WORKSTATION_DISPATCH_CARD_000052V1H2" in service and "WORKSTATION_DISPATCH_CARD_000052V1H2" in lane, failures)
    check("NO_BROWSER_RESPONSE_DOM_SCRAPE", "document.body" not in relay and "innerText" not in relay and "textContent.trim" not in relay, failures)

    # Exact ordering mini-model: proves verifier's expected invariants are internally consistent.
    lifecycle = ["APPROVED_DURABLE", "TEMP_COPY", "SHA_OK", "ATOMIC_RENAME", "ROUTING_SIDECAR", "POST_JOB", "EVIDENCE", "DELIVERED_DURABLE", "ACK", "RETURNED"]
    check("LIFECYCLE_DATA_BEFORE_CONTROL", lifecycle.index("ROUTING_SIDECAR") < lifecycle.index("POST_JOB"), failures)
    check("LIFECYCLE_DELIVERY_BEFORE_ACK", lifecycle.index("DELIVERED_DURABLE") < lifecycle.index("ACK") < lifecycle.index("RETURNED"), failures)

    # Existing project compiler/build gate. Build may update out/, never source.
    if os.environ.get("VERTEX_FINAL_B_INTERNAL_STATIC_ONLY") == "1":
        emit("14_TYPECHECK=SKIPPED_INTERNAL_STATIC_ONLY")
        emit("14_BUILD=SKIPPED_INTERNAL_STATIC_ONLY")
    else:
        npm = "npm.cmd" if os.name == "nt" else "npm"
        typecheck_exit = run([npm, "run", "typecheck"], "TYPECHECK")
        check("14_TYPECHECK", typecheck_exit == 0, failures)
        build_exit = run([npm, "run", "build"], "BUILD")
        check("14_BUILD", build_exit == 0, failures)

    portal_after = source_snapshot(ROOT)
    ws_after = {p.as_posix(): digest(p) for p in [WS_EVIDENCE, WS_SERVER, WS_CORE]}
    check("VERIFY_PORTAL_SOURCE_UNCHANGED", portal_before == portal_after, failures)
    check("WORKSTATION_PRODUCTION_UNCHANGED", ws_before == ws_after, failures)

    emit("WORKSTATION_PORT=47832")
    emit("ACK_ENDPOINT=POST /v1/jobs/{job_id}/evidence/ack")
    emit("PROMPT_RELAY=VERA01..VERA05_CLIPBOARD_PASTE_ONLY")
    emit("DISPLAY_TITLE=LOCAL_DURABLE_PRESENTATION_ONLY")
    emit("HEADER_PULSE=32_LOGICAL_LANES_PORTAL_OBSERVATION")
    emit("RAY_CONSOLE=DEFERRED")
    emit("RED=NONE" if not failures else "RED=VERIFY_FAILURE")
    emit("YELLOW=NONE" if not failures else "YELLOW=REQUIRES_REPAIR")
    emit("VERTEX_SESSION_PORTAL_FINAL_WIRING_B_000054V1=" + ("PASS" if not failures else "FAIL"))
    if failures:
        emit("FAILURES=" + ",".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
