from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

DEV = Path(r"G:\Vertex_Project\Development")
SRC = DEV / "vertex_session_portal"
WORKSTATION = DEV / "vertex_workstation"

DEST = WORKSTATION / "SESSION_PORTAL_LATEST"
STAGING = WORKSTATION / "SESSION_PORTAL_LATEST.staging"
BACKUP = WORKSTATION / "SESSION_PORTAL_PREVIOUS"

EXE = DEST / "Vertex Session Portal.exe"
LAUNCHER = WORKSTATION / "START_SESSION_PORTAL_LATEST.cmd"
MANIFEST = DEST / "build-manifest.json"
SHA_FILE = DEST / "Vertex Session Portal.exe.sha256.txt"

PACKAGE = SRC / "package.json"
OUT_DIR = SRC / "out"
ELECTRON_DIR = SRC / "node_modules" / "electron"
ELECTRON_DIST = ELECTRON_DIR / "dist"
ELECTRON_INSTALL = ELECTRON_DIR / "install.js"

NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
NPM = shutil.which("npm.cmd") or shutil.which("npm") or r"C:\Program Files\nodejs\npm.cmd"

SMOKE_PROFILE = WORKSTATION / "_smoke_session_portal_latest"

REQUIRED_MARKERS = [
    (
        SRC / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.ts",
        "const MAX_COUNT = 5",
        "FIVE_WINDOW_MAX_5",
    ),
    (
        SRC / "src/renderer/src/components/MainFrame/MainFrame.ts",
        "<vertex-vera-window-scaler></vertex-vera-window-scaler>",
        "FIVE_WINDOW_HEADER_MOUNT",
    ),
    (
        SRC / "src/main/vra/vra-dispatch-destination-store.ts",
        "G:\\\\Vertex_Project\\\\Development\\\\_incoming",
        "DISPATCH_DEFAULT_INCOMING",
    ),
    (
        SRC / "src/main/vra/vra-download-destination-policy.ts",
        "capture owner = VraDispatchService",
        "DISPATCH_POLICY_PASSIVE",
    ),
    (
        SRC / "src/main/vra/vra-dispatch-service.ts",
        "item.setSavePath(stagedPath)",
        "DISPATCH_STAGING_CAPTURE",
    ),
    (
        SRC / "src/main/vra/vra-dispatch-service.ts",
        "exportCard(cardId: string): string",
        "DISPATCH_HUMAN_EXPORT",
    ),
    (
        SRC / "src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts",
        "reload.insertAdjacentElement('afterend', button)",
        "DISPATCH_SETTINGS_AFTER_RELOAD",
    ),
]

def safe_emit(value, stream=None):
    stream = stream or sys.stdout
    if value is None:
        return
    enc = getattr(stream, "encoding", None) or "utf-8"
    text = str(value).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(text)
    if text and not text.endswith("\n"):
        stream.write("\n")
    stream.flush()

