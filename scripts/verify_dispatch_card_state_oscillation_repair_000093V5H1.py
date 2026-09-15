from __future__ import annotations
from pathlib import Path
import subprocess, traceback

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

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
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, errors="replace",
                           timeout=180, shell=False)
    except subprocess.TimeoutExpired:
        emit("NPM_TIMEOUT=180")
        return 124
    except Exception as exc:
        emit(f"NPM_EXCEPTION={type(exc).__name__}:{exc}")
        emit(traceback.format_exc())
        return 125
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-16000:].replace("\r",""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-16000:].replace("\r",""))
    return p.returncode

def main() -> int:
    emit("=== DISPATCH CARD STATE OSCILLATION REPAIR 000093V5H1 ===")
    emit("HUMAN_UI_MUTATION=NONE")
    emit("WORKSTATION_MUTATION=NONE")
    emit("HUMAN_GATE=UNCHANGED")
    emit("EXACT_ORIGIN=UNCHANGED")
    emit("OBSERVABILITY_H2=UNCHANGED")

    if not SERVICE.is_file():
        emit("SERVICE_FILE=FAIL")
        return 20

    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    ok = True
    ok &= check("REPAIR_MARKER", "000093V5H1: never expose a half-successful reconcile" in s)
    ok &= check("GET_JOB_PRESENT", "const response = await this.workstation.getJob(card.jobId)" in s)
    ok &= check("EVIDENCE_PICKUP_PRESENT", "if (evidenceNeedsPickup) await this.retrieveEvidence(card)" in s)

    get_pos = s.find("const response = await this.workstation.getJob(card.jobId)")
    pickup_pos = s.find("if (evidenceNeedsPickup) await this.retrieveEvidence(card)", get_pos)
    clear_pos = s.find("card.workstationLastError = null", get_pos)
    catch_pos = s.find("} catch (error) {", pickup_pos)

    ok &= check("ANCHOR_ORDER_VALID", -1 not in (get_pos, pickup_pos, clear_pos, catch_pos))
    ok &= check("ERROR_CLEAR_AFTER_EVIDENCE_PICKUP", pickup_pos < clear_pos < catch_pos)

    premature = s.find("card.workstationLastError = null", get_pos, pickup_pos)
    ok &= check("NO_PREMATURE_ERROR_CLEAR", premature == -1)

    ok &= check("PERSIST_AFTER_FULL_RECONCILE",
                "if (before !== this.workstationCardSyncKey(card)) this.persistCardState(card)" in s[clear_pos:catch_pos])
    ok &= check("CATCH_STICKY_ERROR_PRESERVED",
                "if (card.workstationLastError !== message)" in s[catch_pos:catch_pos+1200])
    ok &= check("OBSERVABILITY_TAP_PRESERVED",
                "await this.evidenceObservability.observeAndPersist({" in s)
    ok &= check("RAY_EVIDENCE_BRIDGE_PRESERVED",
                "000082V5 — Ray Evidence optic-nerve bridge." in s)
    ok &= check("ACK_HUMAN_GATE_PRESERVED",
                "EVIDENCE_ACK_HUMAN_PUBLISH_PRECONDITION_FAILED" in s)
    ok &= check("NO_DOM_SCRAPE",
                "executeJavaScript" not in s and "webContents.executeJavaScript" not in s)

    if not ok:
        return 21

    tc = run_npm("run", "typecheck")
    if tc != 0:
        return 30 if tc < 124 else tc

    build = run_npm("run", "build")
    if build != 0:
        return 31 if build < 124 else build

    emit("DISPATCH_CARD_OSCILLATION_REPAIR=PASS")
    emit("EXPECTED_RUNTIME=Persistent downstream failure stays red; successful full reconcile clears once.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
