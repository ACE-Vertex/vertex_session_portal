from pathlib import Path
import json
import shutil
import subprocess
import sys
import time

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")

SOURCE_BRIDGE = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraTaskDispatchBridge.ts"
SOURCE_MAIN = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
OUT = ROOT / "out"

CURRENT_LATEST = WORKSTATION / "SESSION_PORTAL_LATEST"
BUILDS = WORKSTATION / "SESSION_PORTAL_BUILDS"
STAGING = BUILDS / "000050H1.staging"
PUBLISHED = BUILDS / "000050H1"
LAUNCHER = WORKSTATION / "START_SESSION_PORTAL_LATEST.cmd"
POINTER = WORKSTATION / "SESSION_PORTAL_LATEST.pointer.json"
SMOKE = WORKSTATION / "_smoke_session_portal_000050H1"

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

def run(cmd, cwd=ROOT, check=True):
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
    if check and cp.returncode != 0:
        raise RuntimeError(f"COMMAND_FAILED:{cp.returncode}")
    return cp

def scan_markers(root: Path):
    needles = {
        "TASK_ENVELOPE": "VERTEX_TASK_DISPATCH/1",
        "TASK_RECEIPTS": "vertex.portal.task-dispatch.receipts.v1",
        "TASK_BUTTON": "data-vertex-task-dispatch",
    }
    found = {k: False for k in needles}
    if not root.exists():
        return found
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".js", ".mjs", ".cjs", ".html"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for key, needle in needles.items():
            if needle in text:
                found[key] = True
    return found

def require_source():
    if not SOURCE_BRIDGE.exists():
        raise RuntimeError("000049_TASK_BRIDGE_MISSING")
    if not SOURCE_MAIN.exists():
        raise RuntimeError("MAINFRAME_MISSING")

    bridge = SOURCE_BRIDGE.read_text(encoding="utf-8")
    main = SOURCE_MAIN.read_text(encoding="utf-8")

    checks = {
        "000049_TASK_ENVELOPE": "VERTEX_TASK_DISPATCH/1" in bridge,
        "000049_HUMAN_CONFIRM": "VERA TASK DISPATCH" in bridge and "confirm(" in bridge,
        "000049_TASK_BUTTON": "data-vertex-task-dispatch" in bridge,
        "000049_MAIN_IMPORT": "VeraTaskDispatchBridge" in main,
    }
    for key, ok in checks.items():
        print(f"{key}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"{key}_FAILED")

def copy_runtime_baseline():
    if not CURRENT_LATEST.exists():
        raise RuntimeError(f"CURRENT_LATEST_RUNTIME_MISSING:{CURRENT_LATEST}")
    if not (CURRENT_LATEST / EXE_NAME).exists():
        raise RuntimeError("CURRENT_LATEST_EXE_MISSING")

    if STAGING.exists():
        shutil.rmtree(STAGING, ignore_errors=True)
    if PUBLISHED.exists():
        shutil.rmtree(PUBLISHED, ignore_errors=True)

    BUILDS.mkdir(parents=True, exist_ok=True)

    # Read-only copy of the already VERIFIED runtime shell.
    # This avoids rewriting/renaming the running SESSION_PORTAL_LATEST directory.
    shutil.copytree(CURRENT_LATEST, STAGING)

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
    if not exe.exists():
        raise RuntimeError("STAGED_EXE_MISSING")

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
        f'start "" "%~dp0SESSION_PORTAL_BUILDS\\000050H1\\{EXE_NAME}"\r\n'
    )
    tmp = LAUNCHER.with_suffix(".cmd.tmp")
    tmp.write_text(launcher_text, encoding="utf-8")
    tmp.replace(LAUNCHER)

    pointer = {
        "schema": "vertex-session-portal/latest-pointer-1",
        "build": "000050H1",
        "runtime_path": str(PUBLISHED),
        "exe_path": str(PUBLISHED / EXE_NAME),
        "reason": "side-by-side publish avoids mutating a running SESSION_PORTAL_LATEST runtime",
        "task_dispatch": True,
    }
    pointer_tmp = POINTER.with_suffix(".json.tmp")
    pointer_tmp.write_text(json.dumps(pointer, ensure_ascii=False, indent=2), encoding="utf-8")
    pointer_tmp.replace(POINTER)

def main():
    print("=== TASK DISPATCH RUNTIME PUBLISH 000050H1 ===")
    print("ROOT_CAUSE_000050=LEGACY_000047_PUBLISHER_FAILED_DURING_PREFLIGHT")
    print("000050_RUNTIME_MUTATION_REACHED=NO")
    print("H1_STRATEGY=BUILD_CURRENT_SOURCE_AND_SIDE_BY_SIDE_PUBLISH")

    require_source()

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise RuntimeError("NPM_NOT_FOUND")
    run([npm, "run", "build"])

    built = scan_markers(OUT / "renderer")
    for key, ok in built.items():
        print(f"BUILD_{key}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"BUILD_{key}_FAILED")

    copy_runtime_baseline()

    packaged = scan_markers(STAGING / "resources" / "app" / "out" / "renderer")
    for key, ok in packaged.items():
        print(f"STAGED_{key}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"STAGED_{key}_FAILED")

    smoke()
    publish()

    print(f"PUBLISHED_EXE={PUBLISHED / EXE_NAME}")
    print(f"LATEST_LAUNCHER={LAUNCHER}")
    print(f"LATEST_POINTER={POINTER}")
    print("RUNNING_SESSION_PORTAL_LATEST_MUTATED=NO")
    print("VERTEX_SESSION_PORTAL_TASK_DISPATCH_PUBLISH_RUNTIME_000050H1=PASS")

if __name__ == "__main__":
    main()
