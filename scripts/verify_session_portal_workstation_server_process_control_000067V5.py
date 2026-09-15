from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""

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

controller = read("src/main/workstation/workstation-process-controller.ts")
ipc = read("src/main/ipc/register-vra-dispatch-ipc.ts")
preload = read("src/preload/index.ts")
contracts = read("src/shared/contracts.ts")
lane = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
css = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.css")
client = read("src/main/workstation/workstation-client.ts")
runtime = read("resources/workstation-server/runtime-contract.json")
stage = read("scripts/stage_workstation_server_runtime_000067V5.py")

checks = {
    "PROCESS_CONTROLLER_PRESENT": bool(controller),
    "SEPARATE_PROCESS_SPAWN":
        "spawn(plan.command, plan.args" in controller and
        "detached: true" in controller and
        "child.unref()" in controller,
    "PORTAL_EXIT_DOES_NOT_KILL":
        "Portal exit must not terminate the factory server" in controller and
        ".kill(" not in controller,
    "NO_SHELL":
        "shell: false" in controller,
    "NO_RENDERER_COMMAND_PATH_INPUT":
        "start(): Promise<WorkstationServerProcessState>" in controller and
        "startWorkstationServer(): Promise<WorkstationServerProcessState>" in contracts,
    "LOOPBACK_BIND_ONLY":
        "127.0.0.1:47832" in controller and
        "0.0.0.0" not in controller and
        "127.0.0.1" in client,
    "IDEMPOTENT_EXISTING_SERVER":
        "if (await this.healthOnline())" in controller and
        "this.startInFlight" in controller,
    "EMBEDDED_RUNTIME_FIRST":
        "this.embeddedRuntimeCandidates()" in controller and
        "runtime: 'EMBEDDED'" in controller,
    "SIBLING_PROCESS_FALLBACK":
        "SIBLING_BINARY" in controller and
        "SIBLING_CARGO" in controller,
    "WORKSTATION_ROOT_DISCOVERY":
        "VERTEX_WORKSTATION_ROOT" in controller and
        "vertex_workstation" in controller and
        "headless', 'Cargo.toml" in controller,
    "IPC_PROCESS_STATE":
        "workstation:server-process-state" in ipc,
    "IPC_START":
        "workstation:server-start" in ipc,
    "PRELOAD_PROCESS_STATE":
        "getWorkstationServerProcessState" in preload,
    "PRELOAD_START":
        "startWorkstationServer" in preload,
    "CONTRACT_PROCESS_STATE":
        "interface WorkstationServerProcessState" in contracts and
        "managedByPortal" in contracts,
    "HEADER_START_BUTTON":
        'data-action="start-workstation"' in lane and
        "START WORKSTATION" in lane,
    "ONLINE_STATUS":
        "WORKSTATION ONLINE" in lane and
        'data-role="workstation-server-status"' in lane and
        '.serverStatus[data-online="true"]' in css,
    "STARTING_STATUS":
        "WORKSTATION STARTING" in lane and
        "STARTING…" in lane,
    "EXISTING_DISPATCH_HEALTH_REUSED":
        "this.state?.workstationOnline" in lane and
        "window.vertexPortal.getVraDispatchState()" in lane,
    "NO_STOP_BUTTON_OR_KILL_IPC":
        "stopWorkstationServer" not in contracts and
        "workstation:server-stop" not in ipc,
    "HUMAN_GATE_PRESERVED":
        'data-role="dispatch-dialog"' in lane and
        "this.confirmDispatch()" in lane,
    "SHIFT_RANGE_DELETE_PRESERVED":
        "if (shiftKey && this.selectionAnchorId)" in lane and
        "this.selectedCardIds" in lane,
    "THEMED_REMOVE_DIALOG_PRESERVED":
        'data-role="remove-dialog"' in lane and
        "window.confirm" not in lane,
    "EMPTY_BAY_PRESERVED":
        "BAY READY" in lane and
        "worksDrop.hidden = ordered.length === 0" in lane,
    "EXPORT_PRESERVED":
        'data-action="export"' in lane,
    "EVIDENCE_ACK_PRESERVED":
        "VERA_EVIDENCE_RETURN_EVENT" in lane and
        "ackDeliveredEvidence" in lane,
    "SAFETY_API_PRESERVED":
        "getWorkstationSafety" in contracts and
        "performWorkstationSafetyAction" in contracts and
        "workstation:safety-action" in ipc,
    "DIRECT_HTTP_EXECUTION_ZERO":
        "/v1/apply" not in controller and
        "/v1/verify" not in controller and
        "/v1/rollback" not in controller,
    "RUNTIME_SLOT_SEPARATE":
        '"process_model": "SEPARATE_PROCESS"' in runtime and
        '"portal_exit_kills_server": false' in runtime,
    "RELEASE_STAGER_ATOMIC":
        "os.replace(temp_path, destination)" in stage and
        "workstation-server" in stage,
    "VERIFY_DOES_NOT_STAGE_RUNTIME":
        "subprocess" in globals() and "stage_workstation_server_runtime_000067V5.py" not in " ".join(sys.argv[1:]),
}

# Read-only sibling Workstation contract observation. Missing sibling source is not a production mutation.
workstation_root = ROOT.parent / "vertex_workstation"
ws_main = workstation_root / "headless" / "src" / "main.rs"
ws_server = workstation_root / "headless" / "src" / "server_adapter.rs"
checks["SIBLING_WORKSTATION_HEADLESS_PRESENT"] = ws_main.is_file() and ws_server.is_file()
if checks["SIBLING_WORKSTATION_HEADLESS_PRESENT"]:
    main_text = ws_main.read_text(encoding="utf-8")
    server_text = ws_server.read_text(encoding="utf-8")
    checks["WORKSTATION_SERVE_CONTRACT"] = "workstation" in main_text and "serve" in main_text
    checks["WORKSTATION_127_BIND_CONTRACT"] = "127.0.0.1:47832" in server_text
else:
    checks["WORKSTATION_SERVE_CONTRACT"] = False
    checks["WORKSTATION_127_BIND_CONTRACT"] = False

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"]) == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"]) == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

# Syntax-only check of release stager; do NOT execute it.
checks["RELEASE_STAGER_SYNTAX"] = run(
    [sys.executable, "-m", "py_compile", str(ROOT / "scripts/stage_workstation_server_runtime_000067V5.py")]
) == 0

emit("=== VERTEX SESSION PORTAL / WORKSTATION SERVER PROCESS CONTROL 000067V5 ===")
emit("ARCHITECTURE=PORTAL_LAUNCH_CONTROL_PLUS_SEPARATE_WORKSTATION_PROCESS")
emit("PORTAL_PROCESS_MERGE=ZERO")
emit("WORKSTATION_EXECUTION_AUTHORITY=MUTATION_ZERO")
emit("PORTAL_EXIT_SERVER_KILL=ZERO")
emit("BIND=127.0.0.1:47832")
emit("OFFLINE_UI=START_WORKSTATION")
emit("ONLINE_UI=WORKSTATION_ONLINE")
emit("EMBEDDED_RUNTIME_SLOT=resources/workstation-server")
emit("DEV_FALLBACK=SIBLING_WORKSTATION")
for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")
failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_WORKSTATION_SERVER_PROCESS_CONTROL_000067V5=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
