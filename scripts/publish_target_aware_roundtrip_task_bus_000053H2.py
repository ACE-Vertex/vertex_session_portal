from pathlib import Path
import json
import shutil
import subprocess
import sys
import time

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")
OUT = ROOT / "out"
SOURCE_BRIDGE = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
SOURCE_MAIN = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"

BASELINE = WORKSTATION / "SESSION_PORTAL_BUILDS" / "000052"
BUILDS = WORKSTATION / "SESSION_PORTAL_BUILDS"
STAGING = BUILDS / "000053H2.staging"
PUBLISHED = BUILDS / "000053H2"
LAUNCHER = WORKSTATION / "START_SESSION_PORTAL_LATEST.cmd"
POINTER = WORKSTATION / "SESSION_PORTAL_LATEST.pointer.json"
SMOKE = WORKSTATION / "_smoke_session_portal_000053H2"
EXE_NAME = "Vertex Session Portal.exe"

def emit(value, stream=sys.stdout):
    if value is None:
        return
    enc = getattr(stream, "encoding", None) or "utf-8"
    text = str(value).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(text)
    if text and not text.endswith("\n"):
        stream.write("\n")
    stream.flush()

def run(cmd, cwd=ROOT):
    print("RUN=" + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        [str(x) for x in cmd],
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    emit(cp.stdout)
    emit(cp.stderr, sys.stderr)
    print(f"EXIT_CODE={cp.returncode}")
    if cp.returncode != 0:
        raise RuntimeError(f"COMMAND_FAILED:{cp.returncode}")
    return cp

def scan(root: Path, needle: str) -> bool:
    if not root.exists():
        return False
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".js", ".mjs", ".cjs", ".html"}:
            if needle in path.read_text(encoding="utf-8", errors="ignore"):
                return True
    return False

def require_source():
    bridge = SOURCE_BRIDGE.read_text(encoding="utf-8")
    main = SOURCE_MAIN.read_text(encoding="utf-8")

    checks = {
        "AUTO_DELIVERY_CONTRACT": "env.delivery !== 'AUTO'" in bridge,
        "AUTO_ARM_CONTROL": "dataset.vertexTaskAuto" in bridge,
        "AUTO_POLL_LOOP": "setInterval" in bridge and "pollAuto" in bridge,
        "AUTO_STABLE_POLLS": "STABLE_POLLS_REQUIRED" in bridge,
        "AUTO_NOT_PERSISTED": "armedSources = new Set" in bridge and "localStorage" not in bridge.split("const armedSources",1)[1].split("function loadReceipts",1)[0],
        "VERTEX_DIALOG": "VERTEX // TARGET ROUTER" in bridge and "vertexDialog" in bridge,
        "NATIVE_DIALOG_RETIRED": "window.confirm(" not in bridge and "window.alert(" not in bridge,
        "MAIN_IMPORT": "VeraTaskDispatchBridge" in main,
    }
    for key, ok in checks.items():
        print(f"{key}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(key + "_FAILED")

def copy_runtime():
    if not (BASELINE / EXE_NAME).exists():
        raise RuntimeError("BASELINE_000052_MISSING")

    if STAGING.exists():
        shutil.rmtree(STAGING, ignore_errors=True)
    if PUBLISHED.exists():
        shutil.rmtree(PUBLISHED, ignore_errors=True)

    BUILDS.mkdir(parents=True, exist_ok=True)
    shutil.copytree(BASELINE, STAGING)

    app = STAGING / "resources" / "app"
    if not app.exists():
        raise RuntimeError("STAGING_APP_ROOT_MISSING")

    staged_out = app / "out"
    if staged_out.exists():
        shutil.rmtree(staged_out)
    shutil.copytree(OUT, staged_out)

    package_json = ROOT / "package.json"
    if package_json.exists():
        shutil.copy2(package_json, app / "package.json")

def smoke():
    exe = STAGING / EXE_NAME
    if SMOKE.exists():
        shutil.rmtree(SMOKE, ignore_errors=True)
    SMOKE.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [str(exe), f"--user-data-dir={SMOKE}"],
        cwd=STAGING,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    print(f"SMOKE_PID={proc.pid}")
    time.sleep(5)
    if proc.poll() is not None:
        raise RuntimeError(f"SMOKE_EARLY_EXIT:{proc.returncode}")
    print("SMOKE_ALIVE_5S=PASS")

    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait(timeout=5)

    shutil.rmtree(SMOKE, ignore_errors=True)
    print("SMOKE_TERMINATED=PASS")

def publish():
    STAGING.replace(PUBLISHED)

    launcher_text = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'start "" "%~dp0SESSION_PORTAL_BUILDS\\000053H2\\{EXE_NAME}"\r\n'
    )
    tmp = LAUNCHER.with_suffix(".cmd.tmp")
    tmp.write_text(launcher_text, encoding="utf-8")
    tmp.replace(LAUNCHER)

    pointer = {
        "schema": "vertex-session-portal/latest-pointer-1",
        "build": "000053H2",
        "runtime_path": str(PUBLISHED),
        "exe_path": str(PUBLISHED / EXE_NAME),
        "task_dispatch": True,
        "auto_task_dispatch": True,
        "vertex_task_ui": True,
        "target_readiness_queue": True,
        "selective_target_routing": True,
        "distinct_prompt_per_target": True,
        "structured_result_return": True,
        "auto_default": "OFF",
    }
    tmp_pointer = POINTER.with_suffix(".json.tmp")
    tmp_pointer.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_pointer.replace(POINTER)

