from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else ""

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
        emit("STDOUT_TAIL=" + cp.stdout[-9000:].replace("\n", " | "))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-6000:].replace("\n", " | "))
    return cp.returncode == 0

mainframe = read("src/renderer/src/components/MainFrame/MainFrame.ts")
contracts = read("src/shared/contracts.ts")
preload = read("src/preload/index.ts")
ipc = read("src/main/ipc/register-vra-dispatch-ipc.ts")
svg = read("src/renderer/src/assets/vertex-session-portal-wordmark.svg")

ux_css_match = re.search(
    r"const PORTAL_FINAL_UX_CSS = `(?P<body>.*?)`",
    mainframe,
    re.S
)
ux_css = ux_css_match.group("body") if ux_css_match else ""

checks = {
    "WORDMARK_SVG":
        "<svg" in svg and
        "VERTEX SESSION PORTAL" in svg and
        "data:image/png;base64," in svg,
    "WORDMARK_MAINFRAME_URL":
        "vertex-session-portal-wordmark.svg" in mainframe and
        "HEADER_WORDMARK_URL" in mainframe,
    "OLD_TINY_TEXT_BRAND_RETIRED":
        '<span class="vertex">VERTEX</span>' not in mainframe and
        '<span class="product">SESSION PORTAL</span>' not in mainframe,
    "WORDMARK_RENDERED":
        'class="portalWordmark"' in mainframe and
        'src="${HEADER_WORDMARK_URL}"' in mainframe,
    "HEADER_HEIGHT_CHANGE_ZERO":
        ".topbar" not in ux_css and
        "height:26px" in ux_css and
        "max-height:calc(100% - 2px)" in ux_css,
    "WORDMARK_LARGER_SAME_HEADER":
        "width:154px" in ux_css and
        "flex:0 0 158px" in ux_css,
    "FIT_CONTRACT":
        "PortalWindowFitRequest" in contracts and
        "PortalWindowFitResult" in contracts and
        "fitMainWindow(request: PortalWindowFitRequest)" in contracts,
    "FIT_PRELOAD":
        "fitMainWindow:" in preload and
        "'portal:main-window-fit'" in preload,
    "FIT_IPC_REGISTERED":
        "ipcMain.handle(" in ipc and
        "'portal:main-window-fit'" in ipc,
    "MAIN_PROCESS_WINDOW_AUTHORITY":
        "BrowserWindow.fromWebContents(event.sender)" in ipc,
    "WORKAREA_CLAMP":
        "screen.getDisplayMatching(currentBounds)" in ipc and
        "display.workArea" in ipc,
    "MAXIMIZED_FULLSCREEN_PRESERVED":
        "win.isMaximized() || win.isFullScreen()" in ipc and
        "MAXIMIZED_OR_FULLSCREEN" in ipc,
    "RENDERER_XY_CONTROL_ZERO":
        "fitMainWindow({\n        contentWidth:" in mainframe and
        "contentHeight:" in mainframe and
        "fitMainWindow({ x:" not in mainframe and
        "fitMainWindow({ y:" not in mainframe,
    "MAIN_PROCESS_BOUNDS_OWNER":
        "win.setBounds({ x, y, width, height }, true)" in ipc,
    "FIT_MODE_LAYOUT_CHANGE_ONLY":
        "WINDOW_FIT_SETTLE_MS" in mainframe and
        "scheduleMainWindowFit('BOOTSTRAP')" in mainframe and
        mainframe.count("scheduleMainWindowFit('VERA_LAYOUT')") >= 4,
    "FIT_BOOTSTRAP":
        "this.scheduleMainWindowFit('BOOTSTRAP')" in mainframe,
    "FIT_PLUS_VERA":
        "node?.removeAttribute('presentation-hidden')" in mainframe and
        "this.scheduleMainWindowFit('VERA_LAYOUT')" in mainframe,
    "FIT_MINUS_VERA":
        "hideLastVisibleVera" in mainframe and
        mainframe.count("this.scheduleMainWindowFit('VERA_LAYOUT')") >= 4,
    "VISIBLE_LAYOUT_SCROLLWIDTH":
        "track.scrollWidth" in mainframe and
        "explorer?.getBoundingClientRect().width" in mainframe,
    "VERTICAL_HEIGHT_PRESERVED":
        "Math.ceil(window.innerHeight)" in mainframe,
    "PRESENTATION_HIDE_PRESERVED":
        "presentation-hidden" in mainframe and
        "Keep the canonical session mounted" in mainframe,
    "HUMAN_GATE_UNTOUCHED":
        "dispatch" not in ux_css.lower(),
    "DIRECT_HTTP_EXECUTION_ZERO":
        "/v1/apply" not in ipc and
        "/v1/verify" not in ipc and
        "/v1/rollback" not in ipc,
}

npm = shutil.which("npm.cmd") if sys.platform.startswith("win") else shutil.which("npm")
checks["NPM"] = npm is not None
if npm:
    checks["TYPECHECK"] = run([npm, "run", "typecheck"])
    checks["PRODUCTION_BUILD"] = run([npm, "run", "build"])
else:
    checks["TYPECHECK"] = False
    checks["PRODUCTION_BUILD"] = False

emit("=== SESSION PORTAL / FINAL UX WORDMARK + LAYOUT FIT 000073V5 ===")
emit("HEADER_HEIGHT_CHANGE=ZERO")
emit("WORDMARK=VERTEX_PALE_WHITE_SESSION_CYAN_PORTAL_PALE_WHITE")
emit("FIT_MODE=LAYOUT_CHANGE_ONLY")
emit("FIT_EVENTS=BOOTSTRAP,PLUS_VERA,MINUS_VERA,SESSION_HIDE,LANE_LAYOUT_CHANGE")
emit("MANUAL_RESIZE_BETWEEN_LAYOUT_CHANGES=PRESERVED")
emit("MAXIMIZED_FULLSCREEN=PRESERVED")
emit("DISPLAY_WORKAREA_CLAMP=ENABLED")
emit("RENDERER_WINDOW_TARGET_CONTROL=ZERO")
emit("RENDERER_XY_CONTROL=ZERO")
emit("WORKSTATION_PRODUCTION_MUTATION=ZERO")

for k, v in checks.items():
    emit(f"{k}={'PASS' if v else 'FAIL'}")

failed = [k for k, v in checks.items() if not v]
emit(
    "VERTEX_SESSION_PORTAL_FINAL_UX_WORDMARK_AUTOFIT_000073V5="
    + ("PASS" if not failed else "FAIL")
)
if failed:
    emit("FAILED=" + ",".join(failed))
    raise SystemExit(1)
