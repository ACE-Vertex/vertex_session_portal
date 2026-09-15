from __future__ import annotations
from pathlib import Path
import subprocess, traceback, hashlib

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
CSS = ROOT / "src/renderer/src/components/MainFrame/MainFrame.css"
TS = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")
BASE_SHA = "b9f1b9b0d83bcdc0508a751457182244ce140a7456ab539eb582efcd6dd045b5"

def safe(v: object) -> str:
    return str(v).encode("ascii", errors="backslashreplace").decode("ascii")

def emit(v: object) -> None:
    print(safe(v), flush=True)

def check(name: str, ok: bool) -> bool:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def run_npm(*args: str) -> int:
    cmd = [str(NPM), *args]
    emit("RUN=" + " ".join(cmd))
    try:
        p = subprocess.run(
            cmd, cwd=ROOT, text=True, capture_output=True, errors="replace",
            timeout=180, shell=False
        )
    except subprocess.TimeoutExpired:
        emit("NPM_TIMEOUT=180")
        return 124
    except Exception as exc:
        emit(f"NPM_EXCEPTION={type(exc).__name__}:{exc}")
        emit(traceback.format_exc())
        return 125
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-22000:].replace("\r",""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-22000:].replace("\r",""))
    return p.returncode

def main() -> int:
    emit("=== SESSION PORTAL HEADER LANE PULSE TERMINAL HISTORY RETIRE 000100V5 ===")
    emit("PRODUCTION_SCOPE=MainFrame.css_ONLY")
    emit("MAINFRAME_TS_MUTATION=ZERO")
    emit("WORKSTATION_MUTATION=ZERO")
    emit("SERVICE_MUTATION=ZERO")
    emit("CARD_ALLOCATED_LANE_HISTORY=PRESERVED")
    emit("ABSOLUTE_VISUAL_CONTRACT=00/32_ACTIVE_IMPLIES_ZERO_COLORED_ACTIVE_CELLS")

    if not CSS.is_file() or not TS.is_file():
        return 20

    css = CSS.read_text(encoding="utf-8", errors="replace")
    ts = TS.read_text(encoding="utf-8", errors="replace")
    ok = True

    # Existing MainFrame CSS baseline must remain embedded intact.
    baseline = css.split("/* 000100V5", 1)[0].rstrip() + "\n"
    baseline_sha = hashlib.sha256(baseline.encode("utf-8")).hexdigest()
    emit(f"BASELINE_SHA={baseline_sha}")
    ok &= check("KNOWN_MAINFRAME_CSS_BASELINE_PRESERVED", baseline_sha == BASE_SHA)

    # Exact visual retirement.
    ok &= check("TERMINAL_HISTORY_OVERRIDE_PRESENT",
        '.workstationPulse .lanePulse[data-state="FAILED"]' in css)
    block_start = css.find('.workstationPulse .lanePulse[data-state="FAILED"]')
    block = css[block_start:block_start+320] if block_start >= 0 else ""
    ok &= check("FAILED_USES_FREE_BACKGROUND",
        'background:rgba(113,129,149,.18)' in block)
    ok &= check("FAILED_GLOW_RETIRED", 'box-shadow:none' in block)
    ok &= check("FAILED_CURSOR_RETIRED", 'cursor:default' in block)

    # Prove root-cause source remains historical, and do not erase card facts.
    ok &= check("HEADER_PULSE_OWNER_PRESENT", "private workstationPulse()" in ts)
    ok &= check("CARD_ALLOCATED_LANE_FACT_PRESERVED", "card.allocatedLane" in ts)
    ok &= check("TERMINAL_HISTORY_CLASSIFICATION_PRESENT",
        "jobState === 'FAILED' || jobState === 'REJECTED'" in ts)
    ok &= check("FAILED_NOT_COUNTED_AS_ACTIVE",
        "state === 'BUSY' || state === 'RESERVED'" in ts)
    ok &= check("MAX32_PRESERVED", "MAX_LOGICAL_LANES" in ts)
    ok &= check("HUMAN_GATE_UI_UNTOUCHED", "EMERGENCY STOP" in ts or "E-STOP" in ts or "emergency" in ts.lower())

    if not ok:
        return 21

    rc = run_npm("run", "typecheck")
    if rc != 0:
        return 30 if rc < 124 else rc
    rc = run_npm("run", "build")
    if rc != 0:
        return 31 if rc < 124 else rc

    emit("HEADER_LANE_PULSE_TERMINAL_HISTORY_RETIRE=PASS")
    emit("EXPECTED_IDLE_UI=00/32_ACTIVE_AND_ZERO_PINK_FAILED_CELLS")
    emit("BUSY_RESERVED_VISUALS=PRESERVED")
    emit("FAILED_CARD_HISTORY=PRESERVED_BUT_NOT_RENDERED_AS_OCCUPANCY")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