def main():
    print("=== VERTEX TARGET-AWARE ROUNDTRIP TASK BUS PUBLISH 000053H2 ===")
    print("ROOT_CAUSE_000053H1=COMPILED_RENDERER_VERIFY_USED_COMMENT_ONLY_MARKERS")
    print("REPAIR_000053H2=VERIFY_DURABLE_RUNTIME_SEMANTIC_STRINGS")
    print("ROOT_CAUSE_000053=INHERITED_PREFLIGHT_EXPECTED_OLD_DIALOG_LABEL")
    print("OLD_EXPECTED=VERTEX // TASK DISPATCH")
    print("CURRENT_CANONICAL=VERTEX // TARGET ROUTER")
    print("FEATURES=TARGET_READY_QUEUE|SELECTIVE_ROUTING|DISTINCT_PROMPTS|STRUCTURED_RESULT_RETURN")
    print("ROOT_CAUSE_000052=COMPOSER_WRITE_SUCCEEDED_BUT_SEND_CONTROL_LOOKUP_WAS_SYNCHRONOUS")
    print("REPAIR=ASYNC_SEND_CONTROL_WAIT_WITH_FORM_SCOPED_SUBMIT_FALLBACK")
    print("ROOT_CAUSE_000051=SOURCE_PREFLIGHT_EXPECTED_HTML_ATTRIBUTE_BUT_IMPLEMENTATION_USES_DOM_DATASET_PROPERTY")
    print("BAD_TOKEN=data-vertex-task-auto")
    print("CANONICAL_SOURCE_TOKEN=dataset.vertexTaskAuto")
    require_source()

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise RuntimeError("NPM_NOT_FOUND")
    run([npm, "run", "build"])

    renderer = OUT / "renderer"
    for key, needle in {
        "AUTO_CONTRACT": "TASK_DELIVERY_INVALID",
        "AUTO_CONTROL": "vertexTaskAuto",
        "AUTO_ARMED_LABEL": "AUTO●",
        "VERTEX_HUD": "vertexTaskHud",
        "VERTEX_AUTO_STATUS": "VERTEX // AUTO ARMED",
        "VERTEX_RECEIPTS": "vertex.portal.task-dispatch.receipts.v1",
        "SEND_COMMIT_WAIT": "TARGET_SEND_CONTROL_TIMEOUT",
        "SEND_COMMIT_OK": "SEND_COMMIT_CLICKED",
        "TARGET_READY_QUEUE": "TARGET_BUSY_GENERATING",
        "SELECTIVE_ROUTING": "TARGETS:",
        "DISTINCT_PROMPTS": "target_session=",
        "RESULT_RETURN": "VERTEX TASK RESULT RETURN",
        "RESULT_MARKER": "VERTEX_TASK_RESULT/1",
        "RESULT_CAPTURED": "VERTEX // RESULT CAPTURED",
    }.items():
        ok = scan(renderer, needle)
        print(f"BUILD_{key}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError("BUILD_" + key + "_FAILED")

    copy_runtime()

    staged_renderer = STAGING / "resources" / "app" / "out" / "renderer"
    for key, needle in {
        "AUTO_CONTRACT": "TASK_DELIVERY_INVALID",
        "AUTO_CONTROL": "vertexTaskAuto",
        "AUTO_ARMED_LABEL": "AUTO●",
        "VERTEX_HUD": "vertexTaskHud",
        "VERTEX_AUTO_STATUS": "VERTEX // AUTO ARMED",
        "VERTEX_RECEIPTS": "vertex.portal.task-dispatch.receipts.v1",
        "SEND_COMMIT_WAIT": "TARGET_SEND_CONTROL_TIMEOUT",
        "SEND_COMMIT_OK": "SEND_COMMIT_CLICKED",
        "TARGET_READY_QUEUE": "TARGET_BUSY_GENERATING",
        "SELECTIVE_ROUTING": "TARGETS:",
        "DISTINCT_PROMPTS": "target_session=",
        "RESULT_RETURN": "VERTEX TASK RESULT RETURN",
        "RESULT_MARKER": "VERTEX_TASK_RESULT/1",
        "RESULT_CAPTURED": "VERTEX // RESULT CAPTURED",
    }.items():
        ok = scan(staged_renderer, needle)
        print(f"STAGED_{key}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError("STAGED_" + key + "_FAILED")

    smoke()
    publish()

    print(f"PUBLISHED_EXE={PUBLISHED / EXE_NAME}")
    print(f"LATEST_LAUNCHER={LAUNCHER}")
    print("AUTO_DEFAULT=OFF")
    print("AUTO_ARMING=PER_VERA_PANE")
    print("NATIVE_CONFIRM_ALERT=RETIRED")
    print("VERTEX_SESSION_PORTAL_VERA_AUTO_TASK_DISPATCH_VERTEX_UI_000053H2=PASS")

if __name__ == "__main__":
    main()
