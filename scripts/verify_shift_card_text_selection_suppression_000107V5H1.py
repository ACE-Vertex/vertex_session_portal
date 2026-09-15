from __future__ import annotations
from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
FILE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
NPM = Path(r"C:\Program Files\nodejs\npm.cmd")

def emit(value):
    print(str(value).encode("ascii", errors="backslashreplace").decode("ascii"), flush=True)

def check(name, ok):
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def run_npm(*args):
    p = subprocess.run(
        [str(NPM), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        errors="replace",
        timeout=240,
        shell=False,
    )
    emit(f"EXIT={p.returncode}")
    if p.stdout:
        emit("STDOUT_TAIL=" + p.stdout[-18000:].replace("\r", ""))
    if p.stderr:
        emit("STDERR_TAIL=" + p.stderr[-18000:].replace("\r", ""))
    return p.returncode

def section(text, start, end):
    a = text.find(start)
    if a < 0:
        return ""
    b = text.find(end, a + len(start))
    return text[a:] if b < 0 else text[a:b]

def main():
    emit("=== SHIFT CARD TEXT SELECTION SUPPRESSION 000107V5H1 ===")
    emit("SOURCE_CHANGE=BYTE_EQUIVALENT_TO_000107V5")
    emit("VERIFIER_FIX=QUEUE_OWNER_ORDER_ONLY")

    if not FILE.is_file():
        return 20

    t = FILE.read_text(encoding="utf-8", errors="replace")
    bind = section(t, "  private bind(): void {", "    queue?.addEventListener('dragstart'")

    queue_down = "queue?.addEventListener('mousedown', event => {"
    queue_click = "queue?.addEventListener('click', event => {"

    ok = True
    ok &= check("MOUSEDOWN_OWNER_PRESENT", queue_down in bind)
    ok &= check("QUEUE_CLICK_OWNER_PRESENT", queue_click in bind)
    ok &= check("QUEUE_MOUSEDOWN_PRECEDES_QUEUE_CLICK",
        bind.find(queue_down) >= 0
        and bind.find(queue_click) >= 0
        and bind.find(queue_down) < bind.find(queue_click))
    ok &= check("SHIFT_ONLY",
        "if (!mouse.shiftKey || mouse.button !== 0) return" in bind)
    ok &= check("CARD_BODY_ONLY",
        "target?.closest('button, summary, details, .cardDetails, .cardActions')" in bind
        and "target?.closest<HTMLElement>('.vraCard')" in bind)
    ok &= check("NATIVE_SELECTION_SUPPRESSED",
        "mouse.preventDefault()" in bind
        and "window.getSelection()?.removeAllRanges()" in bind)
    ok &= check("SHIFT_RANGE_LOGIC_PRESERVED",
        "this.selectCard(cardId, mouse.shiftKey)" in bind
        and "if (mouse.shiftKey) mouse.preventDefault()" in bind)
    ok &= check("NORMAL_SELECTION_NOT_GLOBALLY_DISABLED",
        "user-select: none" not in t
        and "selectstart" not in bind)
    ok &= check("INTERACTIVE_CONTROLS_PRESERVED",
        "if (target?.closest('.cardDetails, .cardActions')) return" in bind)
    ok &= check("ARD_000106_PRESERVED",
        "AUTO_DISPATCH_COMMAND_PREFIX" in t
        and "routeAutoAuthorizedCards" in t)
    ok &= check("ONE_CLICK_000104_PRESERVED",
        "void this.dispatch(cardId)" in t
        and 'data-role="dispatch-dialog"' not in t)
    ok &= check("TEST_ONLY_RERUN_PRESERVED",
        "if (!this.explicitTestCard(card)) return ''" in t)

    if not ok:
        return 21

    emit("RUN=npm run typecheck")
    rc = run_npm("run", "typecheck")
    if rc != 0:
        return 30

    emit("RUN=npm run build")
    rc = run_npm("run", "build")
    if rc != 0:
        return 31

    emit("SHIFT_CARD_TEXT_SELECTION_SUPPRESSION=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
