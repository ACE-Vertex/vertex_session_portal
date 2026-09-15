from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT.parent

FILES = {
    "mainframe": ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts",
    "mainframe_css": ROOT / "src/renderer/src/components/MainFrame/MainFrame.css",
    "browser": ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "browser_css": ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css",
    "scaler_css": ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.css",
    "explorer_css": ROOT / "src/renderer/src/components/Explorer/Explorer.css",
    "dispatch_css": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css",
    "destination": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchDestinationControl.ts",
    "main": ROOT / "src/main/index.ts",
}

CSS_MARKER = "VERTEX_SESSION_PORTAL_MOCK_FIDELITY_000049_BEGIN"


def safe_emit(value, stream=None):
    stream = stream or sys.stdout
    if value is None:
        return
    enc = getattr(stream, "encoding", None) or "utf-8"
    text = str(value).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(text)
    if text and not text.endswith("\n"):
        stream.write("\n")
    stream.flush()


def text(name: str) -> str:
    path = FILES[name]
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def check(name: str, ok: bool, failures: list[str]) -> None:
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)


def run_python(script: str, failures: list[str], label: str) -> None:
    path = ROOT / script
    if not path.exists():
        print(f"{label}=SKIP_MISSING:{path}")
        failures.append(label)
        return
    print(f"RUN={sys.executable} {script}")
    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    safe_emit(result.stdout, sys.stdout)
    if result.stderr:
        safe_emit(result.stderr, sys.stderr)
    check(label, result.returncode == 0, failures)


