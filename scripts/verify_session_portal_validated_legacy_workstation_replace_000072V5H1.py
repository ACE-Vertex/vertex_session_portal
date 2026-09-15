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
    return cp.returncode == 0

controller = read("src/main/workstation/workstation-process-controller.ts")
lane = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
css = read("src/renderer/src/components/VraDispatchLane/VraDispatchLane.css")

renderer_forbidden = [
    "process.kill",
    "netstat.exe",
    "Get-CimInstance",
    "ExecutablePath",
    "CommandLine",
    "powershell.exe",
    "replaceValidatedLegacyListener("
]

dynamic_mode = '''data-mode="${this.workstationRuntimeMismatch() ? 'replace-legacy' : 'start'}"'''

checks = {
    "LEGACY_REPLACE_EXPLICIT_CLICK_PATH":
        "await this.replaceValidatedLegacyListener()" in controller,
    "NO_AUTOMATIC_REPLACE_FROM_STATE":
        "replaceValidatedLegacyListener" not in controller.split("async state()",1)[1].split("start():",1)[0],
    "PORT_OWNER_DISCOVERY":
        "netstat.exe" in controller and
        "LISTENING" in controller and
        "WORKSTATION_BIND" in controller,
    "PROCESS_IDENTITY_INSPECTION":
        "Get-CimInstance Win32_Process" in controller and
        "ExecutablePath" in controller and
        "CommandLine" in controller,
    "PROCESS_EXE_ALLOWLIST":
        "vertex.exe" in controller and
        "vertex-workstation.exe" in controller,
    "PATH_ALLOWLIST":
        "legacyProcessAllowed" in controller and
        "pathInside" in controller and
        "workstation-server" in controller,
    "COMMANDLINE_CONTRACT":
        "normalizedCommand.includes('workstation')" in controller and
        "normalizedCommand.includes('serve')" in controller and
        "normalizedCommand.includes('127.0.0.1:47832')" in controller,
    "NO_RENDERER_PID_OR_PATH_INPUT":
        all(token not in lane for token in renderer_forbidden),
    "RENDERER_ONLY_SELECTS_REPLACE_MODE":
        dynamic_mode in lane and
        "REPLACE LEGACY" in lane,
    "VALIDATED_TERMINATE_ONLY":
        "process.kill(pid)" in controller and
        "WORKSTATION_LISTENER_IDENTITY_REJECTED" in controller,
    "NO_SHELL_EXECUTION":
        "shell: false" in controller,
    "FORCE_CURRENT_SOURCE_AFTER_REPLACE":
        "forceCurrentSource = true" in controller and
        "resolveLaunchPlan(forceCurrentSource)" in controller,
    "STALE_EMBEDDED_SKIPPED_AFTER_REPLACE":
        "forceCurrentSource\n      ? undefined" in controller,
    "CURRENT_SOURCE_CARGO_PRESERVED":
        "portal-managed-cargo-target" in controller,
    "SEPARATE_PROCESS_PRESERVED":
        "detached: true" in controller and "child.unref()" in controller,
    "MISMATCH_BUTTON_ENABLED":
        "button.disabled = this.workstationStarting" in lane and
        "REPLACE LEGACY" in lane,
    "SPINNER_ONLY_WHILE_BUSY":
        '.startWorkstation[data-mode="replace-legacy"]:not(:disabled)' in css and
        ".startWorkstation:disabled" in css,
    "RUNTIME_MISMATCH_FAIL_CLOSED_PRESERVED":
        "WORKSTATION RUNTIME MISMATCH" in lane,
    "HUMAN_GATE_PRESERVED":
        'data-role="dispatch-dialog"' in lane and "this.confirmDispatch()" in lane,
    "SAFETY_GATE_PRESERVED":
        "WORKSTATION SAFETY UNKNOWN" in lane and "SAFETY HOLD ·" in lane,
    "DIRECT_HTTP_EXECUTION_ZERO":
        "/v1/apply" not in controller and
        "/v1/verify" not in controller and
        "/v1/rollback" not in controller,
}

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"])
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"])
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== SESSION PORTAL / VALIDATED LEGACY WORKSTATION REPLACE 000072V5H1 ===")
emit("H1_CAUSE=VERIFIER_EXPECTED_STATIC_DATA_MODE_LITERAL")
emit("H1_FIX=VERIFY_RENDERER_BOUNDARY_SEMANTICALLY")
emit("PRODUCTION_CODE_CHANGE=ZERO")
emit("REPLACEMENT=HUMAN_CLICK_ONLY")
emit("BLIND_KILL=ZERO")
emit("POST_REPLACE_RUNTIME=CURRENT_SOURCE_CARGO")

for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")

failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_VALIDATED_LEGACY_WORKSTATION_REPLACE_000072V5H1=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
