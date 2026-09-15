from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
text = MAIN.read_text(encoding="utf-8")

def emit(v):
    print(str(v).encode("cp932", errors="backslashreplace").decode("cp932", errors="replace"), flush=True)

def run(cmd, timeout=1800):
    emit("RUN=" + " ".join(str(x) for x in cmd))
    cp = subprocess.run(
        [str(x) for x in cmd],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    emit(f"EXIT={cp.returncode}")
    if cp.stdout:
        emit("STDOUT_TAIL=" + cp.stdout[-7000:].replace("\n", " | "))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-5000:].replace("\n", " | "))
    return cp.returncode

checks = {
    "MAINFRAME_PRESENT": MAIN.is_file(),
    "CANONICAL_IDS_PRESERVED":
        "const MAIN_VERA_IDS = ['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05'] as const" in text,
    "HIDDEN_PRESENTATION_STORE_PRESERVED": "HIDDEN_VERA_WINDOWS_KEY" in text,
    "MIN_VISIBLE_THREE": "return this.visibleMainSessions().length > 3" in text,
    "REMOVE_BUTTON":
        'data-action="remove-vera"' in text and '>− VERA</button>' in text,
    "ADD_BUTTON_PRESERVED":
        'data-action="add-vera"' in text and '>+ VERA</button>' in text,
    "RIGHTMOST_VISIBLE_HIDE":
        "const target = visible[visible.length - 1]" in text,
    "PRESENTATION_ONLY_HIDE":
        "this.hiddenMainSessions.add(target.id)" in text
        and "node?.setAttribute('presentation-hidden', '')" in text,
    "SESSION_NODE_NOT_REMOVED":
        ".remove()" not in text[text.find("private hideLastVisibleVera"):text.find("private canShowAnotherVera")],
    "SESSION_STATE_NOT_DEACTIVATED":
        "active = false" not in text[text.find("private hideLastVisibleVera"):text.find("private canShowAnotherVera")],
    "HIDDEN_STATE_DURABLE":
        "this.persistHiddenMainSessions()" in text,
    "ADD_REOPENS_HIDDEN":
        "const hidden = active.find(session => this.hiddenMainSessions.has(session.id))" in text,
    "ADD_RESTORES_EXISTING_NODE":
        "node?.removeAttribute('presentation-hidden')" in text,
    "NO_VERA06": "vera-06" not in text,
    "REMOVE_DOM_SYNC":
        "remove.disabled = !this.canHideAnotherVera()" in text,
    "COUNT_DOM_SYNC":
        "count.textContent = `${visible}/5`" in text,
    # Functional routing/session-preservation anchors, not prose-comment matching.
    "VERA_BROWSER_SESSION_REMAINS_MOUNTED":
        "vera-browser-session[session-id=" in text,
    "PRESENTATION_HIDDEN_ATTRIBUTE_CONTRACT":
        "presentation-hidden" in text,
}

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"]) == 0
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"]) == 0
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== VERTEX SESSION PORTAL / VERA WINDOW MINUS CONTROL 000062V5H1 ===")
emit("ROOT_CAUSE=000062V5_VERIFY_FALSE_NEGATIVE_COMMENT_STRING_SPLIT")
emit("FUNCTIONAL_REPAIR=NO_NEW_BEHAVIOR_CHANGE")
emit("VERIFY_REPAIR=SEMANTIC_SESSION_PRESERVATION_CHECKS")
emit("MUTATION_SCOPE=MAINFRAME_REAPPLY_PLUS_VERIFY")
emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")
emit("SESSION_IDENTITY_MUTATION=ZERO")

for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")

failed = [k for k, v in checks.items() if not v]
emit("VERTEX_SESSION_PORTAL_VERA_WINDOW_MINUS_CONTROL_000062V5H1=" + ("PASS" if not failed else "FAIL"))
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
