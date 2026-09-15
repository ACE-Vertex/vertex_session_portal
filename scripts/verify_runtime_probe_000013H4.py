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

def resolve_tool(name: str, fallback: str) -> str:
    candidate = Path(fallback)
    if candidate.exists():
        return str(candidate)

    resolved = shutil.which(name)
    if resolved:
        return resolved

    raise RuntimeError(f"{name.upper()}_NOT_FOUND")

def ensure_electron(node: str) -> str:
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

    return str(cli)

def main() -> int:
    print("VERTEX SESSION PORTAL / RUNTIME PROBE VERIFY 000013H4")
    print(f"ROOT={ROOT}")
    print("REPAIR=JSON_STRING_RENDERER_PROBE_BOUNDARY")

    npm = resolve_tool("npm.cmd", r"C:\Program Files\nodejs\npm.cmd")
    node = resolve_tool("node.exe", r"C:\Program Files\nodejs\node.exe")
    electron_cli = ensure_electron(node)

    build = run([npm, "run", "build"], timeout=180)

    if build.returncode != 0:
        print("BUILD=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H4=FAIL")
        return 2

    print("BUILD=PASS")

    env = os.environ.copy()
    env["VERTEX_RUNTIME_PROBE"] = "1"
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

    runtime = run([node, electron_cli, "."], env=env, timeout=60)

    if runtime.returncode != 0:
        print("RUNTIME=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H4=FAIL")
        return 3

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
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H4=FAIL")
        return 4

    evidence_root = ROOT / "EVIDENCE" / "RUNTIME_PROBE_000013"
    screenshot = evidence_root / "session-portal-runtime.png"
    runtime_json = evidence_root / "runtime-probe.json"

    if not screenshot.exists() or screenshot.stat().st_size == 0:
        print("SCREENSHOT_EVIDENCE=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H4=FAIL")
        return 5

    if not runtime_json.exists() or runtime_json.stat().st_size == 0:
        print("RUNTIME_JSON_EVIDENCE=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H4=FAIL")
        return 6

    print(f"SCREENSHOT_EVIDENCE={screenshot}")
    print(f"RUNTIME_JSON_EVIDENCE={runtime_json}")
    print("RUNTIME=PASS")
    print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013H4=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
