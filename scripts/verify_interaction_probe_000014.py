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

def run(
    cmd: list[str],
    env: dict[str, str] | None = None,
    timeout: int = 120,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
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

        install_result = run(
            [node, str(install)],
            timeout=240,
            cwd=electron_dir,
        )

        if install_result.returncode != 0:
            raise RuntimeError("ELECTRON_DIRECT_INSTALL_FAILED")

    if not exe.exists():
        raise RuntimeError("ELECTRON_BINARY_NOT_READY")

    return str(cli)

def main() -> int:
    print("VERTEX SESSION PORTAL / INTERACTION PROBE VERIFY 000014")
    print(f"ROOT={ROOT}")

    npm = resolve_tool(
        "npm.cmd",
        r"C:\Program Files\nodejs\npm.cmd",
    )

    node = resolve_tool(
        "node.exe",
        r"C:\Program Files\nodejs\node.exe",
    )

    electron_cli = ensure_electron(node)

    build = run(
        [npm, "run", "build"],
        timeout=180,
    )

    if build.returncode != 0:
        print("BUILD=FAIL")
        print("VERTEX_SESSION_PORTAL_INTERACTION_VERIFY_000014=FAIL")
        return 2

    print("BUILD=PASS")

    env = os.environ.copy()
    env["VERTEX_INTERACTION_PROBE"] = "1"
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

    runtime = run(
        [node, electron_cli, "."],
        env=env,
        timeout=75,
    )

    if runtime.returncode != 0:
        print("INTERACTION_RUNTIME=FAIL")
        print("VERTEX_SESSION_PORTAL_INTERACTION_VERIFY_000014=FAIL")
        return 3

    expected = [
        "INITIAL_PRELOAD_BRIDGE=PASS",
        "INITIAL_SESSION_COUNT=4",
        "INITIAL_PRIORITY=vera-02",
        "INITIAL_SIDEBAR=PROJECT",
        "PRIORITY_CLICK=PASS",
        "PRIORITY_AFTER_CLICK=vera-01",
        "SIDEBAR_CLICK=PASS",
        "SIDEBAR_AFTER_CLICK=VCR",
        "SQLITE_PRIORITY_PERSISTENCE=PASS",
        "SQLITE_SIDEBAR_PERSISTENCE=PASS",
        "PERSISTED_PRIORITY=vera-01",
        "PERSISTED_SIDEBAR=VCR",
        "INTERACTION_SCREENSHOT=PASS",
        "INTERACTION_STATE=PASS",
        "VERTEX_SESSION_PORTAL_INTERACTION_PROBE_000014=PASS",
    ]

    missing = [
        marker
        for marker in expected
        if marker not in runtime.stdout
    ]

    if missing:
        print("MISSING_MARKERS=" + ",".join(missing))
        print("VERTEX_SESSION_PORTAL_INTERACTION_VERIFY_000014=FAIL")
        return 4

    evidence_root = (
        ROOT
        / "EVIDENCE"
        / "INTERACTION_PROBE_000014"
    )

    screenshot = (
        evidence_root
        / "interaction-persisted-vcr.png"
    )

    state_json = (
        evidence_root
        / "interaction-probe.json"
    )

    if not screenshot.exists() or screenshot.stat().st_size == 0:
        print("INTERACTION_SCREENSHOT_FILE=FAIL")
        print("VERTEX_SESSION_PORTAL_INTERACTION_VERIFY_000014=FAIL")
        return 5

    if not state_json.exists() or state_json.stat().st_size == 0:
        print("INTERACTION_JSON_FILE=FAIL")
        print("VERTEX_SESSION_PORTAL_INTERACTION_VERIFY_000014=FAIL")
        return 6

    print(f"INTERACTION_SCREENSHOT_EVIDENCE={screenshot}")
    print(f"INTERACTION_JSON_EVIDENCE={state_json}")
    print("INTERACTION_RUNTIME=PASS")
    print("VERTEX_SESSION_PORTAL_INTERACTION_VERIFY_000014=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
