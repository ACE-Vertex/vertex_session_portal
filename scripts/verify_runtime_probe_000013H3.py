from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

def run(cmd: list[str], env: dict[str, str] | None = None, timeout: int = 120, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    actual_cwd = cwd or ROOT
    print("RUN=" + " ".join(cmd))
    print(f"CWD={actual_cwd}")

    proc = subprocess.run(
        cmd,
        cwd=actual_cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        shell=False,
        timeout=timeout,
    )

    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")

    if proc.stderr:
        print("=== STDERR ===")
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n")

    print(f"EXIT_CODE={proc.returncode}")
    return proc

def find_npm() -> str:
    candidate = Path(r"C:\Program Files\nodejs\npm.cmd")
    if candidate.exists():
        return str(candidate)

    resolved = shutil.which("npm.cmd") or shutil.which("npm")
    if resolved:
        return resolved

    raise RuntimeError("NPM_NOT_FOUND")

def find_node() -> str:
    candidate = Path(r"C:\Program Files\nodejs\node.exe")
    if candidate.exists():
        return str(candidate)

    resolved = shutil.which("node.exe") or shutil.which("node")
    if resolved:
        return resolved

    raise RuntimeError("NODE_EXE_NOT_FOUND")

def ensure_electron(node: str) -> tuple[str, str]:
    electron_dir = ROOT / "node_modules" / "electron"
    cli = electron_dir / "cli.js"
    install = electron_dir / "install.js"
    exe = electron_dir / "dist" / "electron.exe"

    if not cli.exists():
        raise RuntimeError("ELECTRON_CLI_NOT_FOUND")

    if not exe.exists():
        if not install.exists():
            raise RuntimeError("ELECTRON_INSTALL_SCRIPT_NOT_FOUND")

        install_result = run([node, str(install)], timeout=240, cwd=electron_dir)
        if install_result.returncode != 0:
            raise RuntimeError("ELECTRON_DIRECT_INSTALL_FAILED")

    if not exe.exists():
        raise RuntimeError("ELECTRON_BINARY_NOT_READY")

    return str(cli), str(exe)

def main() -> int:
    print("VERTEX SESSION PORTAL / RUNTIME PROBE VERIFY 000013H3")
    print(f"ROOT={ROOT}")
    print("REPAIR=SANDBOXED_PRELOAD_COMMONJS")

    npm = find_npm()
    node = find_node()
    electron_cli, electron_exe = ensure_electron(node)

    print(f"NPM={npm}")
    print(f"NODE={node}")
    print(f"ELECTRON_CLI={electron_cli}")
    print(f"ELECTRON_EXE={electron_exe}")

    build = run([npm, "run", "build"], timeout=180)

    if build.returncode != 0:
        print("BUILD=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H3=FAIL")
        return 2

    preload_cjs = ROOT / "out" / "preload" / "index.cjs"
    if not preload_cjs.exists():
        print(f"PRELOAD_CJS_MISSING={preload_cjs}")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H3=FAIL")
        return 3

    print(f"PRELOAD_CJS={preload_cjs}")
    print("BUILD=PASS")

    env = os.environ.copy()
    env["VERTEX_RUNTIME_PROBE"] = "1"
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

    runtime = run([node, electron_cli, "."], env=env, timeout=60)

    if runtime.returncode != 0:
        print("RUNTIME=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H3=FAIL")
        return 4

    expected = [
        "RENDERER_LOAD=PASS",
        "PRELOAD_BRIDGE=PASS",
        "MAIN_FRAME=PASS",
        "EXPLORER=PASS",
        "SESSION_COUNT=4",
        "MAIN_VERA_COUNT=3",
        "SEARCH_VERA_COUNT=1",
        "PRIORITY_COUNT=1",
        "NORMAL_WIDTHS=PASS",
        "PRIORITY_WIDTH=PASS",
        "SESSION_TOPOLOGY=PASS",
        "RUNTIME_WINDOW=PASS",
        "VERTEX_SESSION_PORTAL_RUNTIME_PROBE_000013=PASS",
    ]

    missing = [marker for marker in expected if marker not in runtime.stdout]

    if missing:
        print("MISSING_MARKERS=" + ",".join(missing))
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H3=FAIL")
        return 5

    evidence_root = ROOT / "EVIDENCE" / "RUNTIME_PROBE_000013"
    screenshot = evidence_root / "session-portal-runtime.png"
    runtime_json = evidence_root / "runtime-probe.json"

    if not screenshot.exists() or screenshot.stat().st_size == 0:
        print("SCREENSHOT_EVIDENCE=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H3=FAIL")
        return 6

    if not runtime_json.exists() or runtime_json.stat().st_size == 0:
        print("RUNTIME_JSON_EVIDENCE=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H3=FAIL")
        return 7

    print(f"SCREENSHOT_EVIDENCE={screenshot}")
    print(f"RUNTIME_JSON_EVIDENCE={runtime_json}")
    print("RUNTIME=PASS")
    print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H3=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
