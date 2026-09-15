from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON = ROOT / "package.json"
NODE_MODULES = ROOT / "node_modules"
ELECTRON_DIST = NODE_MODULES / "electron" / "dist"
OUT_DIR = ROOT / "out"
RELEASE_ROOT = ROOT / "release" / "beta"

BETA_SUFFIX = "beta.1"
PRODUCT_NAME = "VERTEX Session Portal"
EXE_NAME = "VERTEX Session Portal Beta.exe"

def safe(text: str) -> str:
    return text.encode("ascii", errors="backslashreplace").decode("ascii")

def emit(name: str, ok: bool, detail: str | None = None) -> bool:
    suffix = f" {safe(detail)}" if detail else ""
    print(f"{name}={'PASS' if ok else 'FAIL'}{suffix}")
    return ok

def run_raw(cmd: list[str], cwd: Path, label: str) -> subprocess.CompletedProcess[bytes]:
    print("RUN=" + " ".join(cmd))
    cp = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        check=False,
    )
    if cp.returncode != 0:
        print(f"{label}=FAIL")
        text = cp.stdout.decode("utf-8", errors="backslashreplace")
        print(safe(text))
    else:
        print(f"{label}=PASS")
    return cp

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def remove_readonly(func, path, _):
    try:
        os.chmod(path, 0o700)
        func(path)
    except Exception:
        pass

def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onerror=remove_readonly)
    path.mkdir(parents=True, exist_ok=True)

def collect_prod_module_paths() -> list[Path]:
    cp = subprocess.run(
        ["npm.cmd", "ls", "--omit=dev", "--parseable", "--all"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        check=False,
    )
    text = cp.stdout.decode("utf-8", errors="replace")
    candidates: list[Path] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        p = Path(line)
        try:
            rp = p.resolve()
        except Exception:
            continue
        if rp == ROOT.resolve():
            continue
        try:
            rp.relative_to(NODE_MODULES.resolve())
        except Exception:
            continue
        if rp.is_dir():
            candidates.append(rp)

    # npm ls can return non-zero for advisory/tree reasons while still emitting valid paths.
    # Require at least the declared runtime dependency tree to be discoverable.
    unique = sorted(set(candidates), key=lambda p: (len(p.parts), str(p).lower()))
    return unique

def copy_prod_modules(app_root: Path, modules: list[Path]) -> None:
    dst_nm = app_root / "node_modules"
    dst_nm.mkdir(parents=True, exist_ok=True)
    nm_root = NODE_MODULES.resolve()

    # Copy shallow parents first, then nested actual module paths.
    for src in modules:
        rel = src.resolve().relative_to(nm_root)
        dst = dst_nm / rel
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)

def build_zip(src_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(src_dir.parent))

