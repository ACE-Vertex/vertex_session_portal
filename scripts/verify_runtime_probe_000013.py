from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

def run(cmd: list[str], env: dict[str, str] | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    print("RUN=" + " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
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
    candidates = [
        Path(r"C:\Program Files\nodejs\npm.cmd"),
        Path(r"C:\Program Files\nodejs\npm.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    from shutil import which
    resolved = which("npm.cmd") or which("npm")

    if resolved:
        return resolved

    raise RuntimeError("NPM_NOT_FOUND")

def find_electron() -> str:
    candidates = [
        ROOT / "node_modules" / "electron" / "dist" / "electron.exe",
        ROOT / "node_modules" / ".bin" / "electron.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise RuntimeError("ELECTRON_EXE_NOT_FOUND")

def main() -> int:
    print("VERTEX SESSION PORTAL / RUNTIME PROBE VERIFY 000013")
    print(f"ROOT={ROOT}")

    required = [
        ROOT / "src" / "main" / "diagnostics" / "runtime-probe.ts",
        ROOT / "src" / "main" / "index.ts",
        ROOT / "package.json",
    ]

    missing = [str(path) for path in required if not path.exists()]

    if missing:
        print("MISSING=" + ",".join(missing))
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013=FAIL")
        return 2

    npm = find_npm()
    electron = find_electron()

    build = run([npm, "run", "build"], timeout=180)

    if build.returncode != 0:
        print("BUILD=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013=FAIL")
        return 3

    print("BUILD=PASS")

    env = os.environ.copy()
    env["VERTEX_RUNTIME_PROBE"] = "1"
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

    runtime = run([electron, "."], env=env, timeout=60)

    if runtime.returncode != 0:
        print("RUNTIME=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013=FAIL")
        return 4

    expected = [
        "RENDERER_LOAD=PASS",
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

    missing_markers = [marker for marker in expected if marker not in runtime.stdout]

    if missing_markers:
        print("MISSING_MARKERS=" + ",".join(missing_markers))
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013=FAIL")
        return 5

    evidence_root = ROOT / "EVIDENCE" / "RUNTIME_PROBE_000013"
    screenshot = evidence_root / "session-portal-runtime.png"
    runtime_json = evidence_root / "runtime-probe.json"

    if not screenshot.exists() or screenshot.stat().st_size == 0:
        print("SCREENSHOT_EVIDENCE=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013=FAIL")
        return 6

    if not runtime_json.exists() or runtime_json.stat().st_size == 0:
        print("RUNTIME_JSON_EVIDENCE=FAIL")
        print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013=FAIL")
        return 7

    print(f"SCREENSHOT_EVIDENCE={screenshot}")
    print(f"RUNTIME_JSON_EVIDENCE={runtime_json}")
    print("RUNTIME=PASS")
    print("VERTEX_SESSION_PORTAL_RUNTIME_VERIFY_000013=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
