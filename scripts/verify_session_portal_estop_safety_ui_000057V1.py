from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WS_ROOT = ROOT.parent / "vertex_workstation"
PARENT_FINAL_B = ROOT / "scripts" / "verify_session_portal_final_wiring_b_000054V1H2.py"
WS_RAY = WS_ROOT / "scripts" / "ray_workstation_durable_estop_control_000056V2.py"

CLIENT = ROOT / "src" / "main" / "workstation" / "workstation-client.ts"
SERVICE = ROOT / "src" / "main" / "vra" / "vra-dispatch-service.ts"
IPC = ROOT / "src" / "main" / "ipc" / "register-vra-dispatch-ipc.ts"
PRELOAD = ROOT / "src" / "preload" / "index.ts"
CONTRACTS = ROOT / "src" / "shared" / "contracts.ts"
MAIN = ROOT / "src" / "renderer" / "src" / "components" / "MainFrame" / "MainFrame.ts"
DISPATCH = ROOT / "src" / "renderer" / "src" / "components" / "VraDispatchLane" / "VraDispatchLane.ts"

WS_SAFETY = WS_ROOT / "headless" / "src" / "safety_state.rs"
WS_SERVER = WS_ROOT / "headless" / "src" / "server_adapter.rs"
WS_CORE = WS_ROOT / "headless" / "src" / "core_bridge.rs"
WS_FILES = [WS_SAFETY, WS_SERVER, WS_CORE]


def emit(value: object) -> None:
    print(str(value).encode("ascii", errors="backslashreplace").decode("ascii"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_tree(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def check(name: str, ok: bool, failures: list[str]) -> None:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)


def run(cmd: list[str], label: str, cwd: Path) -> int:
    emit("RUN=" + " ".join(cmd))
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    emit(completed.stdout)
    emit(f"{label}_EXIT={completed.returncode}")
    return completed.returncode


def between(text: str, start: str, end: str) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start))
    return text[i:] if j < 0 else text[i:j]


