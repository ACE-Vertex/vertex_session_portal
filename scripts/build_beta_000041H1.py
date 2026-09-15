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
BETTER_SQLITE = NODE_MODULES / "better-sqlite3"
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

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def package_dir_for(name: str, parent_pkg_dir: Path | None) -> Path | None:
    # Node-style nearest lookup: package-local node_modules first, then root node_modules.
    candidates: list[Path] = []
    if parent_pkg_dir is not None:
        candidates.append(parent_pkg_dir / "node_modules" / Path(*name.split("/")))
    candidates.append(NODE_MODULES / Path(*name.split("/")))
    for c in candidates:
        if (c / "package.json").is_file():
            return c.resolve()
    return None

def collect_runtime_packages(root_pkg: dict) -> list[Path]:
    queue: list[tuple[str, Path | None]] = [
        (name, None) for name in (root_pkg.get("dependencies") or {}).keys()
    ]
    seen: set[Path] = set()
    ordered: list[Path] = []

    while queue:
        name, parent = queue.pop(0)
        pkg_dir = package_dir_for(name, parent)
        if pkg_dir is None:
            raise RuntimeError(f"runtime dependency not found: {name}")
        if pkg_dir in seen:
            continue
        seen.add(pkg_dir)
        ordered.append(pkg_dir)

        meta = read_json(pkg_dir / "package.json")
        child_names: list[str] = []
        child_names.extend((meta.get("dependencies") or {}).keys())
        child_names.extend((meta.get("optionalDependencies") or {}).keys())
        # Include installed peer dependencies when present; skip absent optional peers.
        child_names.extend((meta.get("peerDependencies") or {}).keys())
        for child in child_names:
            local = package_dir_for(child, pkg_dir)
            if local is not None:
                queue.append((child, pkg_dir))

    return ordered

def copy_runtime_packages(app_root: Path, packages: list[Path]) -> None:
    root_resolved = ROOT.resolve()
    for src in packages:
        try:
            rel = src.resolve().relative_to(root_resolved)
        except ValueError as exc:
            raise RuntimeError(f"package escaped project root: {src}") from exc
        if not str(rel).lower().startswith("node_modules"):
            raise RuntimeError(f"unexpected runtime package path: {src}")
        dst = app_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)

def ensure_better_sqlite_native() -> list[Path]:
    native = list(BETTER_SQLITE.rglob("better_sqlite3.node"))
    if native:
        print(f"SOURCE_BETTER_SQLITE3_NATIVE_COUNT={len(native)}")
        for p in native:
            print(f"SOURCE_BETTER_SQLITE3_NATIVE={p}")
        return native

    print("SOURCE_BETTER_SQLITE3_NATIVE=MISSING_REBUILD_REQUESTED")
    cp = run_raw(["npm.cmd", "run", "rebuild:native"], ROOT, "NATIVE_REBUILD")
    if cp.returncode != 0:
        raise RuntimeError("better-sqlite3 native rebuild failed")

    native = list(BETTER_SQLITE.rglob("better_sqlite3.node"))
    if not native:
        raise RuntimeError("better-sqlite3 native binary still missing after rebuild")

    print(f"SOURCE_BETTER_SQLITE3_NATIVE_COUNT={len(native)}")
    for p in native:
        print(f"SOURCE_BETTER_SQLITE3_NATIVE={p}")
    return native

def build_zip(src_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(src_dir.parent))

def main() -> None:
    print("VERTEX SESSION PORTAL / BETA BUILD REPAIR 000041H1")
    print(f"ROOT={ROOT}")
    print("REPAIR=EXPLICIT_RUNTIME_DEPENDENCY_GRAPH_AND_NATIVE_BINARY_COPY")

    if not PACKAGE_JSON.exists():
        emit("PACKAGE_JSON", False)
        raise SystemExit(2)

    pkg = read_json(PACKAGE_JSON)
    base_version = str(pkg.get("version") or "0.1.0")
    beta_version = f"{base_version}-{BETA_SUFFIX}"
    beta_dir_name = f"VertexSessionPortal-{beta_version}-win-x64"
    portable_dir = RELEASE_ROOT / beta_dir_name
    zip_path = RELEASE_ROOT / f"{beta_dir_name}.zip"
    zip_sha_path = RELEASE_ROOT / f"{beta_dir_name}.sha256.txt"

    print(f"BASE_VERSION={base_version}")
    print(f"BETA_VERSION={beta_version}")
    print(f"OUTPUT={portable_dir}")

    checks = [
        emit("CURRENT_BUILD_SCRIPT", "build" in (pkg.get("scripts") or {})),
        emit("ELECTRON_DIST_PRESENT", (ELECTRON_DIST / "electron.exe").exists()),
        emit("BETTER_SQLITE3_PRESENT", BETTER_SQLITE.is_dir()),
    ]
    if not all(checks):
        raise SystemExit(3)

    # First guarantee that the source native module exists for the Electron ABI.
    ensure_better_sqlite_native()

    # Build the exact currently verified source.
    cp = run_raw(["npm.cmd", "run", "build"], ROOT, "SOURCE_BUILD")
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)

    preload_ok = (OUT_DIR / "preload" / "index.cjs").exists() or (OUT_DIR / "preload" / "index.mjs").exists()
    checks = [
        emit("OUT_MAIN_PRESENT", (OUT_DIR / "main" / "index.js").exists()),
        emit("OUT_PRELOAD_PRESENT", preload_ok),
        emit("OUT_RENDERER_PRESENT", (OUT_DIR / "renderer" / "index.html").exists()),
    ]
    if not all(checks):
        raise SystemExit(4)

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

    # H1: do not trust `npm ls --parseable` as the packaging source.
    # Resolve the runtime graph from package.json and copy the actual package trees.
    runtime_packages = collect_runtime_packages(pkg)
    print(f"RUNTIME_PACKAGE_COUNT={len(runtime_packages)}")
    for p in runtime_packages:
        print(f"RUNTIME_PACKAGE={p.relative_to(ROOT)}")

    copy_runtime_packages(app_root, runtime_packages)

    packaged_better = app_root / "node_modules" / "better-sqlite3"
    packaged_native = list(packaged_better.rglob("better_sqlite3.node"))
    emit("PACKAGED_BETTER_SQLITE3_DIR", packaged_better.is_dir(), str(packaged_better))
    emit("PACKAGED_BETTER_SQLITE3_NATIVE", bool(packaged_native), str(packaged_native[0]) if packaged_native else None)
    if not packaged_native:
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
        "runtime_package_count": len(runtime_packages),
        "native_binaries": [str(p.relative_to(app_root)) for p in packaged_native],
        "source_hashes": {
            "out/main/index.js": sha256_file(OUT_DIR / "main" / "index.js"),
            "out/renderer/index.html": sha256_file(OUT_DIR / "renderer" / "index.html"),
        },
    }
    (portable_dir / "BETA_BUILD_MANIFEST.json").write_text(
        json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Smoke-start packaged EXE using an isolated userData directory.
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
    print("APPLICATION_SOURCE_MUTATION=NO")
    print("GENERATED_RELEASE_ONLY=YES")
    print("VERTEX_SESSION_PORTAL_BETA_BUILD_000041H1=PASS")

if __name__ == "__main__":
    main()