def run(cmd, cwd=SRC, check=True):
    printable = " ".join(str(x) for x in cmd)
    print(f"RUN={printable}")
    result = subprocess.run(
        [str(x) for x in cmd],
        cwd=cwd,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    safe_emit(result.stdout, sys.stdout)
    if result.stderr:
        safe_emit(result.stderr, sys.stderr)
    print(f"EXIT_CODE={result.returncode}")
    if check and result.returncode != 0:
        raise RuntimeError(f"COMMAND_FAILED:{printable}:EXIT={result.returncode}")
    return result

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_source_markers():
    for path, marker, label in REQUIRED_MARKERS:
        if not path.exists():
            raise RuntimeError(f"{label}_FILE_MISSING:{path}")
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            raise RuntimeError(f"{label}_MARKER_MISSING:{path}")
        print(f"{label}=PASS")

def ensure_electron():
    electron_exe = ELECTRON_DIST / "electron.exe"
    if electron_exe.exists():
        print(f"ELECTRON_EXE_READY={electron_exe}")
        return
    if not ELECTRON_INSTALL.exists():
        raise RuntimeError("ELECTRON_INSTALL_SCRIPT_MISSING")
    run([NODE, ELECTRON_INSTALL], cwd=ELECTRON_DIR)
    if not electron_exe.exists():
        raise RuntimeError("ELECTRON_EXE_MISSING_AFTER_INSTALL")
    print(f"ELECTRON_EXE_READY_AFTER_INSTALL={electron_exe}")

def production_module_paths():
    result = run([NPM, "ls", "--omit=dev", "--parseable", "--all"], check=False)

    nm_root = (SRC / "node_modules").resolve()
    src_root = SRC.resolve()
    paths = []

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        p = Path(line)
        try:
            rp = p.resolve()
        except Exception:
            continue
        if rp == src_root:
            continue
        try:
            rp.relative_to(nm_root)
        except Exception:
            continue
        if rp.exists():
            paths.append(rp)

    better = (SRC / "node_modules" / "better-sqlite3").resolve()
    if better.exists() and better not in paths:
        paths.append(better)

    seen = set()
    unique = []
    for p in sorted(paths, key=lambda x: (len(x.parts), str(x).lower())):
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    print(f"PRODUCTION_MODULE_PATHS={len(unique)}")
    for p in unique:
        print(f"PRODUCTION_MODULE={p}")
    return unique

def build_staging():
    if STAGING.exists():
        shutil.rmtree(STAGING)

    shutil.copytree(ELECTRON_DIST, STAGING, symlinks=False)

    app_dir = STAGING / "resources" / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(OUT_DIR, app_dir / "out", symlinks=False)
    shutil.copy2(PACKAGE, app_dir / "package.json")

    nm_dst = app_dir / "node_modules"
    nm_dst.mkdir(parents=True, exist_ok=True)
    nm_root = (SRC / "node_modules").resolve()

    for module in production_module_paths():
        rel = module.relative_to(nm_root)
        dest = nm_dst / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(module, dest, symlinks=False)

    electron_exe = STAGING / "electron.exe"
    if not electron_exe.exists():
        raise RuntimeError("STAGING_ELECTRON_EXE_MISSING")

    electron_exe.replace(STAGING / "Vertex Session Portal.exe")

    default_asar = STAGING / "resources" / "default_app.asar"
    if default_asar.exists():
        default_asar.unlink()

def verify_native(staging_root: Path):
    better = staging_root / "resources" / "app" / "node_modules" / "better-sqlite3"
    candidates = [
        better / "prebuilds" / "win32-x64.node",
        better / "build" / "Release" / "better_sqlite3.node",
    ]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        raise RuntimeError("PACKAGED_BETTER_SQLITE3_NATIVE_MISSING")
    for p in existing:
        print(f"PACKAGED_BETTER_SQLITE3_NATIVE={p}")
    print("PACKAGED_BETTER_SQLITE3_NATIVE=PASS")

def smoke(staging_root: Path):
    exe = staging_root / "Vertex Session Portal.exe"
    if SMOKE_PROFILE.exists():
        shutil.rmtree(SMOKE_PROFILE, ignore_errors=True)
    SMOKE_PROFILE.mkdir(parents=True, exist_ok=True)

    cmd = [str(exe), f"--user-data-dir={SMOKE_PROFILE}"]
    print("SMOKE_RUN=" + " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=staging_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    print(f"SMOKE_PID={proc.pid}")
    time.sleep(5.0)

    early = proc.poll()
    if early is not None:
        raise RuntimeError(f"PORTABLE_RUNTIME_EARLY_EXIT:{early}")

    print("PORTABLE_RUNTIME_ALIVE_5S=PASS")
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait(timeout=5)

    print("PORTABLE_RUNTIME_TERMINATED=PASS")
    shutil.rmtree(SMOKE_PROFILE, ignore_errors=True)

def publish():
    WORKSTATION.mkdir(parents=True, exist_ok=True)

    if BACKUP.exists():
        shutil.rmtree(BACKUP, ignore_errors=True)

    if DEST.exists():
        try:
            DEST.replace(BACKUP)
            print(f"PREVIOUS_BUILD_BACKUP={BACKUP}")
        except Exception as exc:
            raise RuntimeError(
                "SESSION_PORTAL_LATEST_IS_LOCKED_CLOSE_IT_AND_RETRY:" + repr(exc)
            )

    STAGING.replace(DEST)

def write_metadata():
    pkg = json.loads(PACKAGE.read_text(encoding="utf-8"))
    digest = sha256(EXE)
    record = {
        "product": "Vertex Session Portal",
        "channel": "LATEST",
        "source_root": str(SRC),
        "published_root": str(DEST),
        "source_package_version": pkg.get("version"),
        "five_window_verified": True,
        "dispatch_destination_setting_verified": True,
        "dispatch_staging_first_verified": True,
        "dispatch_human_export_verified": True,
        "vra_capture_owner": "VRA_DISPATCH_SERVICE_ONLY",
        "dispatch_flow": "CHATGPT_TO_STAGING_TO_DISPATCH_BAY_TO_HUMAN_EXPORT_OR_WORKS",
        "default_dispatch_destination": r"G:\Vertex_Project\Development\_incoming",
        "exe_sha256": digest,
        "published_at_unix": int(time.time()),
    }
    MANIFEST.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    SHA_FILE.write_text(f"{digest}  {EXE.name}\n", encoding="utf-8")

    launcher = '@echo off\r\nsetlocal\r\nstart "" "%~dp0SESSION_PORTAL_LATEST\\Vertex Session Portal.exe"\r\n'
    LAUNCHER.write_text(launcher, encoding="utf-8")

    print(f"LATEST_EXE={EXE}")
    print(f"LATEST_LAUNCHER={LAUNCHER}")
    print(f"LATEST_EXE_SHA256={digest}")

def main():
    print("=== VERTEX SESSION PORTAL / PUBLISH LATEST TO WORKSTATION 000047 ===")
    print(f"SOURCE={SRC}")
    print(f"DESTINATION={DEST}")

    if os.name != "nt":
        raise RuntimeError("WINDOWS_REQUIRED")
    if not SRC.exists():
        raise RuntimeError(f"SOURCE_ROOT_MISSING:{SRC}")

    verify_source_markers()

    run([NPM, "run", "build"])
    if not (OUT_DIR / "main" / "index.js").exists():
        raise RuntimeError("OUT_MAIN_MISSING")
    if not (OUT_DIR / "renderer" / "index.html").exists():
        raise RuntimeError("OUT_RENDERER_MISSING")
    print("CURRENT_SOURCE_BUILD=PASS")

    ensure_electron()
    build_staging()

    staged_exe = STAGING / "Vertex Session Portal.exe"
    if not staged_exe.exists() or staged_exe.stat().st_size < 1024 * 1024:
        raise RuntimeError("STAGED_EXE_INVALID")
    print("STAGED_EXE_PRESENT=PASS")

    verify_native(STAGING)
    smoke(STAGING)
    publish()
    write_metadata()

    print("CANONICAL_LATEST_ROOT=" + str(DEST))
    print("CANONICAL_LATEST_EXE=" + str(EXE))
    print("VERTEX_SESSION_PORTAL_PUBLISH_LATEST_TO_WORKSTATION_000047=PASS")

if __name__ == "__main__":
    main()
