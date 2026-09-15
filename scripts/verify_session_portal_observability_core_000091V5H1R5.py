from __future__ import annotations

from pathlib import Path
import subprocess
import traceback
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
OBS = ROOT / "src" / "main" / "observability"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")


def ascii_safe(value: object) -> str:
    text = str(value)
    return text.encode("ascii", errors="backslashreplace").decode("ascii")

def emit(value: object) -> None:
    print(ascii_safe(value), flush=True)

REQUIRED = [
    OBS / "contracts.ts",
    OBS / "ray-core.ts",
    OBS / "sensor-core.ts",
    OBS / "judge-core.ts",
    OBS / "impact-core.ts",
    OBS / "guard-core.ts",
    OBS / "black-box.ts",
    OBS / "evidence-intelligence.ts",
    OBS / "observability-coordinator.ts",
    OBS / "index.ts",
    ROOT / "docs" / "ARCHITECTURE" / "OBSERVABILITY_CORE_000091V5H1.md",
]

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def check(name: str, ok: bool) -> bool:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def run_npm(*args: str) -> int:
    command = [str(NPM), *args]
    emit("RUN=" + " ".join(command))
    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            errors="replace",
            timeout=180,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        emit("NPM_TIMEOUT=180")
        if exc.stdout:
            emit("STDOUT_PARTIAL=" + str(exc.stdout)[-12000:])
        if exc.stderr:
            emit("STDERR_PARTIAL=" + str(exc.stderr)[-12000:])
        return 124
    except Exception as exc:
        emit(f"NPM_EXCEPTION={type(exc).__name__}:{exc}")
        emit(traceback.format_exc())
        return 125

    emit(f"EXIT={proc.returncode}")
    if proc.stdout:
        emit("STDOUT_TAIL=" + proc.stdout[-16000:].replace("\r", ""))
    if proc.stderr:
        emit("STDERR_TAIL=" + proc.stderr[-16000:].replace("\r", ""))
    return proc.returncode

def main() -> int:
    emit("=== VERTEX SESSION PORTAL / HIDDEN OBSERVABILITY CORE 000091V5H1R5 VERIFY ===")
    emit(f"ROOT={ROOT}")
    emit("MANIFEST_VERIFY_PROGRAM=PYTHON_ONLY")
    emit("NPM_EXECUTION=PYTHON_CHILD_DIRECT_NPM_CMD")
    emit("VERIFIER_OUTPUT_ENCODING=ASCII_BACKSLASHREPLACE")
    emit("HUMAN_UI_CHANGE=NONE")
    emit("RAY_MODE=READ_ONLY")
    emit("VRA_DISPATCH_SERVICE_MUTATION=NONE")
    emit("WORKSTATION_PRODUCTION_MUTATION=NONE")

    if not check("ROOT_PRESENT", ROOT.exists()):
        return 20
    if not check("NPM_PRESENT", NPM.exists()):
        return 24

    ok = True
    for path in REQUIRED:
        ok &= check("FILE_" + path.name.replace(".", "_").upper(), path.exists())
    if not ok:
        return 21

    try:
        ray = read(OBS / "ray-core.ts")
        guard = read(OBS / "guard-core.ts")
        evidence = read(OBS / "evidence-intelligence.ts")
        coord = read(OBS / "observability-coordinator.ts")
        index = read(OBS / "index.ts")

        forbidden_ray = [
            "writeFile(", "appendFile(", "rm(", "unlink(", "rename(",
            "child_process", "BrowserWindow", "webContents", "executeJavaScript"
        ]
        ok &= check("RAY_NO_WRITE_OR_EXEC_APIS", not any(token in ray for token in forbidden_ray))
        ok &= check("RAY_SCOPE_GUARD", "RAY_SCOPE_DENIED" in ray and "resolveScoped" in ray)
        ok &= check("RAY_DEEP_SCAN", "deepScan" in ray and "extractImports" in ray and "extractSymbols" in ray)
        ok &= check("RAY_CONTENT_SEARCH", "searchContent" in ray)
        ok &= check("RAY_HARD_BOUNDS", "HARD_MAX_NODES" in ray and "HARD_MAX_DEPTH" in ray)

        ok &= check("GUARD_RAY_READ_ONLY", "RAY_READ_ONLY_VIOLATION" in guard)
        ok &= check("GUARD_HUMAN_APPLY", "HUMAN_APPLY_AUTHORITY_REQUIRED" in guard and "HUMAN_APPROVAL_REQUIRED" in guard)
        ok &= check("GUARD_VERIFY_MUTATION_BLOCK", "VERIFY_SOURCE_MUTATION_FORBIDDEN" in guard)

        ok &= check("EVIDENCE_STDOUT_PATH", "stdout_path" in evidence)
        ok &= check("EVIDENCE_STDERR_PATH", "stderr_path" in evidence)
        ok &= check("COORDINATOR_LOG_HYDRATION", "commandLogPaths" in coord and "readText" in coord)
        ok &= check("COORDINATOR_JUDGE_LOOP", "observeEvidence" in coord and "judge.evaluate" in coord)
        ok &= check("BLACKBOX_EXPORTED", "black-box" in index)
        ok &= check(
            "NO_RENDERER_OBSERVABILITY_COMPONENT",
            not (ROOT / "src" / "renderer" / "src" / "components" / "Observability").exists()
        )
    except Exception as exc:
        emit(f"STATIC_EXCEPTION={type(exc).__name__}:{exc}")
        emit(traceback.format_exc())
        return 22

    if not ok:
        return 23

    typecheck = run_npm("run", "typecheck")
    if typecheck != 0:
        emit(f"TYPECHECK_FAILED_EXIT={typecheck}")
        return 30 if typecheck < 124 else typecheck

    build = run_npm("run", "build")
    if build != 0:
        emit(f"BUILD_FAILED_EXIT={build}")
        return 31 if build < 124 else build

    emit("OBSERVABILITY_CORE_FOUNDATION=PASS")
    emit("NEXT=H2_EVIDENCE_RETURN_BACKEND_WIRING")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        emit(f"VERIFIER_FATAL_EXCEPTION={type(exc).__name__}:{exc}")
        emit(traceback.format_exc())
        raise SystemExit(99)