def run_build(failures: list[str]) -> None:
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    print(f"RUN={npm} run build")
    result = subprocess.run(
        [npm, "run", "build"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    safe_emit(result.stdout, sys.stdout)
    if result.stderr:
        safe_emit(result.stderr, sys.stderr)
    check("SOURCE_BUILD", result.returncode == 0, failures)


def main() -> None:
    print("=== VERTEX SESSION PORTAL / MOCK FIDELITY + STREAM STABILITY VERIFY 000049 ===")
    print(f"ROOT={ROOT}")

    failures: list[str] = []
    mainframe = text("mainframe")
    browser = text("browser")
    main_ts = text("main")
    destination = text("destination")

    # UI / brand fidelity.
    check("VERTEX_BRAND_MARK", 'class="brandMark"' in mainframe, failures)
    check("SESSION_PORTAL_TITLE_CASE", '<span class="product">Session Portal</span>' in mainframe, failures)
    check("PRIMARY_ENTRY_BADGE", 'class="primaryEntry"' in mainframe and "PRIMARY ENTRY" in mainframe, failures)
    check("MAINFRAME_FIDELITY_CSS", CSS_MARKER in text("mainframe_css"), failures)
    check("EXPLORER_FIDELITY_CSS", CSS_MARKER in text("explorer_css"), failures)
    check("DISPATCH_FIDELITY_CSS", CSS_MARKER in text("dispatch_css"), failures)
    check("SCALER_FIDELITY_CSS", CSS_MARKER in text("scaler_css"), failures)
    check("BROWSER_FIDELITY_CSS", CSS_MARKER in text("browser_css"), failures)

    # VERA 04 / 05 must no longer expose Human-assigned assignment chrome.
    check(
        "VERA_04_05_ASSIGNMENT_GATED",
        "session.id !== 'vera-04' && session.id !== 'vera-05'" in mainframe,
        failures,
    )
    check(
        "VERA_04_05_OBJECTIVE_GATED",
        "const objective = assignmentChrome && this.state.virtualArd" in mainframe,
        failures,
    )
    check(
        "INDEPENDENT_HUMAN_ASSIGNED_LITERAL_RETIRED",
        "INDEPENDENT VERA · Human assigned session" not in mainframe
        and "INDEPENDENT VERA · Human assigned session" not in browser,
        failures,
    )

    # Dispatch Bay full destination setting, backed by existing 000046H2 bridge.
    check("DISPATCH_DESTINATION_IMPORT", "VraDispatchDestinationControl" in mainframe, failures)
    check("DISPATCH_VRA_SAVE_PATH_VISIBLE", "VRA Save Path" in destination, failures)
    check("DISPATCH_DESTINATION_BRIDGE", "vertexDispatchDestination" in destination, failures)
    check("DISPATCH_DESTINATION_CHOOSER", "await bridge.choose()" in destination, failures)
    check("DISPATCH_DESTINATION_PANEL", "data-vra-dispatch-destination-panel" in destination, failures)
    # Preserve 000047's legacy source-marker contract while replacing the old gear-only UI.
    check(
        "PUBLISH_000047_COMPAT_MARKER",
        "reload.insertAdjacentElement('afterend', button)" in destination,
        failures,
    )

    # Five-webview stream stability and explicit hard recovery without ChatGPT DOM scraping.
    check("WEBVIEW_RELOAD_IGNORING_CACHE", "reloadIgnoringCache" in browser, failures)
    check("WEBVIEW_STOP_CONTROL", "browser.stop()" in browser, failures)
    check("WEBVIEW_RECOVER_BUTTON", 'data-action="recover"' in browser, failures)
    check("WEBVIEW_UNRESPONSIVE_EVENT", "addEventListener('unresponsive'" in browser, failures)
    check("WEBVIEW_RENDER_PROCESS_GONE_EVENT", "addEventListener('render-process-gone'" in browser, failures)
    check("DISABLE_RENDERER_BACKGROUNDING", "disable-renderer-backgrounding" in main_ts, failures)
    check("DISABLE_BACKGROUND_TIMER_THROTTLING", "disable-background-timer-throttling" in main_ts, failures)
    check("DISABLE_OCCLUDED_WINDOW_BACKGROUNDING", "disable-backgrounding-occluded-windows" in main_ts, failures)
    check("MAIN_WINDOW_BACKGROUND_THROTTLING_OFF", "backgroundThrottling: false" in main_ts, failures)
    check("WEBVIEW_BACKGROUND_THROTTLING_OFF", "webPreferences.backgroundThrottling = false" in main_ts, failures)
    check("NO_CHATGPT_DOM_SCRAPE", "executeJavaScript" not in browser, failures)

    # Preserve the current five-window and Dispatch Bay foundations.
    check("FIVE_WINDOW_SCALER_MOUNT", "<vertex-vera-window-scaler></vertex-vera-window-scaler>" in mainframe, failures)
    check("VRA_DISPATCH_LANE_MOUNT", "<vertex-vra-dispatch-lane" in mainframe, failures)
    check("SEARCH_VERA_RETIRED", "<search-vera" not in mainframe, failures)

    if failures:
        print("STATIC_FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    run_build(failures)
    if failures:
        print("BUILD_FAILURES=" + ",".join(failures))
        raise SystemExit(3)

    # Do not create another launcher. Rebuild/publish through the existing canonical
    # Workstation latest entry established by 000047.
    run_python("scripts/publish_latest_to_vertex_workstation_000047.py", failures, "PUBLISH_CANONICAL_LATEST")
    run_python("scripts/verify_workstation_latest_session_portal_000047.py", failures, "VERIFY_CANONICAL_LATEST")

    launcher = DEV / "vertex_workstation" / "START_SESSION_PORTAL_LATEST.cmd"
    latest_exe = DEV / "vertex_workstation" / "SESSION_PORTAL_LATEST" / "Vertex Session Portal.exe"
    check("PRIMARY_ENTRY_LAUNCHER_PRESENT", launcher.exists(), failures)
    check("PRIMARY_ENTRY_EXE_PRESENT", latest_exe.exists(), failures)

    if launcher.exists():
        launcher_text = launcher.read_text(encoding="utf-8", errors="replace")
        check("PRIMARY_ENTRY_POINTS_TO_LATEST", "SESSION_PORTAL_LATEST\\Vertex Session Portal.exe" in launcher_text, failures)

    if failures:
        print("FAILURES=" + ",".join(failures))
        raise SystemExit(4)

    print(f"PRIMARY_ENTRY={launcher}")
    print(f"LATEST_EXE={latest_exe}")
    print("MANUAL_CHAT_ACCEPTANCE=SEND_2_PLUS_MESSAGES_PER_LANE_AND_CANCEL_RECOVERY")
    print("VERTEX_SESSION_PORTAL_MOCK_FIDELITY_STABILITY_000049=PASS")


if __name__ == "__main__":
    main()
