from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "release"
CANDIDATE = RELEASE_ROOT / "candidates" / "000087V5" / "VertexSessionPortal-000087V5-win-x64"
OFFICIAL = RELEASE_ROOT / "official" / "VertexSessionPortal-000087V5-win-x64"
APP_DIR_NAME = "app"
EXE_NAME = "Vertex Session Portal.exe"
SMOKE_ROOT = RELEASE_ROOT / "_smoke" / "session-portal-000087V5"

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd, label, timeout=1800):
    emit("RUN_" + label + "=" + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=timeout,
    )
    emit(f"{label}_EXIT={cp.returncode}")
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-12000:].replace("\n", " | "))
    return cp

def copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)

def production_module_paths(npm: str) -> list[Path]:
    cp = run([npm, "ls", "--omit=dev", "--parseable", "--all"], "PRODUCTION_MODULES", timeout=300)
    if cp.returncode not in (0, 1):
        raise RuntimeError(f"NPM_LS_FAILED:{cp.returncode}")

    paths: list[Path] = []
    root_norm = str(ROOT.resolve()).lower()
    node_modules_root = (ROOT / "node_modules").resolve()
    for raw in (cp.stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        p = Path(line)
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if str(resolved).lower() == root_norm:
            continue
        try:
            resolved.relative_to(node_modules_root)
        except ValueError:
            continue
        if resolved.exists():
            paths.append(resolved)

    unique = []
    seen = set()
    for p in paths:
        key = str(p).lower()
        if key not in seen:
            unique.append(p)
            seen.add(key)
    return unique

def package_candidate(npm: str) -> dict:
    package_json = ROOT / "package.json"
    electron_dist = ROOT / "node_modules" / "electron" / "dist"
    electron_exe = electron_dist / "electron.exe"
    out_dir = ROOT / "out"

    if not package_json.is_file():
        raise RuntimeError("PACKAGE_JSON_MISSING")
    if not electron_exe.is_file():
        raise RuntimeError("ELECTRON_EXE_MISSING")
    if not out_dir.is_dir():
        raise RuntimeError("OUT_DIR_MISSING_AFTER_BUILD")

    if CANDIDATE.exists():
        shutil.rmtree(CANDIDATE)
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)

    # Start from the exact installed Electron runtime used by this project.
    copytree(electron_dist, CANDIDATE)

    packaged_exe = CANDIDATE / EXE_NAME
    original_electron_exe = CANDIDATE / "electron.exe"
    if packaged_exe.exists():
        packaged_exe.unlink()
    original_electron_exe.replace(packaged_exe)

    app_dir = CANDIDATE / "resources" / APP_DIR_NAME
    app_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(package_json, app_dir / "package.json")
    package_lock = ROOT / "package-lock.json"
    if package_lock.is_file():
        shutil.copy2(package_lock, app_dir / "package-lock.json")

    copytree(out_dir, app_dir / "out")

    modules = production_module_paths(npm)
    node_modules_root = (ROOT / "node_modules").resolve()
    packaged_modules = []
    for module in modules:
        rel = module.resolve().relative_to(node_modules_root)
        dst = app_dir / "node_modules" / rel
        if module.is_dir():
            copytree(module, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(module, dst)
        packaged_modules.append(rel.as_posix())

    if not packaged_exe.is_file() or packaged_exe.stat().st_size < 1_000_000:
        raise RuntimeError("PACKAGED_EXE_INVALID")

    native_candidates = list((app_dir / "node_modules" / "better-sqlite3").rglob("*.node"))
    if not native_candidates:
        raise RuntimeError("PACKAGED_BETTER_SQLITE3_NATIVE_MISSING")

    source_hashes = {}
    for rel in ["package.json"]:
        p = ROOT / rel
        source_hashes[rel] = sha256(p)
    for p in sorted(out_dir.rglob("*")):
        if p.is_file():
            source_hashes[p.relative_to(ROOT).as_posix()] = sha256(p)

    manifest = {
        "schema": "vertex-session-portal/official-portable-release-1",
        "artifact_id": "vertex-session-portal-official-portable-release-000087V5",
        "project_root": str(ROOT),
        "package_name": EXE_NAME,
        "candidate_dir": str(CANDIDATE),
        "official_dir": str(OFFICIAL),
        "packaged_exe_sha256": sha256(packaged_exe),
        "packaged_exe_size": packaged_exe.stat().st_size,
        "production_modules": packaged_modules,
        "native_modules": [str(p.relative_to(CANDIDATE)).replace("\\", "/") for p in native_candidates],
        "source_hashes": source_hashes,
    }
    (CANDIDATE / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (CANDIDATE / f"{EXE_NAME}.sha256.txt").write_text(
        f"{manifest['packaged_exe_sha256']}  {EXE_NAME}\n",
        encoding="utf-8",
    )
    return manifest

def smoke_candidate() -> None:
    exe = CANDIDATE / EXE_NAME
    if SMOKE_ROOT.exists():
        try:
            shutil.rmtree(SMOKE_ROOT)
        except OSError:
            pass
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)

    cmd = [str(exe), f"--user-data-dir={SMOKE_ROOT}"]
    emit("SMOKE_RUN=" + " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        cwd=str(CANDIDATE),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    emit(f"SMOKE_PID={proc.pid}")

    try:
        time.sleep(5)
        code = proc.poll()
        if code is not None:
            raise RuntimeError(f"PORTABLE_RUNTIME_EXITED_EARLY:{code}")
        emit("PORTABLE_RUNTIME_ALIVE_5S=PASS")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        emit("PORTABLE_RUNTIME_TERMINATED=PASS")

def promote_official() -> None:
    OFFICIAL.parent.mkdir(parents=True, exist_ok=True)
    staging = OFFICIAL.parent / (OFFICIAL.name + ".next")

    if staging.exists():
        shutil.rmtree(staging)
    copytree(CANDIDATE, staging)

    # Final package content is never exposed half-copied.
    if OFFICIAL.exists():
        shutil.rmtree(OFFICIAL)
    os.replace(staging, OFFICIAL)

    pointer = RELEASE_ROOT / "official" / "CURRENT.txt"
    pointer.write_text(
        "\n".join([
            "VERTEX SESSION PORTAL OFFICIAL PORTABLE RELEASE",
            f"ARTIFACT=000087V5",
            f"DIRECTORY={OFFICIAL}",
            f"EXE={OFFICIAL / EXE_NAME}",
            f"SHA256={sha256(OFFICIAL / EXE_NAME)}",
            "",
        ]),
        encoding="utf-8",
    )

def main():
    emit("=== VERTEX SESSION PORTAL / OFFICIAL PORTABLE RELEASE 000087V5 ===")
    emit(f"ROOT={ROOT}")
    emit(f"OFFICIAL={OFFICIAL}")
    emit(f"OFFICIAL_EXE={OFFICIAL / EXE_NAME}")
    emit("WINDOWS_REQUIRED=YES")
    emit("CURRENT_SOURCE=YES")
    emit("PRODUCTION_SOURCE_MUTATION=ZERO")
    emit("BUILD_ARTIFACT_MUTATION=YES")

    if os.name != "nt":
        emit("FAIL=WINDOWS_REQUIRED")
        return 2

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        emit("FAIL=NPM_NOT_FOUND")
        return 3

    build = run([npm, "run", "build"], "CURRENT_SOURCE_BUILD")
    if build.returncode != 0:
        emit("FAIL=CURRENT_SOURCE_BUILD")
        return 4
    emit("CURRENT_SOURCE_BUILD=PASS")

    try:
        manifest = package_candidate(npm)
        emit(f"CANDIDATE_EXE_SHA256={manifest['packaged_exe_sha256']}")
        emit(f"PRODUCTION_MODULES={len(manifest['production_modules'])}")
        emit(f"NATIVE_MODULES={len(manifest['native_modules'])}")
        smoke_candidate()
        promote_official()
    except Exception as exc:
        emit(f"FAIL={type(exc).__name__}:{exc}")
        return 5

    official_exe = OFFICIAL / EXE_NAME
    if not official_exe.is_file():
        emit("FAIL=OFFICIAL_EXE_MISSING")
        return 6

    official_sha = sha256(official_exe)
    emit(f"OFFICIAL_EXE={official_exe}")
    emit(f"OFFICIAL_EXE_SHA256={official_sha}")
    emit(f"OFFICIAL_EXE_SIZE={official_exe.stat().st_size}")
    emit("PACKAGED_BETTER_SQLITE3_NATIVE=PASS")
    emit("PORTABLE_RUNTIME_SMOKE=PASS")
    emit("VERTEX_SESSION_PORTAL_OFFICIAL_PORTABLE_RELEASE_000087V5=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
