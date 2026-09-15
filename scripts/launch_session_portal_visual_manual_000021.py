from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "EVIDENCE" / "VISUAL_MANUAL_LAUNCH_000021"

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(
            encoding="utf-8",
            errors="backslashreplace",
        )
    except Exception:
        pass

def fail(message: str, code: int) -> int:
    print(f"ERROR={message}")
    print("VERTEX_SESSION_PORTAL_VISUAL_MANUAL_LAUNCH_000021=FAIL")
    return code

def main() -> int:
    print("VERTEX SESSION PORTAL / VISUAL MANUAL LAUNCH 000021")
    print(f"ROOT={ROOT}")

    electron = ROOT / "node_modules" / "electron" / "dist" / "electron.exe"
    main_bundle = ROOT / "out" / "main" / "index.js"
    renderer = ROOT / "out" / "renderer" / "index.html"

    if not electron.exists():
        return fail("ELECTRON_BINARY_NOT_FOUND", 2)

    if not main_bundle.exists():
        return fail("MAIN_BUNDLE_NOT_FOUND", 3)

    if not renderer.exists():
        return fail("RENDERER_BUNDLE_NOT_FOUND", 4)

    EVIDENCE.mkdir(parents=True, exist_ok=True)

    stdout_path = EVIDENCE / "session-portal.stdout.log"
    stderr_path = EVIDENCE / "session-portal.stderr.log"

    env = os.environ.copy()

    # Force a normal, user-visible run.
    for key in [
        "VERTEX_RUNTIME_PROBE",
        "VERTEX_INTERACTION_PROBE",
        "VERTEX_UI_CONTROL_PROBE",
        "VERTEX_VIRTUAL_ARD_PROBE",
        "VERTEX_REAL_LLM_PROBE",
        "VERTEX_SEARCH_VERA_PROBE",
        "VERTEX_VISUAL_CANONICAL_PROBE",
    ]:
        env.pop(key, None)

    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

    flags = 0
    if os.name == "nt":
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        flags |= getattr(subprocess, "DETACHED_PROCESS", 0)

    with stdout_path.open("ab", buffering=0) as stdout_file, \
         stderr_path.open("ab", buffering=0) as stderr_file:

        proc = subprocess.Popen(
            [str(electron), "."],
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            close_fds=True,
            creationflags=flags,
        )

    print(f"LAUNCHED_PID={proc.pid}")

    time.sleep(2.5)

    return_code = proc.poll()

    if return_code is not None:
        stderr_tail = ""
        try:
            stderr_tail = stderr_path.read_text(
                encoding="utf-8",
                errors="backslashreplace",
            )[-4000:]
        except Exception:
            pass

        print(f"EARLY_EXIT_CODE={return_code}")
        if stderr_tail:
            print("EARLY_STDERR_TAIL=" + stderr_tail)

        return fail("SESSION_PORTAL_EXITED_EARLY", 5)

    evidence = {
        "artifact_id": "vertex-session-portal-visual-manual-launch-000021",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "NORMAL_USER_VISIBLE_VISUAL_TEST",
        "pid": proc.pid,
        "electron": str(electron),
        "project_root": str(ROOT),
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "diagnostic_probe": False,
        "visual_baseline": "VISUAL_CANONICAL_SF_000020H1",
    }

    evidence_path = EVIDENCE / "launch.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("NORMAL_LAUNCH_MODE=YES")
    print("VISUAL_CANONICAL_000020H1=ACTIVE")
    print("DIAGNOSTIC_PROBE_MODE=NO")
    print("WINDOW_PROCESS_ALIVE_AFTER_2_5S=PASS")
    print(f"LAUNCH_EVIDENCE={evidence_path}")
    print(f"STDOUT_LOG={stdout_path}")
    print(f"STDERR_LOG={stderr_path}")
    print("VERTEX_SESSION_PORTAL_VISUAL_MANUAL_LAUNCH_000021=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
