from pathlib import Path
import hashlib
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ROOT.parent / "vertex_workstation"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"
BROWSER = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"
MAINFRAME = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
CONTRACTS = ROOT / "src/shared/contracts.ts"
PRELOAD = ROOT / "src/preload/index.ts"
IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
SCALER = ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.ts"
MARKER = "WORKSTATION_DISPATCH_CARD_000052V1H2"


def safe_emit(text: str) -> None:
    data = str(text).encode("ascii", errors="backslashreplace").decode("ascii")
    print(data)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, ok: bool, failures: list[str]) -> None:
    safe_emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)


def source_snapshot() -> dict[str, str]:
    roots = [ROOT / "src", ROOT / "package.json", ROOT / "tsconfig.json", ROOT / "tsconfig.node.json", ROOT / "tsconfig.web.json"]
    result: dict[str, str] = {}
    for item in roots:
        if item.is_file():
            result[item.relative_to(ROOT).as_posix()] = sha(item)
        elif item.is_dir():
            for path in sorted(item.rglob("*")):
                if path.is_file() and not any(part in {"node_modules", "out", "dist", "build", "EVIDENCE"} for part in path.parts):
                    result[path.relative_to(ROOT).as_posix()] = sha(path)
    return result


def run_typecheck() -> int:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    safe_emit(f"RUN={npm} run typecheck")
    completed = subprocess.run(
        [npm, "run", "typecheck"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    safe_emit(completed.stdout)
    safe_emit(f"TYPECHECK_EXIT={completed.returncode}")
    return completed.returncode


def mask_ts_comments(text: str, *, mask_strings: bool = False) -> str:
    """Mask comments while preserving offsets/newlines; optionally mask string bodies too."""
    out: list[str] = []
    i = 0
    mode = "code"
    quote = ""
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if mode == "code":
            if ch == "/" and nxt == "/":
                out.extend((" ", " "))
                i += 2
                mode = "line_comment"
                continue
            if ch == "/" and nxt == "*":
                out.extend((" ", " "))
                i += 2
                mode = "block_comment"
                continue
            if ch in {"'", '\"', "`"}:
                quote = ch
                out.append(" " if mask_strings else ch)
                i += 1
                mode = "string"
                continue
            out.append(ch)
            i += 1
            continue

        if mode == "line_comment":
            if ch == "\n":
                out.append("\n")
                mode = "code"
            else:
                out.append(" ")
            i += 1
            continue

        if mode == "block_comment":
            if ch == "*" and nxt == "/":
                out.extend((" ", " "))
                i += 2
                mode = "code"
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
            continue

        # string mode
        if ch == "\\" and i + 1 < len(text):
            out.append(" " if mask_strings else ch)
            out.append(" " if mask_strings else text[i + 1])
            i += 2
            continue
        out.append(" " if mask_strings and ch != "\n" else ch)
        i += 1
        if ch == quote:
            mode = "code"
            quote = ""

    return "".join(out)


def has_will_download_registration(text: str) -> bool:
    code = mask_ts_comments(text, mask_strings=False)
    return re.search(r"\.(?:on|once|addListener)\s*\(\s*(['\"])will-download\1", code) is not None


def has_set_save_path_call(text: str) -> bool:
    code = mask_ts_comments(text, mask_strings=True)
    return re.search(r"\.\s*setSavePath\s*\(", code) is not None


def owner_scan(kind: str) -> list[str]:
    owners: list[str] = []
    source_root = ROOT / "src"
    for path in source_root.rglob("*.ts"):
        try:
            text = read(path)
        except Exception:
            continue
        owns = has_will_download_registration(text) if kind == "will-download" else has_set_save_path_call(text)
        if owns:
            owners.append(path.relative_to(ROOT).as_posix())
    return sorted(owners)


def main() -> int:
    safe_emit("=== VERTEX SESSION PORTAL / WORKSTATION DISPATCH CARD VERIFY 000052V1H3 ===")
    safe_emit(f"ROOT={ROOT}")
    safe_emit("VERIFY_MODE=READ_ONLY_SOURCE_CHECK_PLUS_TSC_NO_EMIT")
    safe_emit("PRODUCTION_MUTATION_FROM_VERIFY=NO")

    failures: list[str] = []
    check("TARGET_SESSION_PORTAL_ONLY", ROOT.name == "vertex_session_portal", failures)
    check("VERTEX_WORKSTATION_NOT_TARGET", ROOT.resolve() != FORBIDDEN.resolve(), failures)

    required = [SERVICE, LANE, CSS, BROWSER, MAINFRAME, CONTRACTS, PRELOAD, IPC, SCALER]
    for path in required:
        check("FILE_" + path.name.replace(".", "_").upper(), path.is_file(), failures)
    if failures:
        safe_emit("FAILURES=" + ",".join(failures))
        return 2

    before = source_snapshot()
    service = read(SERVICE)
    lane = read(LANE)
    css = read(CSS)
    browser = read(BROWSER)
    mainframe = read(MAINFRAME)
    contracts = read(CONTRACTS)
    preload = read(PRELOAD)
    ipc = read(IPC)
    scaler = read(SCALER)

    check("H2_SERVICE_MARKER", MARKER in service, failures)
    check("H2_RENDERER_MARKER", MARKER in lane, failures)
    check("H2_CSS_MARKER", MARKER in css, failures)

    # P1: real VeraBrowserSession -> source map -> immutable Capture origin.
    check(
        "BROWSER_REAL_SESSION_ID_REGISTRATION",
        "sessionId: this.sessionId()" in browser and "getWebContentsId()" in browser,
        failures,
    )
    check(
        "SOURCE_MAP_IS_CAPTURE_AUTHORITY",
        "webviewSources = new Map<number, string>()" in service
        and "registerWebviewSource(" in service
        and "private sourceFor(webContents: WebContents)" in service,
        failures,
    )
    unresolved_at = service.find("console.warn('VRA_ORIGIN_UNRESOLVED')")
    capture_id_at = service.find("const captureId = randomUUID()")
    save_path_at = service.find("item.setSavePath(stagedPath)")
    check(
        "NEW_CAPTURE_ORIGIN_FAIL_CLOSED_BEFORE_STAGING",
        unresolved_at >= 0 and capture_id_at > unresolved_at and save_path_at > capture_id_at,
        failures,
    )
    check("ORIGIN_UNRESOLVED_CANCELS_DOWNLOAD", "if (!origin)" in service and "item.cancel()" in service, failures)
    check("NO_UNKNOWN_NEW_CAPTURE_STAGING", "private captureOrigin(webContents: WebContents): ImmutableVraOrigin | null" in service, failures)
    check("IMMUTABLE_CAPTURE_ORIGIN", "return Object.freeze({" in service, failures)
    check("NO_ACTIVE_WINDOW_ORIGIN_INFERENCE", "active-window" not in service.lower() and "active-window" not in lane.lower(), failures)
    check("RENDERER_NO_SOURCE_SESSION_INFERENCE", "sourceSessionId" not in lane and "laneLabel(" not in lane, failures)
    check(
        "LEGACY_SOURCE_SESSION_MIGRATION_ONLY",
        "allowLegacySourceSessionId" in service
        and "New Capture is never allowed to use this fallback" in service,
        failures,
    )

    for session_id, vera in [("vera-01", "VERA01"), ("vera-02", "VERA02"), ("vera-03", "VERA03"), ("vera-04", "VERA04"), ("vera-05", "VERA05")]:
        check(f"ORIGIN_MAP_{vera}", f"case '{session_id}': return '{vera}'" in service, failures)

    # VERA3 H2 canonical vra-routing/1 vocabulary.
    check("ROUTING_CONTRACT_V1", "VRA_ROUTING_CONTRACT_VERSION = 'vra-routing/1'" in service, failures)
    for field in [
        "job_id", "origin_vera", "origin_session", "origin_window", "return_channel",
        "project_id", "project_name", "requested_lane", "lane_policy", "parallelism",
        "worker_concurrency", "correlation_id", "allocated_lane"
    ]:
        check("DURABLE_" + field.upper(), field in service, failures)
    check("REQUESTED_LANE_CANONICAL", "routing.requested_lane" in service and "routing.lane_hint" in service, failures)
    check("PREFERRED_LANE_RETIRED", "preferred_lane" not in service, failures)
    check("LANE_POLICY_ANY_PREFER_ONLY", "normalized === 'ANY' || normalized === 'PREFER'" in service and "VRA_EXTERNAL_LANE_POLICY_UNSUPPORTED" in service, failures)
    check("PREFER_REQUIRES_REQUEST", "VRA_ROUTING_REQUESTED_LANE_REQUIRED_FOR_PREFER" in service, failures)
    check("PARALLELISM_MAX_32", "MAX_LANE_PARALLELISM = 32" in service and "numeric <= MAX_LANE_PARALLELISM" in service, failures)
    check("WORKER_CONCURRENCY_SEPARATE", "normalizeWorkerConcurrency" in service and "workerConcurrency" in service, failures)
    check("ALLOCATED_LANE_CAPTURE_NULL", "allocatedLane: null" in service, failures)
    check("WORKSTATION_ALLOCATION_AUTHORITY", "Final Lane Allocation Authority is Workstation" in service, failures)

    # P2 durable sidecar and restart/process-kill safety.
    check("SIDECAR_DURABLE", ".meta.json" in service and "writeJsonAtomic" in service, failures)
    check("LEDGER_ATOMIC", "this.writeJsonAtomic(this.ledgerPath, ledger)" in service, failures)
    check("SIDECAR_ATOMIC_RENAME", "renameSync(temp, path)" in service, failures)
    check("DISPATCH_PHASE_APPROVED", "dispatchPhase = 'APPROVED'" in service, failures)
    check("DISPATCH_PHASE_PUBLISHED", "dispatchPhase = 'PUBLISHED'" in service, failures)
    check("APPROVED_PUBLICATION_RECONCILE", "reconcileApprovedPublication" in service and "process kill after atomic rename" in service, failures)
    check("REMOVE_TOMBSTONE_FIRST", "Tombstone first" in service and "status: 'REMOVED'" in service, failures)

    # P3 Human Approval -> temp copy -> SHA -> atomic rename -> final sidecar.
    approval_at = service.find("card.humanApproval = 'APPROVED'")
    approval_sidecar_at = service.find("this.writeStagingMetadata(card.stagedPath", approval_at)
    approval_ledger_at = service.find("this.persistAndEmit()", approval_sidecar_at)
    publish_call_at = service.find("this.publishToIncomingAtomic(card, destination)", approval_ledger_at)
    final_phase_at = service.find("card.dispatchPhase = 'PUBLISHED'", publish_call_at)
    final_sidecar_at = service.find("this.writeStagingMetadata(card.stagedPath", final_phase_at)
    check(
        "HUMAN_APPROVAL_DURABLE_BEFORE_PUBLISH",
        approval_at >= 0 < approval_sidecar_at < approval_ledger_at < publish_call_at,
        failures,
    )
    check("FINAL_SIDECAR_AFTER_ATOMIC_PUBLISH", publish_call_at >= 0 < final_phase_at < final_sidecar_at, failures)

    publish_start = service.find("private publishToIncomingAtomic")
    publish_end = service.find("private reconcileApprovedPublication", publish_start)
    publish_block = service[publish_start:publish_end]
    temp_copy_at = publish_block.find("copyFileSync(card.stagedPath, temp)")
    temp_sha_at = publish_block.find("this.sha256(temp) !== card.sha256")
    rename_at = publish_block.find("renameSync(temp, destination)")
    check("INCOMING_TEMP_COPY_FIRST", temp_copy_at >= 0, failures)
    check("INCOMING_TEMP_SHA_BEFORE_RENAME", temp_copy_at >= 0 < temp_sha_at < rename_at, failures)
    check("INCOMING_ATOMIC_RENAME", rename_at >= 0, failures)
    check("NO_DIRECT_FINAL_VRA_COPY", "copyFileSync(card.stagedPath, destination)" not in publish_block, failures)
    check("TEMP_NOT_VRA_SUFFIX", ".tmp`" in publish_block and "renameSync(temp, destination)" in publish_block, failures)
    check("HTTP_POST_V1_JOBS_NOT_IMPLEMENTED", "POST /v1/jobs intentionally remains" in service and "fetch(" not in service and "/v1/jobs'" not in service, failures)

    # Human gate / staging-first / export / capture ownership safety.
    check("STAGING_FIRST_PRESERVED", "STAGING FIRST" in service and "item.setSavePath(stagedPath)" in service, failures)
    check("HUMAN_EXPORT_PRESERVED", "exportCard(cardId: string)" in service and 'data-action="export"' in lane, failures)
    check("SHA256_GATE_PRESERVED", "STAGED_VRA_SHA256_MISMATCH" in service, failures)
    check("HUMAN_APPROVAL_PENDING_AT_CAPTURE", "humanApproval: 'PENDING'" in service, failures)
    check("HUMAN_GATE_UI", "APPROVE + DISPATCH" in lane and "HUMAN GATE · NO AUTO APPLY" in lane, failures)
    check("NO_AUTO_DISPATCH_TIMER", "setInterval" not in lane and "setTimeout" not in lane, failures)
    check("NO_AUTO_APPLY", "autoApply" not in service and "autoApply" not in lane, failures)

    will_owners = owner_scan("will-download")
    save_owners = owner_scan("setSavePath")
    safe_emit("WILL_DOWNLOAD_OWNERS=" + ";".join(will_owners))
    safe_emit("SET_SAVE_PATH_OWNERS=" + ";".join(save_owners))
    policy_path = ROOT / "src/main/vra/vra-download-destination-policy.ts"
    policy_text = read(policy_path) if policy_path.is_file() else ""
    safe_emit(f"DESTINATION_POLICY_RAW_WILL_DOWNLOAD_TOKEN={'YES' if 'will-download' in policy_text else 'NO'}")
    safe_emit(f"DESTINATION_POLICY_RAW_SET_SAVE_PATH_TOKEN={'YES' if 'setSavePath' in policy_text else 'NO'}")
    check("DESTINATION_POLICY_NOT_CAPTURE_OWNER", not has_will_download_registration(policy_text), failures)
    check("DESTINATION_POLICY_NOT_SAVE_OWNER", not has_set_save_path_call(policy_text), failures)
    check("CAPTURE_OWNER_SINGLE", will_owners == ["src/main/vra/vra-dispatch-service.ts"], failures)
    check("VRA_SAVE_OWNER_SINGLE", save_owners == ["src/main/vra/vra-dispatch-service.ts"], failures)

    # Card UI: provenance/routing facts only; no filesystem Path surface.
    for forbidden in ["stagedPath", "worksPath", "worksIncomingRoot"]:
        check("HUMAN_CARD_NO_" + forbidden.upper(), forbidden not in lane, failures)
    check("WORKS_RECEIVING_PATH_UI_RETIRED", "WORKS RECEIVING BAY" not in lane, failures)
    for label in [
        "ORIGIN VERA", "ORIGIN SESSION / WINDOW", "PROJECT NAME", "ARTIFACT ID",
        "TITLE / JOB SUMMARY", "REQUESTED LANE", "LANE POLICY", "HUMAN APPROVAL"
    ]:
        check("CARD_" + re.sub(r"[^A-Z0-9]+", "_", label).strip("_"), label in lane, failures)
    check("CARD_ALLOCATED_LANE_OPTIONAL", "allocatedLane ? this.field('ALLOCATED LANE · WORKSTATION'" in lane, failures)
    check("VERA05_INTEGRATION_SEAT", "INTEGRATION · VERA05" in lane, failures)
    check("ROUTING_V1_UI_CONTRACT", "VRA-ROUTING/1" in lane, failures)
    check("ORIGIN_FAIL_CLOSED_UI_CONTRACT", "ORIGIN FAIL-CLOSED" in lane, failures)
    check("ATOMIC_INCOMING_UI_CONTRACT", "ATOMIC _INCOMING" in lane, failures)

    # Existing VERA 1-5 layout and bridges are preserved, not replaced by H2.
    check("MAINFRAME_DISPATCH_LANE_MOUNT", "<vertex-vra-dispatch-lane" in mainframe, failures)
    check("SCALER_DEFAULT_THREE", "const MIN_COUNT = 3" in scaler, failures)
    check("SCALER_MAX_FIVE", "const MAX_COUNT = 5" in scaler, failures)
    check("SCALER_VERA04", "'vera-04'" in scaler, failures)
    check("SCALER_VERA05", "'vera-05'" in scaler, failures)
    check("PRELOAD_DISPATCH_BRIDGE", "workstation:vra-dispatch-card" in preload, failures)
    check("IPC_DISPATCH_BRIDGE", "workstation:vra-dispatch-card" in ipc, failures)
    check("IPC_EXPORT_BRIDGE", "workstation:vra-export-card" in ipc, failures)
    check("HUMAN_APPLY_CONTRACT", "applyAuthority: 'HUMAN_APPLY'" in contracts, failures)
    check("HUMAN_DISPATCH_CONTRACT", "dispatchAuthority: 'HUMAN'" in contracts, failures)
    check("NO_BROWSER_DOM_SCRAPE", "executeJavaScript" not in browser and "executeJavaScript" not in service and "executeJavaScript" not in lane, failures)

    if failures:
        safe_emit("STATIC_FAILURES=" + ",".join(failures))
        return 3

    check("TSC_NO_EMIT_TYPECHECK", run_typecheck() == 0, failures)
    after = source_snapshot()
    check("VERIFY_SOURCE_HASHES_UNCHANGED", before == after, failures)

    if failures:
        safe_emit("FAILURES=" + ",".join(failures))
        return 4

    safe_emit("APPLY_MECHANISM=VRA_COPY_OPERATIONS_ONLY")
    safe_emit("VERIFY_MUTATES_PRODUCTION_SOURCE=NO")
    safe_emit("HTTP_POST_V1_JOBS=DEFERRED_TO_FINAL_INTEGRATION")
    safe_emit("VERTEX_WORKSTATION_MUTATION=NO")
    safe_emit("HUMAN_GATE=PRESERVED")
    safe_emit("VERTEX_SESSION_PORTAL_WORKSTATION_DISPATCH_CARD_000052V1H3=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