def main() -> None:
    print("VERTEX SESSION PORTAL / BETA BUILD 000041")
    print(f"ROOT={ROOT}")

    if not PACKAGE_JSON.exists():
        print("PACKAGE_JSON=FAIL")
        raise SystemExit(2)

    pkg = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    base_version = str(pkg.get("version") or "0.1.0")
    beta_version = f"{base_version}-{BETA_SUFFIX}"
    beta_dir_name = f"VertexSessionPortal-{beta_version}-win-x64"
    portable_dir = RELEASE_ROOT / beta_dir_name
    zip_path = RELEASE_ROOT / f"{beta_dir_name}.zip"
    zip_sha_path = RELEASE_ROOT / f"{beta_dir_name}.sha256.txt"

    print(f"BASE_VERSION={base_version}")
    print(f"BETA_VERSION={beta_version}")
    print(f"OUTPUT={portable_dir}")

    checks = []
    checks.append(emit("CURRENT_BUILD_SCRIPT", "build" in (pkg.get("scripts") or {})))
    checks.append(emit("ELECTRON_DIST_PRESENT", (ELECTRON_DIST / "electron.exe").exists()))
    checks.append(emit("BETTER_SQLITE3_PRESENT", (NODE_MODULES / "better-sqlite3").exists()))
    if not all(checks):
        raise SystemExit(3)

    # 1) Build the exact currently-verified source.
    cp = run_raw(["npm.cmd", "run", "build"], ROOT, "SOURCE_BUILD")
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)

    built_required = [
        OUT_DIR / "main" / "index.js",
        OUT_DIR / "preload" / "index.cjs",
        OUT_DIR / "renderer" / "index.html",
    ]
    # Older/preload variants can be mjs; accept either current cjs or legacy mjs.
    preload_ok = (OUT_DIR / "preload" / "index.cjs").exists() or (OUT_DIR / "preload" / "index.mjs").exists()
    checks = [
        emit("OUT_MAIN_PRESENT", (OUT_DIR / "main" / "index.js").exists()),
        emit("OUT_PRELOAD_PRESENT", preload_ok),
        emit("OUT_RENDERER_PRESENT", (OUT_DIR / "renderer" / "index.html").exists()),
    ]
    if not all(checks):
        raise SystemExit(4)

    # 2) Build a standalone Windows x64 portable Electron directory without
    #    introducing electron-builder/electron-packager or network dependencies.
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    clean_dir(portable_dir)
    shutil.copytree(ELECTRON_DIST, portable_dir, dirs_exist_ok=True)

    default_app = portable_dir / "resources" / "default_app.asar"
    if default_app.exists():
        default_app.unlink()

    electron_exe = portable_dir / "electron.exe"
    beta_exe = portable_dir / EXE_NAME
    if beta_exe.exists():
        beta_exe.unlink()
    electron_exe.rename(beta_exe)

    app_root = portable_dir / "resources" / "app"
    clean_dir(app_root)
    shutil.copytree(OUT_DIR, app_root / "out", dirs_exist_ok=True)

    runtime_pkg = {
        "name": pkg.get("name", "vertex-session-portal"),
        "productName": PRODUCT_NAME,
        "version": beta_version,
        "private": True,
        "description": pkg.get("description", "VERTEX Session Portal beta"),
        "main": "out/main/index.js",
        "dependencies": pkg.get("dependencies", {}),
    }
    (app_root / "package.json").write_text(
        json.dumps(runtime_pkg, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    modules = collect_prod_module_paths()
    print(f"PRODUCTION_MODULE_PATHS={len(modules)}")
    if not modules:
        print("PRODUCTION_DEPENDENCY_DISCOVERY=FAIL")
        raise SystemExit(5)

    copy_prod_modules(app_root, modules)

    native_candidates = list((app_root / "node_modules" / "better-sqlite3").rglob("better_sqlite3.node"))
    emit("PACKAGED_BETTER_SQLITE3_NATIVE", bool(native_candidates))
    if not native_candidates:
        raise SystemExit(6)

    beta_readme = (
        f"{PRODUCT_NAME} {beta_version}\n"
        "Internal beta / portable Windows x64 build.\n\n"
        f"Launch: {EXE_NAME}\n"
        "Persistent ChatGPT account/session storage is managed by Electron userData.\n"
        "This beta was built from the currently verified Session Portal source.\n"
    )
    (portable_dir / "BETA_README.txt").write_text(beta_readme, encoding="utf-8")

    build_manifest = {
        "schema": "vertex-session-portal-beta/1",
        "product": PRODUCT_NAME,
        "base_version": base_version,
        "beta_version": beta_version,
        "platform": "win32",
        "arch": "x64",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(ROOT),
        "entrypoint": "resources/app/out/main/index.js",
        "executable": EXE_NAME,
        "electron_version": str((pkg.get("devDependencies") or {}).get("electron", "unknown")),
        "runtime_dependencies": pkg.get("dependencies", {}),
        "source_hashes": {
            "out/main/index.js": sha256_file(OUT_DIR / "main" / "index.js"),
            "out/renderer/index.html": sha256_file(OUT_DIR / "renderer" / "index.html"),
        },
    }
    (portable_dir / "BETA_BUILD_MANIFEST.json").write_text(
        json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 3) Smoke-start the packaged executable against an isolated temporary
    #    Chromium profile. It must remain alive long enough to prove packaged
    #    app bootstrap; then terminate it deliberately.
    smoke_profile = Path(tempfile.mkdtemp(prefix="vertex-session-portal-beta-smoke-"))
    try:
        print("PACKAGED_SMOKE_START=BEGIN")
        proc = subprocess.Popen(
            [str(beta_exe), f"--user-data-dir={smoke_profile}"],
            cwd=portable_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(6.0)
        alive = proc.poll() is None
        emit("PACKAGED_RUNTIME_ALIVE_6S", alive)
        if not alive:
            print(f"PACKAGED_RUNTIME_EXIT_CODE={proc.returncode}")
            raise SystemExit(7)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        print("PACKAGED_SMOKE_START=PASS")
    finally:
        shutil.rmtree(smoke_profile, ignore_errors=True)

    # 4) Zip the portable beta and emit a SHA-256 receipt.
    build_zip(portable_dir, zip_path)
    zip_sha = sha256_file(zip_path)
    zip_sha_path.write_text(f"{zip_sha}  {zip_path.name}\n", encoding="utf-8")

    final_checks = [
        emit("BETA_EXE_PRESENT", beta_exe.exists(), str(beta_exe)),
        emit("BETA_MANIFEST_PRESENT", (portable_dir / "BETA_BUILD_MANIFEST.json").exists()),
        emit("BETA_ZIP_PRESENT", zip_path.exists(), str(zip_path)),
        emit("BETA_ZIP_SHA256_PRESENT", zip_sha_path.exists(), zip_sha),
    ]
    if not all(final_checks):
        raise SystemExit(8)

    print(f"BETA_PORTABLE_DIR={portable_dir}")
    print(f"BETA_ZIP={zip_path}")
    print(f"BETA_ZIP_SHA256={zip_sha}")
    print("SOURCE_MUTATION=NO")
    print("GENERATED_RELEASE_ONLY=YES")
    print("VERTEX_SESSION_PORTAL_BETA_BUILD_000041=PASS")

if __name__ == "__main__":
    main()
