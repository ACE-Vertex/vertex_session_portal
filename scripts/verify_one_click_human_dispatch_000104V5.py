from __future__ import annotations
from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def emit(v):
    print(str(v).encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)

def check(name, ok):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def section(text, start, end):
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:] if b < 0 else text[a:b]

def run(*args):
    p = subprocess.run(
        [str(NPM), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        errors="replace",
        timeout=180,
        shell=False,
    )
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-16000:].replace("\r",""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-16000:].replace("\r",""))
    return p.returncode

def main():
    emit("=== SESSION PORTAL ONE CLICK HUMAN DISPATCH 000104V5 ===")
    if not LANE.is_file() or not SERVICE.is_file():
        return 20

    r = LANE.read_text(encoding="utf-8", errors="replace")
    s = SERVICE.read_text(encoding="utf-8", errors="replace")
    request = section(r, "  private requestDispatch(", "  private async dispatch(")

    ok = True
    ok &= check("BUTTON_REMAINS_HUMAN_GATE",
        'data-action="dispatch"' in r and 'data-human-gate="APPROVE + DISPATCH"' in r)
    ok &= check("ONE_CLICK_DIRECT_DISPATCH",
        "void this.dispatch(cardId)" in request)
    ok &= check("SECOND_CONFIRM_DIALOG_RETIRED",
        'data-role="dispatch-dialog"' not in r
        and 'data-action="dispatch-confirm"' not in r
        and 'data-action="dispatch-cancel"' not in r
        and "工場へ発注しますか？" not in r)
    ok &= check("PENDING_DISPATCH_DIALOG_STATE_RETIRED",
        "pendingDispatchCardId" not in r
        and "closeDispatchDialog" not in r
        and "confirmDispatch" not in r)
    ok &= check("REMOVE_CONFIRMATION_UNCHANGED",
        'data-role="remove-dialog"' in r
        and 'data-action="remove-confirm"' in r)
    ok &= check("BUSY_GUARD_PRESERVED",
        "if (this.busyCardId) return" in request
        and "this.busyAction = 'dispatch'" in r)
    ok &= check("SAFETY_BLOCK_PRESERVED",
        "const blocked = this.workstationDispatchBlockReason()" in r)
    ok &= check("MAIN_HUMAN_APPROVAL_PRESERVED",
        "card.humanApproval = 'APPROVED'" in s)
    ok &= check("ATOMIC_PUBLISH_PRESERVED",
        "publishToIncomingAtomic" in s)
    ok &= check("TEST_RERUN_GATE_000102_PRESERVED",
        "VRA_TEST_RERUN_NON_TEST_DENIED" in s
        and "card.cardKind === 'TEST'" in r)
    ok &= check("NO_AUTO_APPLY_NEW_PATH",
        "dispatchVraCard(cardId)" in r)
    if not ok:
        return 21

    emit("RUN=npm run typecheck")
    rc = run("run", "typecheck")
    if rc != 0:
        return 30

    emit("RUN=npm run build")
    rc = run("run", "build")
    if rc != 0:
        return 31

    emit("ONE_CLICK_HUMAN_DISPATCH=PASS")
    emit("HUMAN_GATE=PHYSICAL_DISPATCH_BUTTON_CLICK")
    emit("SECOND_CONFIRMATION=RETIRED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
