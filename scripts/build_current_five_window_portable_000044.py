from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package.json"
OUT_DIR = ROOT / "out"
ELECTRON_DIR = ROOT / "node_modules" / "electron"
ELECTRON_DIST = ELECTRON_DIR / "dist"
ELECTRON_INSTALL = ELECTRON_DIR / "install.js"
NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
NPM = shutil.which("npm.cmd") or shutil.which("npm") or r"C:\Program Files\nodejs\npm.cmd"

RELEASE_ROOT = ROOT / "release" / "current" / "VertexSessionPortal-current-win-x64"
APP_DIR = RELEASE_ROOT / "resources" / "app"
EXE = RELEASE_ROOT / "Vertex Session Portal.exe"
MANIFEST = RELEASE_ROOT / "build-manifest.json"
SHA_FILE = RELEASE_ROOT / "Vertex Session Portal.exe.sha256.txt"
SMOKE_PROFILE = ROOT / "release" / "_smoke" / "session-portal-current"

REQUIRED_FIVE_WINDOW_MARKERS = [
    (ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.ts", "const MAX_COUNT = 5"),
    (ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts", "<vertex-vera-window-scaler></vertex-vera-window-scaler>"),
    (ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts", "'vera-05'"),
]

def safe_emit(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if text is None:
        return
    value = str(text)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    safe = value.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
    stream.write(safe)
    if safe and not safe.endswith("\n"):
        stream.write("\n")
    stream.flush()

def run(cmd, cwd=ROOT, timeout=None, check=True):
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
        timeout=timeout,
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

def ensure_five_window_source():
    for path, marker in REQUIRED_FIVE_WINDOW_MARKERS:
        if not path.exists():
            raise RuntimeError(f"FIVE_WINDOW_SOURCE_MISSING:{path}")
        text = path.read_text(encoding="utf-8")
        if marker not in text:
            raise RuntimeError(f"FIVE_WINDOW_MARKER_MISSING:{path}:{marker}")
    print("FIVE_WINDOW_SOURCE=PASS")

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
    result = run(
        [NPM, "ls", "--omit=dev", "--parseable", "--all"],
        cwd=ROOT,
        check=False,
    )
    # npm can return nonzero for peer/optional-tree warnings while still printing usable paths.
    raw = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    resolved_root = ROOT.resolve()
    modules = []
    for p in raw:
        try:
            rp = p.resolve()
        except Exception:
            continue
        if rp == resolved_root:
            continue
        try:
            rp.relative_to((ROOT / "node_modules").resolve())
        except Exception:
            continue
        if rp.exists():
            modules.append(rp)

    # Ensure direct runtime dependency is present even if npm tree reporting changes.
    better = (ROOT / "node_modules" / "better-sqlite3").resolve()
    if better.exists() and better not in modules:
        modules.append(better)

    # Deduplicate, keeping only the shallowest occurrence of identical paths.
    seen = set()
    unique = []
    for p in sorted(modules, key=lambda x: (len(x.parts), str(x).lower())):
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    print(f"PRODUCTION_MODULE_PATHS={len(unique)}")
    for p in unique:
        print(f"PRODUCTION_MODULE={p}")
    return unique

def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=False)

def create_portable():
    staging = RELEASE_ROOT.with_name(RELEASE_ROOT.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    if RELEASE_ROOT.exists():
        shutil.rmtree(RELEASE_ROOT)

    # Electron runtime first.
    shutil.copytree(ELECTRON_DIST, staging, symlinks=False)

    app = staging / "resources" / "app"
    app.mkdir(parents=True, exist_ok=True)

    # Current compiled application.
    shutil.copytree(OUT_DIR, app / "out", symlinks=False)
    shutil.copy2(PACKAGE, app / "package.json")

    # Runtime modules only; do not duplicate Electron/dev toolchain.
    node_modules_dst = app / "node_modules"
    node_modules_dst.mkdir(parents=True, exist_ok=True)
    nm_root = (ROOT / "node_modules").resolve()
    for src in production_module_paths():
        rel = src.relative_to(nm_root)
        dst = node_modules_dst / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, symlinks=False)

    electron_exe = staging / "electron.exe"
    if not electron_exe.exists():
        raise RuntimeError("STAGED_ELECTRON_EXE_MISSING")
    renamed = staging / "Vertex Session Portal.exe"
    electron_exe.replace(renamed)

    # Remove default app if present; resources/app is the canonical app.
    default_asar = staging / "resources" / "default_app.asar"
    if default_asar.exists():
        default_asar.unlink()

    staging.replace(RELEASE_ROOT)
    print(f"PORTABLE_DIR={RELEASE_ROOT}")
    print(f"PORTABLE_EXE={EXE}")

def verify_packaged_native():
    better_root = APP_DIR / "node_modules" / "better-sqlite3"
    if not better_root.exists():
        raise RuntimeError("PACKAGED_BETTER_SQLITE3_MISSING")
    candidates = [
        better_root / "prebuilds" / "win32-x64.node",
        better_root / "build" / "Release" / "better_sqlite3.node",
    ]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        raise RuntimeError("PACKAGED_BETTER_SQLITE3_NATIVE_MISSING")
    for p in existing:
        print(f"PACKAGED_BETTER_SQLITE3_NATIVE={p}")
    print("PACKAGED_BETTER_SQLITE3_NATIVE=PASS")

def write_manifest():
    pkg = json.loads(PACKAGE.read_text(encoding="utf-8"))
    digest = sha256(EXE)
    record = {
        "artifact": EXE.name,
        "product": "Vertex Session Portal",
        "build_kind": "current-portable-five-window",
        "source_package_version": pkg.get("version"),
        "source_root": str(ROOT),
        "five_window_source_verified": True,
        "default_window_count": 3,
        "max_window_count": 5,
        "exe_sha256": digest,
        "built_at_unix": int(time.time()),
    }
    MANIFEST.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    SHA_FILE.write_text(f"{digest}  {EXE.name}\n", encoding="utf-8")
    print(f"PORTABLE_EXE_SHA256={digest}")
    print(f"BUILD_MANIFEST={MANIFEST}")
    print(f"PACKAGE_SHA={SHA_FILE}")

def smoke():
    if SMOKE_PROFILE.exists():
        shutil.rmtree(SMOKE_PROFILE, ignore_errors=True)
    SMOKE_PROFILE.mkdir(parents=True, exist_ok=True)

    cmd = [str(EXE), f"--user-data-dir={SMOKE_PROFILE}"]
    print(f"SMOKE_RUN={' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=RELEASE_ROOT,
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

def main():
    print("=== VERTEX SESSION PORTAL / CURRENT FIVE-WINDOW PORTABLE BUILD 000044 ===")
    print(f"ROOT={ROOT}")
    if os.name != "nt":
        raise RuntimeError("WINDOWS_REQUIRED")
    print("WINDOWS_REQUIRED=PASS")

    ensure_five_window_source()
    run([NPM, "run", "build"])
    if not (OUT_DIR / "main" / "index.js").exists():
        raise RuntimeError("OUT_MAIN_MISSING")
    if not (OUT_DIR / "renderer" / "index.html").exists():
        raise RuntimeError("OUT_RENDERER_MISSING")
    print("CURRENT_SOURCE_BUILD=PASS")

    ensure_electron()
    create_portable()

    if not EXE.exists() or EXE.stat().st_size < 1024 * 1024:
        raise RuntimeError("PORTABLE_EXE_INVALID")
    print("PORTABLE_EXE_PRESENT=PASS")
    print("PORTABLE_EXE_NONTRIVIAL_SIZE=PASS")

    verify_packaged_native()
    write_manifest()
    smoke()

    print("CANONICAL_CURRENT_EXE=" + str(EXE))
    print("VERTEX_SESSION_PORTAL_CURRENT_FIVE_WINDOW_PORTABLE_BUILD_000044=PASS")

if __name__ == "__main__":
    main()
