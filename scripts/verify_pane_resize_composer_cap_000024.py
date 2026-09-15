from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(
            encoding="utf-8",
            errors="backslashreplace",
        )
    except Exception:
        pass

def run(cmd, env=None, timeout=180):
    print("RUN=" + " ".join(map(str, cmd)))

    proc = subprocess.run(
        [str(x) for x in cmd],
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
        print(
            proc.stdout,
            end=""
            if proc.stdout.endswith("\n")
            else "\n",
        )

    if proc.stderr:
        print("=== STDERR ===")
        print(
            proc.stderr,
            end=""
            if proc.stderr.endswith("\n")
            else "\n",
        )

    print(f"EXIT_CODE={proc.returncode}")
    return proc

def resolve(name, fallback):
    candidate = Path(fallback)
    if candidate.exists():
        return str(candidate)

    found = shutil.which(name)
    if found:
        return found

    raise RuntimeError(
        f"{name}_NOT_FOUND"
    )

def ensure_electron(node):
    electron_dir = ROOT / "node_modules" / "electron"
    cli = electron_dir / "cli.js"
    exe = electron_dir / "dist" / "electron.exe"
    install = electron_dir / "install.js"

    if not cli.exists():
        raise RuntimeError(
            "ELECTRON_CLI_NOT_FOUND"
        )

    if not exe.exists():
        result = run(
            [node, install],
            timeout=240,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "ELECTRON_INSTALL_FAILED"
            )

    if not exe.exists():
        raise RuntimeError(
            "ELECTRON_BINARY_NOT_READY"
        )

    return str(cli)

def main():
    print(
        "VERTEX SESSION PORTAL / PANE RESIZE + COMPOSER CAP VERIFY 000024"
    )
    print(f"ROOT={ROOT}")

    npm = resolve(
        "npm.cmd",
        r"C:\Program Files\nodejs\npm.cmd",
    )

    node = resolve(
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
        print(
            "VERTEX_SESSION_PORTAL_PANE_COMPOSER_VERIFY_000024=FAIL"
        )
        return 2

    print("BUILD=PASS")

    env = os.environ.copy()
    env["VERTEX_PANE_COMPOSER_PROBE"] = "1"
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

    runtime = run(
        [node, electron_cli, "."],
        env=env,
        timeout=120,
    )

    if runtime.returncode != 0:
        print(
            "PANE_COMPOSER_000024_RUNTIME=FAIL"
        )
        print(
            "VERTEX_SESSION_PORTAL_PANE_COMPOSER_VERIFY_000024=FAIL"
        )
        return 3

    expected = [
        "PANE_COMPOSER_000024_TOPOLOGY=PASS",
        "PANE_COMPOSER_000024_NORMAL_DEFAULT_600=PASS",
        "PANE_COMPOSER_000024_PRIORITY_MIN_1200=PASS",
        "PANE_COMPOSER_000024_RESIZE_HANDLES=PASS",
        "PANE_COMPOSER_000024_MANUAL_RESIZE=PASS",
        "PANE_COMPOSER_000024_MANUAL_CLAMP_600=PASS",
        "PANE_COMPOSER_000024_RESIZE_RESET=PASS",
        "PANE_COMPOSER_000024_COMPOSER_MAX_115=PASS",
        "PANE_COMPOSER_000024_TEXTAREA_MAX_72=PASS",
        "PANE_COMPOSER_000024_CORE=PASS",
        "VERTEX_SESSION_PORTAL_PANE_COMPOSER_PROBE_000024=PASS",
    ]

    missing = [
        marker
        for marker in expected
        if marker not in runtime.stdout
    ]

    if missing:
        print(
            "MISSING_MARKERS="
            + ",".join(missing)
        )
        print(
            "VERTEX_SESSION_PORTAL_PANE_COMPOSER_VERIFY_000024=FAIL"
        )
        return 4

    print(
        "PANE_COMPOSER_000024_RUNTIME=PASS"
    )
    print(
        "VERTEX_SESSION_PORTAL_PANE_COMPOSER_VERIFY_000024=PASS"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
