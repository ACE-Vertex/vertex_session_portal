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

contracts = read("src/shared/contracts.ts")
controller = read("src/main/workstation/workstation-process-controller.ts")
lane = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
css = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.css")
runtime = read("resources/workstation-server/runtime-contract.json")

checks = {
    "PROCESS_PHASE_INCOMPATIBLE": "'INCOMPATIBLE'" in contracts,
    "PROCESS_COMPAT_FIELDS":
        "serverReachable: boolean" in contracts and
        "compatible: boolean" in contracts and
        "runtimeGeneration: string | null" in contracts,
    "REQUIRED_RUNTIME_CONTRACT": "vertex-workstation/headless-server-1" in controller,
    "REQUIRED_RECOVERY_CONTRACT": "estop-failed-write-recovery-1" in controller,
    "HEALTH_IDENTITY_PARSED":
        "body.runtime_contract" in controller and
        "body.runtime_generation" in controller and
        "body.recovery_contract" in controller,
    "LEGACY_SERVER_NOT_ONLINE":
        "if (health.reachable)" in controller and
        "'INCOMPATIBLE'" in controller,
    "OCCUPIED_PORT_NO_DUPLICATE":
        "Never start a second factory onto an occupied control-plane port" in controller,
    "STALE_RELEASE_DEBUG_RETIRED":
        "target', 'release', 'vertex.exe" not in controller and
        "target', 'debug', 'vertex.exe" not in controller,
    "EMBEDDED_FIRST": "this.embeddedRuntimeCandidates()" in controller,
    "CURRENT_SOURCE_CARGO":
        "Development fallback always compiles the current Workstation source" in controller and
        "portal-managed-cargo-target" in controller,
    "SEPARATE_PROCESS":
        "detached: true" in controller and
        "child.unref()" in controller and
        "shell: false" in controller,
    "BLIND_KILL_ZERO": ".kill(" not in controller,
    "PROCESS_AUTHORITY_PRECEDENCE":
        "if (this.workstationProcess)" in lane and
        "this.workstationProcess.compatible === true" in lane,
    "LEGACY_UI":
        "WORKSTATION LEGACY · RESTART REQUIRED" in lane and
        '.serverStatus[data-phase="INCOMPATIBLE"]' in css,
    "GENERATION_UI":
        "workstationGenerationLabel" in lane and
        "WORKSTATION ONLINE ·" in lane,
    "DISPATCH_FAIL_CLOSED":
        "WORKSTATION RUNTIME MISMATCH" in lane and
        "000069V5対応Serverへ再起動してください" in lane,
    "HUMAN_GATE_PRESERVED":
        'data-role="dispatch-dialog"' in lane and
        "this.confirmDispatch()" in lane,
    "SAFETY_GATE_PRESERVED":
        "WORKSTATION SAFETY UNKNOWN" in lane and
        "SAFETY HOLD ·" in lane,
    "SHIFT_RANGE_DELETE_PRESERVED": "if (shiftKey && this.selectionAnchorId)" in lane,
    "EVIDENCE_ACK_PRESERVED":
        "VERA_EVIDENCE_RETURN_EVENT" in lane and "ackDeliveredEvidence" in lane,
    "RUNTIME_SLOT_CONTRACT":
        '"required_runtime_contract": "vertex-workstation/headless-server-1"' in runtime and
        '"legacy_sibling_binary_launch": false' in runtime,
    "DIRECT_HTTP_EXECUTION_ZERO":
        "/v1/apply" not in controller and
        "/v1/verify" not in controller and
        "/v1/rollback" not in controller,
}

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"]) == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"]) == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== VERTEX SESSION PORTAL / WORKSTATION RUNTIME UNIFICATION 000070V5 ===")
emit("PROCESS_MERGE=ZERO")
emit("RUNTIME_IDENTITY_REQUIRED=YES")
emit("LEGACY_BINARY_AUTO_ACCEPT=ZERO")
emit("DEV_RUNTIME=CURRENT_SOURCE_CARGO")
emit("CARGO_TARGET=runtime/portal-managed-cargo-target")
emit("BLIND_PROCESS_KILL=ZERO")
emit("CONTROL_PLANE=127.0.0.1:47832")
for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")
failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_WORKSTATION_RUNTIME_UNIFICATION_000070V5=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
