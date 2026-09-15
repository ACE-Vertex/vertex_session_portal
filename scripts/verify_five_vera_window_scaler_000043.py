from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "main": ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts",
    "browser": ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "scaler": ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.ts",
    "scaler_css": ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.css",
}

def text(name: str) -> str:
    path = FILES[name]
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")

def safe_emit(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if text is None:
        return
    value = str(text)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    safe = value.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
    stream.write(safe)
    if safe and not safe.endswith("\n"):
        stream.write("\n")
    stream.flush()

def check(name: str, ok: bool, failures: list[str]) -> None:
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def main() -> None:
    print("VERTEX SESSION PORTAL / FIVE VERA WINDOW SCALER VERIFY 000043")
    print(f"ROOT={ROOT}")

    failures: list[str] = []
    main_ts = text("main")
    browser_ts = text("browser")
    scaler_ts = text("scaler")
    scaler_css = text("scaler_css")

    check("SCALER_COMPONENT_PRESENT", bool(scaler_ts), failures)
    check("SCALER_STYLE_PRESENT", bool(scaler_css), failures)
    check(
        "MAINFRAME_SCALER_IMPORT",
        "import '../VeraWindowScaler/VeraWindowScaler'" in main_ts,
        failures,
    )
    check(
        "HEADER_SCALER_MOUNT",
        "<vertex-vera-window-scaler></vertex-vera-window-scaler>" in main_ts,
        failures,
    )
    check("DEFAULT_THREE_WINDOWS", "const MIN_COUNT = 3" in scaler_ts, failures)
    check("MAX_FIVE_WINDOWS", "const MAX_COUNT = 5" in scaler_ts, failures)
    check("HEADER_BUTTONS_3_4_5", "${[3, 4, 5].map" in scaler_ts, failures)
    check("VERA_04_DEFINED", "'vera-04'" in scaler_ts, failures)
    check("VERA_05_DEFINED", "'vera-05'" in scaler_ts, failures)
    check(
        "WINDOW_COUNT_PERSISTENCE",
        "vertex.portal.active-vera-count" in scaler_ts,
        failures,
    )
    check(
        "DYNAMIC_INSERT_BEFORE_VRA_LANE",
        "track.insertBefore(pane, dispatchLane)" in scaler_ts,
        failures,
    )
    check(
        "VRA_DISPATCH_LANE_PRESERVED",
        "<vertex-vra-dispatch-lane" in main_ts,
        failures,
    )
    check("SEARCH_VERA_STAYS_RETIRED", "<search-vera" not in main_ts, failures)
    check(
        "RELAY_FIVE_IDS",
        "['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05']" in browser_ts,
        failures,
    )
    check("RELAY_REGEX_1_TO_5", "([12345])" in browser_ts, failures)
    check(
        "NO_BROWSER_DOM_SCRAPE_ADDED",
        "executeJavaScript" not in scaler_ts and "webview" not in scaler_ts.lower(),
        failures,
    )

    if failures:
        print("STATIC_FAILURES=" + ",".join(failures))
        raise SystemExit(2)

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
    print(f"BUILD_EXIT={result.returncode}")
    check("BUILD", result.returncode == 0, failures)

    if failures:
        raise SystemExit(3)

    print("VERTEX_SESSION_PORTAL_FIVE_VERA_WINDOW_SCALER_000043=PASS")

if __name__ == "__main__":
    main()
