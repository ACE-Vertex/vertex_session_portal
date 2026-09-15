from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "release"
CANDIDATE = RELEASE_ROOT / "candidates" / "000087V5H1" / "VertexSessionPortal-000087V5H1-win-x64"
OFFICIAL = RELEASE_ROOT / "official" / "VertexSessionPortal-000087V5H1-win-x64"
EXE_NAME = "Vertex Session Portal.exe"
RUNTIME_NAME = "Vertex Session Portal.runtime.exe"
LAUNCHER_SOURCE = ROOT / "tools" / "portable_launcher" / "session_portal_launcher_000087V5H1.rs"
SMOKE_ROOT = RELEASE_ROOT / "_smoke" / "session-portal-000087V5H1"

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
    emit(f"{label}_TAIL=" + (cp.stdout or "")[-10000:].replace("\n", " | "))
    return cp

def copytree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)

def pe_subsystem(path: Path) -> int:
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise RuntimeError("NOT_PE_MZ")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_offset:pe_offset+4] != b"PE\0\0":
        raise RuntimeError("NOT_PE_SIGNATURE")
    opt = pe_offset + 4 + 20
    return struct.unpack_from("<H", data, opt + 68)[0]

def production_module_paths(npm: str):
    cp = run([npm, "ls", "--omit=dev", "--parseable", "--all"], "PRODUCTION_MODULES", 300)
    if cp.returncode not in (0, 1):
        raise RuntimeError(f"NPM_LS_FAILED:{cp.returncode}")

    nm = (ROOT / "node_modules").resolve()
    seen = set()
    out = []
    for raw in (cp.stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        p = Path(line)
        try:
            rp = p.resolve()
            rel = rp.relative_to(nm)
        except Exception:
            continue
        key = str(rp).lower()
        if key in seen or not rp.exists():
            continue
        seen.add(key)
        out.append((rp, rel))
    return out

def build_package(npm: str, rustc: str):
    electron_dist = ROOT / "node_modules" / "electron" / "dist"
    electron_exe = electron_dist / "electron.exe"
    out_dir = ROOT / "out"

    if not electron_exe.is_file():
        raise RuntimeError("ELECTRON_EXE_MISSING")
    if not LAUNCHER_SOURCE.is_file():
        raise RuntimeError("LAUNCHER_SOURCE_MISSING")
    if not out_dir.is_dir():
        raise RuntimeError("OUT_DIR_MISSING")

    if CANDIDATE.exists():
        shutil.rmtree(CANDIDATE)
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    copytree(electron_dist, CANDIDATE)

    runtime_exe = CANDIDATE / RUNTIME_NAME
    (CANDIDATE / "electron.exe").replace(runtime_exe)

    launcher_exe = CANDIDATE / EXE_NAME
    cp = run(
        [rustc, "--edition=2021", "-O", str(LAUNCHER_SOURCE), "-o", str(launcher_exe)],
        "LAUNCHER_BUILD",
        300,
    )
    if cp.returncode != 0:
        raise RuntimeError("LAUNCHER_BUILD_FAILED")
    if pe_subsystem(launcher_exe) != 2:
        raise RuntimeError("LAUNCHER_NOT_WINDOWS_GUI_SUBSYSTEM")

    (CANDIDATE / "workspace-root.txt").write_text(str(ROOT) + "\n", encoding="utf-8")

    app_dir = CANDIDATE / "resources" / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "package.json", app_dir / "package.json")
    lock = ROOT / "package-lock.json"
    if lock.is_file():
        shutil.copy2(lock, app_dir / "package-lock.json")
    copytree(out_dir, app_dir / "out")

    modules = []
    for src, rel in production_module_paths(npm):
        dst = app_dir / "node_modules" / rel
        if src.is_dir():
            copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        modules.append(rel.as_posix())

    natives = list((app_dir / "node_modules" / "better-sqlite3").rglob("*.node"))
    if not natives:
        raise RuntimeError("PACKAGED_BETTER_SQLITE3_NATIVE_MISSING")

    if launcher_exe.stat().st_size < 100_000:
        raise RuntimeError("LAUNCHER_EXE_TOO_SMALL")
    if runtime_exe.stat().st_size < 1_000_000:
        raise RuntimeError("RUNTIME_EXE_TOO_SMALL")

    manifest = {
        "schema": "vertex-session-portal/official-portable-release-2",
        "artifact_id": "vertex-session-portal-official-portable-release-000087V5H1",
        "project_root": str(ROOT),
        "official_dir": str(OFFICIAL),
        "launcher_exe": EXE_NAME,
        "runtime_exe": RUNTIME_NAME,
        "launcher_sha256": sha256(launcher_exe),
        "runtime_sha256": sha256(runtime_exe),
        "workspace_root_hint": str(ROOT),
        "production_modules": modules,
        "native_modules": [str(p.relative_to(CANDIDATE)).replace("\\\\", "/") for p in natives],
        "cwd_contract": "launcher resolves real vertex_session_portal root before spawning Electron runtime",
    }

    (CANDIDATE / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (CANDIDATE / f"{EXE_NAME}.sha256.txt").write_text(
        f"{manifest['launcher_sha256']}  {EXE_NAME}\n",
        encoding="utf-8",
    )
    return manifest

def smoke():
    exe = CANDIDATE / EXE_NAME
    if SMOKE_ROOT.exists():
        shutil.rmtree(SMOKE_ROOT, ignore_errors=True)
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)

    launcher = subprocess.Popen(
        [str(exe), f"--user-data-dir={SMOKE_ROOT}"],
        cwd=str(CANDIDATE),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    emit(f"SMOKE_LAUNCHER_PID={launcher.pid}")
    try:
        launcher.wait(timeout=5)
    except subprocess.TimeoutExpired:
        launcher.terminate()
        raise RuntimeError("LAUNCHER_DID_NOT_EXIT")

    time.sleep(5)

    ps = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not ps:
        raise RuntimeError("POWERSHELL_NOT_FOUND_FOR_SMOKE")

    want = str(CANDIDATE / RUNTIME_NAME).replace('"', '""')
    query_script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f'$want="{want}";'
        "$rows=Get-CimInstance Win32_Process | Where-Object {"
        "$_.ExecutablePath -and "
        "([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($want))"
        "} | Select-Object ProcessId,ExecutablePath,CommandLine;"
        "$rows | ConvertTo-Json -Compress"
    )
    cp = subprocess.run(
        [ps, "-NoProfile", "-Command", query_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=30,
    )
    emit(f"SMOKE_RUNTIME_QUERY_EXIT={cp.returncode}")
    if not cp.stdout.strip():
        raise RuntimeError("PORTABLE_RUNTIME_NOT_ALIVE_AFTER_5S")
    emit("PORTABLE_RUNTIME_ALIVE_5S=PASS")

    stop_script = (
        "$ErrorActionPreference='SilentlyContinue';"
        f'$want="{want}";'
        "Get-CimInstance Win32_Process | Where-Object {"
        "$_.ExecutablePath -and "
        "([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($want))"
        "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(
        [ps, "-NoProfile", "-Command", stop_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
        check=False,
        timeout=30,
    )
    emit("SMOKE_RUNTIME_TERMINATED=PASS")

def promote():
    OFFICIAL.parent.mkdir(parents=True, exist_ok=True)
    next_dir = OFFICIAL.parent / (OFFICIAL.name + ".next")
    if next_dir.exists():
        shutil.rmtree(next_dir)
    copytree(CANDIDATE, next_dir)
    if OFFICIAL.exists():
        shutil.rmtree(OFFICIAL)
    os.replace(next_dir, OFFICIAL)

    (RELEASE_ROOT / "official" / "CURRENT.txt").write_text(
        "\n".join([
            "VERTEX SESSION PORTAL OFFICIAL PORTABLE RELEASE",
            "ARTIFACT=000087V5H1",
            f"DIRECTORY={OFFICIAL}",
            f"EXE={OFFICIAL / EXE_NAME}",
            f"RUNTIME={OFFICIAL / RUNTIME_NAME}",
            f"WORKSPACE_ROOT={ROOT}",
            "",
        ]),
        encoding="utf-8",
    )

def main():
    emit("=== SESSION PORTAL OFFICIAL PORTABLE RELEASE 000087V5H1 ===")
    emit("ROOT_CAUSE=PACKAGED_EXE_STARTED_WITH_RELEASE_DIRECTORY_AS_PROCESS_CWD")
    emit("VISIBLE_SYMPTOM=PROJECT_EXPLORER_MISTOOK_PORTABLE_PACKAGE_FOR_WORKSPACE")
    emit("FIX=GUI_LAUNCHER_NORMALIZES_WORKSPACE_ROOT_BEFORE_ELECTRON_RUNTIME")
    emit(f"ROOT={ROOT}")
    emit(f"OFFICIAL={OFFICIAL}")
    emit("SOURCE_MUTATION=ZERO")

    if os.name != "nt":
        emit("FAIL=WINDOWS_REQUIRED")
        return 2

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    rustc = shutil.which("rustc.exe") or shutil.which("rustc")
    if not npm or not rustc:
        emit(f"FAIL=TOOL_MISSING npm={bool(npm)} rustc={bool(rustc)}")
        return 3

    cp = run([npm, "run", "build"], "CURRENT_SOURCE_BUILD")
    if cp.returncode != 0:
        emit("FAIL=CURRENT_SOURCE_BUILD")
        return 4

    try:
        manifest = build_package(npm, rustc)
        emit(f"LAUNCHER_SHA256={manifest['launcher_sha256']}")
        emit(f"RUNTIME_SHA256={manifest['runtime_sha256']}")
        emit("WORKSPACE_ROOT_HINT=" + manifest["workspace_root_hint"])
        smoke()
        promote()
    except Exception as exc:
        emit(f"FAIL={type(exc).__name__}:{exc}")
        return 5

    if not (OFFICIAL / EXE_NAME).is_file():
        emit("FAIL=OFFICIAL_LAUNCHER_MISSING")
        return 6
    if not (OFFICIAL / RUNTIME_NAME).is_file():
        emit("FAIL=OFFICIAL_RUNTIME_MISSING")
        return 7

    emit(f"OFFICIAL_EXE={OFFICIAL / EXE_NAME}")
    emit(f"OFFICIAL_RUNTIME={OFFICIAL / RUNTIME_NAME}")
    emit("PROJECT_EXPLORER_CWD_CONTRACT=REAL_SOURCE_ROOT")
    emit("PORTABLE_RUNTIME_SMOKE=PASS")
    emit("VERTEX_SESSION_PORTAL_OFFICIAL_PORTABLE_RELEASE_000087V5H1=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
