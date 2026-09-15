from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import time
import urllib.request

PORTAL_ROOT = Path(__file__).resolve().parents[1]
DEV_ROOT = PORTAL_ROOT.parent
WORKSTATION_ROOT = DEV_ROOT / "vertex_workstation"

RELEASE_ROOT = PORTAL_ROOT / "release"
CANDIDATE = RELEASE_ROOT / "candidates" / "000087V5H2" / "VertexSessionPortal-000087V5H2-win-x64"
OFFICIAL = RELEASE_ROOT / "official" / "VertexSessionPortal-000087V5H2-win-x64"
BUNDLE_BUILD = RELEASE_ROOT / "_bundle_build" / "000087V5H2"
WORKSTATION_TARGET = BUNDLE_BUILD / "workstation-target"

EXE_NAME = "Vertex Session Portal.exe"
RUNTIME_NAME = "Vertex Session Portal.runtime.exe"
LAUNCHER_SOURCE = PORTAL_ROOT / "tools" / "portable_launcher" / "session_portal_self_contained_launcher_000087V5H2.rs"

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run(cmd, label, cwd=None, timeout=1800):
    emit("RUN_" + label + "=" + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(cwd or PORTAL_ROOT),
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

def copytree(src: Path, dst: Path):
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
    cp = run([npm, "ls", "--omit=dev", "--parseable", "--all"], "PRODUCTION_MODULES", timeout=300)
    if cp.returncode not in (0, 1):
        raise RuntimeError(f"NPM_LS_FAILED:{cp.returncode}")

    nm = (PORTAL_ROOT / "node_modules").resolve()
    seen = set()
    result = []
    for raw in (cp.stdout or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            rp = Path(line).resolve()
            rel = rp.relative_to(nm)
        except Exception:
            continue
        key = str(rp).lower()
        if key in seen or not rp.exists():
            continue
        seen.add(key)
        result.append((rp, rel))
    return result

def build_workstation(cargo: str) -> Path:
    manifest = WORKSTATION_ROOT / "headless" / "Cargo.toml"
    if not manifest.is_file():
        raise RuntimeError(f"WORKSTATION_MANIFEST_MISSING:{manifest}")

    WORKSTATION_TARGET.mkdir(parents=True, exist_ok=True)
    cp = run(
        [
            cargo,
            "build",
            "--release",
            "--manifest-path",
            manifest,
            "--bin",
            "vertex",
            "--target-dir",
            WORKSTATION_TARGET,
        ],
        "WORKSTATION_RELEASE_BUILD",
        cwd=WORKSTATION_ROOT,
    )
    if cp.returncode != 0:
        raise RuntimeError("WORKSTATION_RELEASE_BUILD_FAILED")

    binary = WORKSTATION_TARGET / "release" / "vertex.exe"
    if not binary.is_file() or binary.stat().st_size < 500_000:
        raise RuntimeError(f"WORKSTATION_RELEASE_BINARY_INVALID:{binary}")
    emit(f"WORKSTATION_BINARY={binary}")
    emit(f"WORKSTATION_SHA256={sha256(binary)}")
    return binary

def free_loopback_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port

def workstation_smoke(binary: Path):
    port = free_loopback_port()
    smoke_root = BUNDLE_BUILD / f"workstation-smoke-{port}"
    smoke_root.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [
            str(binary),
            "workstation",
            "serve",
            "--bind",
            f"127.0.0.1:{port}",
            "--root",
            str(smoke_root),
        ],
        cwd=str(smoke_root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    emit(f"WORKSTATION_SMOKE_PID={proc.pid}")
    emit(f"WORKSTATION_SMOKE_PORT={port}")

    deadline = time.time() + 12
    ok = False
    try:
        while time.time() < deadline:
            if proc.poll() is not None:
                raise RuntimeError(f"WORKSTATION_SMOKE_EXITED:{proc.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                    ok = True
                    break
            except OSError:
                time.sleep(0.12)
        if not ok:
            raise RuntimeError("WORKSTATION_SMOKE_LISTENER_TIMEOUT")
        emit("WORKSTATION_SMOKE_TCP=PASS")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=8)
        emit("WORKSTATION_SMOKE_TERMINATED=PASS")

def package_portal(npm: str, rustc: str, workstation_binary: Path):
    electron_dist = PORTAL_ROOT / "node_modules" / "electron" / "dist"
    out_dir = PORTAL_ROOT / "out"
    if not (electron_dist / "electron.exe").is_file():
        raise RuntimeError("ELECTRON_EXE_MISSING")
    if not out_dir.is_dir():
        raise RuntimeError("PORTAL_OUT_MISSING")
    if not LAUNCHER_SOURCE.is_file():
        raise RuntimeError("SELF_CONTAINED_LAUNCHER_SOURCE_MISSING")

    if CANDIDATE.exists():
        shutil.rmtree(CANDIDATE)
    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
    copytree(electron_dist, CANDIDATE)

    runtime = CANDIDATE / RUNTIME_NAME
    (CANDIDATE / "electron.exe").replace(runtime)

    launcher = CANDIDATE / EXE_NAME
    cp = run(
        [rustc, "--edition=2021", "-O", LAUNCHER_SOURCE, "-o", launcher],
        "PORTAL_BOOTSTRAP_BUILD",
        timeout=300,
    )
    if cp.returncode != 0:
        raise RuntimeError("PORTAL_BOOTSTRAP_BUILD_FAILED")
    if pe_subsystem(launcher) != 2:
        raise RuntimeError("PORTAL_BOOTSTRAP_NOT_GUI_SUBSYSTEM")

    app_dir = CANDIDATE / "resources" / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PORTAL_ROOT / "package.json", app_dir / "package.json")
    if (PORTAL_ROOT / "package-lock.json").is_file():
        shutil.copy2(PORTAL_ROOT / "package-lock.json", app_dir / "package-lock.json")
    copytree(out_dir, app_dir / "out")

    for src, rel in production_module_paths(npm):
        dst = app_dir / "node_modules" / rel
        if src.is_dir():
            copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    native = list((app_dir / "node_modules" / "better-sqlite3").rglob("*.node"))
    if not native:
        raise RuntimeError("PACKAGED_BETTER_SQLITE3_NATIVE_MISSING")

    ws_slot = CANDIDATE / "resources" / "workstation-server"
    ws_slot.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workstation_binary, ws_slot / "vertex-workstation.exe")
    (ws_slot / "runtime" / "lanes").mkdir(parents=True, exist_ok=True)
    (ws_slot / "BUNDLED_WORKSTATION.json").write_text(
        json.dumps(
            {
                "schema": "vertex-session-portal/bundled-workstation-1",
                "bind": "127.0.0.1:47832",
                "binary": "vertex-workstation.exe",
                "runtime_root": "runtime",
                "source_project": str(WORKSTATION_ROOT),
                "sha256": sha256(ws_slot / "vertex-workstation.exe"),
                "max_logical_lanes": 32,
                "default_logical_lanes": 5,
                "authority": "WORKSTATION",
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema": "vertex-session-portal/self-contained-official-release-1",
        "artifact_id": "vertex-session-portal-self-contained-bundled-workstation-000087V5H2",
        "portal_launcher": EXE_NAME,
        "portal_runtime": RUNTIME_NAME,
        "bundled_workstation": "resources/workstation-server/vertex-workstation.exe",
        "workstation_bind": "127.0.0.1:47832",
        "portal_launcher_sha256": sha256(launcher),
        "portal_runtime_sha256": sha256(runtime),
        "bundled_workstation_sha256": sha256(ws_slot / "vertex-workstation.exe"),
        "production_native_modules": [str(p.relative_to(CANDIDATE)).replace("\\\\", "/") for p in native],
        "startup_contract": "Portal launcher starts bundled Workstation only when 127.0.0.1:47832 is not already listening.",
        "human_gate": True,
        "lane_allocation_authority": "Workstation",
    }
    (CANDIDATE / "build-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (CANDIDATE / f"{EXE_NAME}.sha256.txt").write_text(
        f"{manifest['portal_launcher_sha256']}  {EXE_NAME}\n",
        encoding="utf-8",
    )
    (CANDIDATE / "Bundled Workstation.sha256.txt").write_text(
        f"{manifest['bundled_workstation_sha256']}  resources/workstation-server/vertex-workstation.exe\n",
        encoding="utf-8",
    )
    return manifest

def portal_smoke():
    launcher = CANDIDATE / EXE_NAME
    smoke_user = RELEASE_ROOT / "_smoke" / "session-portal-000087V5H2"
    smoke_user.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["VERTEX_SESSION_PORTAL_SKIP_WORKSTATION_AUTO_START"] = "1"

    proc = subprocess.Popen(
        [str(launcher), f"--user-data-dir={smoke_user}"],
        cwd=str(CANDIDATE),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )
    emit(f"PORTAL_LAUNCHER_SMOKE_PID={proc.pid}")
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.terminate()
        raise RuntimeError("PORTAL_BOOTSTRAP_DID_NOT_EXIT")

    time.sleep(5)

    # The GUI bootstrapper exits after spawning Electron. Presence of the runtime
    # is verified by exact executable path, then only that smoke runtime is stopped.
    ps = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not ps:
        raise RuntimeError("POWERSHELL_NOT_FOUND")
    want = str(CANDIDATE / RUNTIME_NAME).replace('"', '""')
    query = (
        "$ErrorActionPreference='SilentlyContinue';"
        f'$want="{want}";'
        "$rows=Get-CimInstance Win32_Process | Where-Object {"
        "$_.ExecutablePath -and "
        "([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($want))"
        "} | Select-Object ProcessId;"
        "$rows | ConvertTo-Json -Compress"
    )
    cp = subprocess.run(
        [ps, "-NoProfile", "-Command", query],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
        timeout=30,
    )
    if not cp.stdout.strip():
        raise RuntimeError("PORTAL_RUNTIME_NOT_ALIVE_AFTER_5S")
    emit("PORTAL_RUNTIME_ALIVE_5S=PASS")

    stop = (
        "$ErrorActionPreference='SilentlyContinue';"
        f'$want="{want}";'
        "Get-CimInstance Win32_Process | Where-Object {"
        "$_.ExecutablePath -and "
        "([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($want))"
        "} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(
        [ps, "-NoProfile", "-Command", stop],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
        check=False,
        timeout=30,
    )
    emit("PORTAL_RUNTIME_SMOKE_TERMINATED=PASS")

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
            "VERTEX SESSION PORTAL SELF-CONTAINED OFFICIAL RELEASE",
            "ARTIFACT=000087V5H2",
            f"DIRECTORY={OFFICIAL}",
            f"EXE={OFFICIAL / EXE_NAME}",
            f"WORKSTATION={OFFICIAL / 'resources' / 'workstation-server' / 'vertex-workstation.exe'}",
            "WORKSTATION_BIND=127.0.0.1:47832",
            "",
        ]),
        encoding="utf-8",
    )