def main() -> int:
    failures: list[str] = []
    emit("=== VERTEX SESSION PORTAL / WORKSTATION SAFETY CONTROL UI 000057V1 VERIFY ===")
    emit(f"ROOT={ROOT}")
    emit(f"WORKSTATION_READ_ONLY={WS_ROOT}")
    emit("PRODUCTION_MUTATION_FROM_VERIFY=NO")

    required = {
        "CLIENT": CLIENT,
        "SERVICE": SERVICE,
        "IPC": IPC,
        "PRELOAD": PRELOAD,
        "CONTRACTS": CONTRACTS,
        "MAINFRAME": MAIN,
        "DISPATCH_BAY": DISPATCH,
        "WS_SAFETY_STATE": WS_SAFETY,
        "WS_SERVER_ADAPTER": WS_SERVER,
        "WS_CORE_BRIDGE": WS_CORE,
        "PARENT_FINAL_B_H2": PARENT_FINAL_B,
        "WS_SAFETY_RAY": WS_RAY,
    }
    for name, path in required.items():
        check(f"FILE_{name}", path.is_file(), failures)
    if failures:
        emit("RED=REQUIRED_FILE_MISSING")
        emit("FAILURES=" + ",".join(failures))
        return 2

    client = read(CLIENT)
    service = read(SERVICE)
    ipc = read(IPC)
    preload = read(PRELOAD)
    contracts = read(CONTRACTS)
    main = read(MAIN)
    dispatch = read(DISPATCH)
    ws_safety = read(WS_SAFETY)
    ws_server = read(WS_SERVER)
    ws_core = read(WS_CORE)

    # Workstation production contract: exact, READ-ONLY observed.
    check("WS_BIND_127_0_0_1_47832", 'pub const DEFAULT_BIND: &str = "127.0.0.1:47832"' in ws_server, failures)
    check("WS_GET_SAFETY_EXACT", 'request.method == "GET" && request.path == "/v1/safety"' in ws_server, failures)
    for action in ("drain", "estop", "reset", "resume"):
        check(f"WS_POST_SAFETY_{action.upper()}_EXACT", f'"/v1/safety/{action}"' in ws_server, failures)
    request_block = between(ws_safety, "pub struct SafetyActionRequest", "pub struct SafetyMetrics")
    check("WS_REQUEST_DENY_UNKNOWN_FIELDS", '#[serde(deny_unknown_fields)]' in ws_safety[: ws_safety.find("pub struct SafetyActionRequest")], failures)
    check("WS_REQUEST_ID_FIELD", "pub request_id: String" in request_block, failures)
    check("WS_AUTHORITY_FIELD", "pub authority: String" in request_block, failures)
    check("WS_REASON_FIELD", "pub reason: String" in request_block, failures)
    check("WS_HUMAN_AUTHORITY_EXACT", 'request.authority != "HUMAN"' in ws_safety and "SAFETY_HUMAN_AUTHORITY_REQUIRED" in ws_safety, failures)
    check("WS_REQUEST_ID_MAX_256", 'validate_field("request_id", &request.request_id, 256)' in ws_safety, failures)
    check("WS_REASON_MAX_2048", 'validate_field("reason", &request.reason, 2048)' in ws_safety, failures)
    for state in ("RUNNING", "DRAINING", "ESTOP_LATCHED", "RESET_READY"):
        check(f"WS_STATE_{state}", f'"{state}"' in ws_safety, failures)
    check("WS_DRAIN_IDEMPOTENT", "SafetyAction::Drain => state == SafetyState::Draining" in ws_safety, failures)
    check("WS_ESTOP_IDEMPOTENT", "SafetyAction::Estop => state == SafetyState::EstopLatched" in ws_safety, failures)
    check("WS_RESET_IDEMPOTENT", "SafetyAction::Reset => state == SafetyState::ResetReady" in ws_safety, failures)
    check("WS_RESUME_EXACT_REQUEST_ID_RETRY", 'document.last_request_id.as_deref() == Some(request.request_id.as_str())' in ws_safety, failures)
    check("WS_RESET_RECOVERY_PRECONDITION", 'require_recovery_ready(&metrics, "RESET")' in ws_safety, failures)
    check("WS_RESUME_RECOVERY_PRECONDITION", 'require_recovery_ready(&metrics, "RESUME")' in ws_safety, failures)
    check("WS_RECOVERY_ACTIVE_JOBS_ZERO", "metrics.active_jobs != 0" in ws_safety, failures)
    check("WS_RECOVERY_RESULT_PASS", 'metrics.recovery_result != "PASS"' in ws_safety, failures)
    check("WS_ERROR_409_SAFETY", all(token in ws_server for token in ["SAFETY_STATE_REJECTED", "SAFETY_TRANSITION_INVALID", "SAFETY_RECOVERY_BLOCKED"]), failures)
    check("WS_ERROR_403_HUMAN", "SAFETY_HUMAN_AUTHORITY_REQUIRED" in ws_server, failures)
    check("WS_ERROR_ENVELOPE", 'json!({ "error": { "code": code, "message": message.into() } })' in ws_server, failures)
    check("WS_GET_RESPONSE_SAFETY", '"safety": state' in ws_core, failures)
    check("WS_GET_RESPONSE_METRICS", '"metrics": metrics' in ws_core, failures)
    check("WS_OBSERVATION_PLANE_ALIVE", '"observation_plane": "ALIVE"' in ws_core, failures)
    check("WS_EVIDENCE_RETURN_PLANE_ALIVE", '"evidence_return_plane": "ALIVE"' in ws_core, failures)
    check("WS_AUTO_RESET_ZERO", '"auto_reset": false' in ws_safety, failures)
    check("WS_AUTO_RESUME_ZERO", '"auto_resume": false' in ws_safety, failures)

    # Portal main-only HTTP boundary and fixed schema.
    check("CLIENT_LOOPBACK_HOST_ONLY", "host: '127.0.0.1'" in client and "port: 47832" in client, failures)
    check("CLIENT_TIMEOUT_PRESENT", "timeoutMs: 2500" in client, failures)
    check("CLIENT_GET_SAFETY", "this.jsonRequest('GET', '/v1/safety')" in client, failures)
    for action, path in (("DRAIN","drain"),("ESTOP","estop"),("RESET","reset"),("RESUME","resume")):
        check(f"CLIENT_{action}_FIXED_PATH", f"case '{action}': return '/v1/safety/{path}'" in client, failures)
    check("CLIENT_NO_RENDERER_ARBITRARY_HTTP", "node:http" not in main and "fetch(" not in main, failures)
    check("PORTAL_REQUEST_HAS_NO_AUTHORITY_INPUT", "export interface WorkstationSafetyActionRequest {" in contracts and "authority:" not in between(contracts, "export interface WorkstationSafetyActionRequest", "export interface WorkstationSafetyActionResult"), failures)
    check("MAIN_SERVICE_INJECTS_HUMAN_AUTHORITY", "authority: 'HUMAN'" in service, failures)
    check("SAFETY_IPC_STATE_FIXED", "'workstation:safety-state'" in ipc and "service.getWorkstationSafety()" in ipc, failures)
    check("SAFETY_IPC_ACTION_FIXED", "'workstation:safety-action'" in ipc and "service.performWorkstationSafetyAction(request)" in ipc, failures)
    check("SAFETY_PRELOAD_STATE", "getWorkstationSafety:" in preload and "ipcRenderer.invoke('workstation:safety-state')" in preload, failures)
    check("SAFETY_PRELOAD_ACTION", "performWorkstationSafetyAction:" in preload and "ipcRenderer.invoke('workstation:safety-action', request)" in preload, failures)

    # No optimistic safety authority: POST -> GET -> verified observation.
    safety_action_method = between(service, "async performWorkstationSafetyAction", "onChanged(listener")
    post_pos = safety_action_method.find("await this.workstation.safetyAction")
    get_pos = safety_action_method.find("await this.workstation.getSafety()")
    set_pos = safety_action_method.find("this.setWorkstationSafety(observation)")
    check("ESTOP_POST_THEN_GET_RECHECK", 0 <= post_pos < get_pos < set_pos, failures)
    check("POST_REVERIFY_STATE_GENERATION", "observation.state !== post.state || observation.generation !== post.generation" in safety_action_method, failures)
    check("NO_OPTIMISTIC_MAINFRAME_STATE", "const result = await window.vertexPortal.performWorkstationSafetyAction" in main and "this.safety = result.observation" in main, failures)

    # Human confirmation + exact action availability.
    ui_action_method = between(main, "private async performSafetyAction", "private bindSafetyControls")
    confirm_pos = ui_action_method.find("window.confirm(")
    action_pos = ui_action_method.find("performWorkstationSafetyAction")
    check("HUMAN_CONFIRM_BEFORE_POST", 0 <= confirm_pos < action_pos, failures)
    check("E_STOP_VISUALLY_DISTINCT", 'class="safetyAction${danger ? \' estop\' : \'\'}"' in main and ".safetyAction.estop" in main, failures)
    check("RUNNING_CONTROLS", "state === 'RUNNING'" in main and "button('DRAIN', 'DRAIN')" in main and "button('ESTOP', 'EMERGENCY STOP', true)" in main, failures)
    check("DRAINING_DISTINCT", "state === 'DRAINING'" in main and "button('RESUME', 'RESUME')" in main, failures)
    check("ESTOP_RESET_ONLY", "state === 'ESTOP_LATCHED'" in main and "actions.push(button('RESET', 'RESET'))" in main, failures)
    check("RESET_READY_RESUME", "state === 'RESET_READY'" in main and "actions.push(button('RESUME', 'RESUME'))" in main, failures)
    check("RESET_NOT_AUTO_RUNNING", "case 'RESET': return 'RESET_READY'" in main, failures)
    check("RESUME_EXPLICIT_HUMAN", "case 'RESUME': return 'RUNNING'" in main and "window.confirm" in ui_action_method, failures)
    check("AUTO_RESET_ZERO_PORTAL", "AUTO RESET" not in main.upper() and "setTimeout(() => void this.performSafetyAction('RESET')" not in main, failures)
    check("AUTO_RESUME_ZERO_PORTAL", "setTimeout(() => void this.performSafetyAction('RESUME')" not in main and "setInterval(() => void this.performSafetyAction" not in main, failures)

    # Durable request id provides safe Human retry, especially RESUME response-loss.
    check("REQUEST_ID_DURABLE_LOCAL", "SAFETY_PENDING_KEY" in main and "window.localStorage.setItem(SAFETY_PENDING_KEY" in main, failures)
    check("REQUEST_ID_REUSED_SAME_ACTION", "if (existing?.action === action) return existing" in main, failures)
    check("NO_AUTO_POST_RETRY", ui_action_method.count("performWorkstationSafetyAction") == 1, failures)
    check("RESPONSE_LOSS_GET_ONLY", "await this.refreshSafety(false)" in ui_action_method and "No automatic POST retry" in ui_action_method, failures)

    # Restart/offline semantics are Workstation-authoritative.
    bootstrap = between(main, "private async bootstrap", "private async refreshStatus")
    check("PORTAL_RESTART_GET_SAFETY", "await this.refreshSafety(false)" in bootstrap and "getWorkstationSafety()" in main, failures)
    check("OFFLINE_UNKNOWN_NOT_RUNNING", "state: 'UNKNOWN'" in main and "online: false" in main and "UNKNOWN / OFFLINE" in main, failures)
    check("OFFLINE_CONTROLS_DISABLED", "if (!this.safety?.online || this.safetyBusy) return false" in main, failures)
    check("NO_PORTAL_FAKE_RUNNING_DEFAULT", "private safety: WorkstationSafetyObservation | null = null" in main, failures)

    # Safety hold prevents Portal starting new Workstation registration while stopped, but does not
    # cut observation/evidence for already-registered jobs.
    check("DISPATCH_BAY_SAFETY_HOLD", "private safetyHoldState()" in dispatch and "safetyHold ? 'disabled'" in dispatch, failures)
    check("SERVICE_NEW_REGISTRATION_REQUIRES_RUNNING", "card.workstationRegistration !== 'REGISTERED' && this.workstationSafety.state !== 'RUNNING'" in service, failures)
    check("SAFETY_REJECT_REGISTRATION_RETRYABLE", "error.code === 'SAFETY_STATE_REJECTED'" in service and "? 'PENDING'" in service, failures)
    check("REGISTERED_JOB_OBSERVATION_DURING_STOP", "const response = await this.workstation.getJob(card.jobId)" in service and "await this.retrieveEvidence(card)" in service, failures)
    check("EVIDENCE_ACK_PRESERVED_PORTAL", "acknowledgeEvidenceDelivery" in service and "acknowledgeVraEvidenceDelivery" in preload, failures)

    # Existing Final Wiring B invariants remain present before its own full verifier runs.
    check("FINAL_B_PROMPT_RELAY_PRESERVED", "readClipboardText(): Promise<string>" in contracts, failures)
    check("FINAL_B_DISPLAY_TITLE_PRESERVED", "vertex.vera.display-title" in read(ROOT / "src" / "renderer" / "src" / "components" / "VeraBrowserSession" / "VeraBrowserSession.ts"), failures)
    check("FINAL_B_32_LANE_PULSE_PRESERVED", "const MAX_LOGICAL_LANES = 32" in main, failures)
    check("FINAL_B_PATH_HIDDEN", "stagedPath" not in dispatch and "worksPath" not in dispatch, failures)
    check("NO_DIRECT_HTTP_APPLY_VERIFY_ROLLBACK", all(token not in client for token in ["/v1/apply", "/v1/verify", "/v1/rollback"]), failures)

    if failures:
        emit("RED=STATIC_CONTRACT_FAILURE")
        emit("FAILURES=" + ",".join(failures))
        return 3

    portal_before = snapshot_tree(ROOT / "src")
    ws_before = {p.as_posix(): digest(p) for p in WS_FILES}

    # Reconfirm the physically-applied Workstation E-STOP source through its READ-ONLY Ray.
    ws_ray_exit = run([sys.executable, str(WS_RAY)], "WORKSTATION_SAFETY_RAY", WS_ROOT)
    check("WORKSTATION_SAFETY_RAY_PASS", ws_ray_exit == 0, failures)

    # Parent H2 performs all Final Wiring B static checks and its H1 performs actual npm typecheck/build.
    parent_exit = run([sys.executable, str(PARENT_FINAL_B)], "FINAL_B_H2_FULL", ROOT)
    check("FINAL_B_H2_FULL_REGRESSION", parent_exit == 0, failures)

    portal_after = snapshot_tree(ROOT / "src")
    ws_after = {p.as_posix(): digest(p) for p in WS_FILES}
    check("VERIFY_PORTAL_SOURCE_UNCHANGED", portal_before == portal_after, failures)
    check("WORKSTATION_PRODUCTION_UNCHANGED", ws_before == ws_after, failures)

    if failures:
        emit("RED=VERIFY_FAILURE")
        emit("YELLOW=REQUIRES_REPAIR")
        emit("FAILURES=" + ",".join(failures))
        emit("VERTEX_SESSION_PORTAL_ESTOP_SAFETY_UI_000057V1=FAIL")
        return 1

    emit("UI_PLACEMENT=HEADER_NEXT_TO_WORKSTATION_PULSE")
    emit("SAFETY_AUTHORITY=WORKSTATION")
    emit("PORTAL_AUTHORITY=HUMAN_UI_ONLY")
    emit("SAFETY_HTTP=127.0.0.1:47832_ONLY")
    emit("CONFIRMATION=REQUIRED_BEFORE_DRAIN_ESTOP_RESET_RESUME")
    emit("ESTOP_UI_CONFIRMATION=POST_THEN_GET_RECHECK_NO_OPTIMISTIC_STATE")
    emit("PORTAL_RESTART=GET_V1_SAFETY")
    emit("OFFLINE=UNKNOWN_OFFLINE_NO_FALSE_RUNNING")
    emit("AUTO_RESET=0")
    emit("AUTO_RESUME=0")
    emit("WORKSTATION_MUTATION=NO")
    emit("RED=NONE")
    emit("YELLOW=NONE")
    emit("VERTEX_SESSION_PORTAL_ESTOP_SAFETY_UI_000057V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
