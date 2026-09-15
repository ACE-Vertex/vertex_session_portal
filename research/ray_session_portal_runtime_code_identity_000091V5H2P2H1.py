from __future__ import annotations
from pathlib import Path
import json, subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

def safe(v: object) -> str:
    return str(v).encode("ascii", errors="backslashreplace").decode("ascii")

def emit(v: object) -> None:
    print(safe(v), flush=True)

def main() -> int:
    emit("=== SESSION PORTAL RUNTIME CODE IDENTITY RAY 000091V5H2P2H1 ===")
    emit("MODE=READ_ONLY")
    emit("EXIT_0=SOURCE_TREE_OR_OUT_BUILD")
    emit("EXIT_41=PACKAGED_OR_PORTABLE_EXE")
    emit("EXIT_42=NO_PORTAL_PROCESS_CANDIDATE")
    emit("EXIT_43=UNRESOLVED")

    src = ROOT / "src/main/vra/vra-dispatch-service.ts"
    built = ROOT / "out/main/index.js"

    source_has_h2 = src.is_file() and "EvidenceReturnObservabilityTap" in src.read_text(
        encoding="utf-8", errors="replace"
    )
    built_has_h2 = built.is_file() and "evidence-return-observability-tap-1" in built.read_text(
        encoding="utf-8", errors="replace"
    )

    emit(f"SOURCE_HAS_H2_TAP={'YES' if source_has_h2 else 'NO'}")
    emit(f"BUILT_MAIN_HAS_H2_TAP={'YES' if built_has_h2 else 'NO'}")

    query = (
        "$p = Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match 'electron|Vertex.*Session.*Portal|vertex-session-portal' "
        "-or $_.CommandLine -match 'vertex_session_portal|vertex-session-portal|Vertex.Session.Portal' "
        "}; "
        "$p | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3"
    )
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", query],
        text=True,
        capture_output=True,
        errors="replace",
        timeout=20,
        shell=False,
    )
    if p.returncode != 0:
        emit(f"POWERSHELL_EXIT={p.returncode}")
        return 43

    raw = p.stdout.strip()
    if not raw:
        emit("RUNTIME_IDENTITY=NO_PORTAL_PROCESS_CANDIDATE")
        return 42

    try:
        data = json.loads(raw)
    except Exception:
        emit("RUNTIME_IDENTITY=UNRESOLVED_JSON")
        return 43

    if isinstance(data, dict):
        data = [data]

    candidates = []
    for item in data:
        exe = str(item.get("ExecutablePath") or "")
        cmd = str(item.get("CommandLine") or "")
        name = str(item.get("Name") or "")
        text = (exe + " " + cmd + " " + name).lower()
        if (
            ("session" in text and "portal" in text)
            or "vertex_session_portal" in text
            or "vertex-session-portal" in text
        ):
            candidates.append(item)

    emit(f"PORTAL_PROCESS_CANDIDATES={len(candidates)}")
    if not candidates:
        emit("RUNTIME_IDENTITY=NO_PORTAL_PROCESS_CANDIDATE")
        return 42

    root_lower = str(ROOT).lower()
    built_lower = str(built).lower()
    source_runtime = False
    packaged_runtime = False

    for item in candidates:
        exe = str(item.get("ExecutablePath") or "")
        cmd = str(item.get("CommandLine") or "")
        joined = (exe + " " + cmd).lower()
        emit(f"PID={item.get('ProcessId')}")
        emit(f"EXE={exe}")
        emit(f"CMD={cmd}")

        if root_lower in joined or built_lower in joined:
            source_runtime = True
        elif exe.lower().endswith(".exe") and "electron.exe" not in exe.lower():
            packaged_runtime = True

    if source_runtime:
        emit("RUNTIME_IDENTITY=SOURCE_TREE_OR_OUT_BUILD")
        emit(f"H2_BUILD_MARKER={'PRESENT' if built_has_h2 else 'MISSING'}")
        return 0

    if packaged_runtime:
        emit("RUNTIME_IDENTITY=PACKAGED_OR_PORTABLE_EXE")
        return 41

    emit("RUNTIME_IDENTITY=UNRESOLVED")
    return 43

if __name__ == "__main__":
    raise SystemExit(main())