def main():
    emit("=== SESSION PORTAL SELF-CONTAINED OFFICIAL RELEASE 000087V5H2 ===")
    emit(f"PORTAL_ROOT={PORTAL_ROOT}")
    emit(f"WORKSTATION_ROOT={WORKSTATION_ROOT}")
    emit("TOPOLOGY=PORTAL_PLUS_BUNDLED_WORKSTATION")
    emit("WORKSTATION_BIND=127.0.0.1:47832")
    emit("WORKSTATION_MAX_LANES=32")
    emit("WORKSTATION_DEFAULT_LANES=5")
    emit("HUMAN_GATE=PRESERVED")
    emit("PRODUCTION_SOURCE_MUTATION=ZERO_DURING_VERIFY")

    if os.name != "nt":
        emit("FAIL=WINDOWS_REQUIRED")
        return 2

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    cargo = shutil.which("cargo.exe") or shutil.which("cargo")
    rustc = shutil.which("rustc.exe") or shutil.which("rustc")
    if not npm or not cargo or not rustc:
        emit(f"FAIL=TOOL_MISSING npm={bool(npm)} cargo={bool(cargo)} rustc={bool(rustc)}")
        return 3

    portal_build = run([npm, "run", "build"], "PORTAL_CURRENT_SOURCE_BUILD")
    if portal_build.returncode != 0:
        emit("FAIL=PORTAL_CURRENT_SOURCE_BUILD")
        return 4

    try:
        ws_binary = build_workstation(cargo)
        workstation_smoke(ws_binary)
        manifest = package_portal(npm, rustc, ws_binary)
        portal_smoke()
        promote()
    except Exception as exc:
        emit(f"FAIL={type(exc).__name__}:{exc}")
        return 5

    bundled = OFFICIAL / "resources" / "workstation-server" / "vertex-workstation.exe"
    if not bundled.is_file():
        emit("FAIL=BUNDLED_WORKSTATION_NOT_PUBLISHED")
        return 6

    emit(f"OFFICIAL_EXE={OFFICIAL / EXE_NAME}")
    emit(f"BUNDLED_WORKSTATION={bundled}")
    emit(f"BUNDLED_WORKSTATION_SHA256={sha256(bundled)}")
    emit("SELF_CONTAINED_RUNTIME=PASS")
    emit("VERTEX_SESSION_PORTAL_SELF_CONTAINED_BUNDLED_WORKSTATION_000087V5H2=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
