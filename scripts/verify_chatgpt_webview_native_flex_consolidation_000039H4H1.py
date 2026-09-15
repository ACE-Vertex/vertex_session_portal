from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TS = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"
CSS = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css"
MAIN = ROOT / "src/renderer/src/components/MainFrame/MainFrame.css"

def emit(name, ok):
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def safe_ascii(text: str) -> str:
    return text.encode("ascii", errors="backslashreplace").decode("ascii")

def main():
    print("VERTEX SESSION PORTAL / CHATGPT WEBVIEW NATIVE FLEX CONSOLIDATION VERIFY 000039H4H1")
    print(f"ROOT={ROOT}")

    ts = TS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    main_css = MAIN.read_text(encoding="utf-8")

    m = re.search(r"\.chatgptView\s*\{(?P<body>.*?)\}", css, re.S)
    body = m.group("body") if m else ""
    compact = re.sub(r"\s+", "", body)

    checks = [
        emit("WEBVIEW_BLOCK_FOUND", m is not None),
        emit("WEBVIEW_NATIVE_DISPLAY_FLEX", "display:flex;" in compact),
        emit("WEBVIEW_DISPLAY_BLOCK_RETIRED", "display:block;" not in compact),
        emit("WEBVIEW_FLEX_FILL", "flex:11auto;" in compact),
        emit("WEBVIEW_WIDTH_100", "width:100%;" in compact),
        emit("WEBVIEW_HEIGHT_100", "height:100%;" in compact),
        emit("H2_RESIZE_OBSERVER_RETIRED", "ResizeObserver" not in ts),
        emit("H2_SYNC_METHODS_RETIRED",
             "syncBrowserViewport" not in ts and
             "scheduleBrowserViewportSync" not in ts and
             "startBrowserViewportSync" not in ts and
             "stopBrowserViewportSync" not in ts),
        emit("H2_INLINE_PIXEL_WRITES_RETIRED",
             "browser.style.width" not in ts and "browser.style.height" not in ts),
        emit("PERSIST_PARTITION_PRESERVED", "persist:vertex-vera-chatgpt" in ts),
        emit("THREAD_BRIDGE_PRESERVED", "updateVeraSessionThread" in ts),
        emit("VRA_DOWNLOAD_BRIDGE_PRESERVED", "registerVraWebviewSource" in ts),
        emit("NO_CHATGPT_DOM_SCRAPE", "executeJavaScript" not in ts),
        emit("MAIN_SESSION_TRACK_PRESERVED",
             ".sessionTrack" in main_css and
             re.search(r"\.sessionTrack\s*\{[^}]*height\s*:\s*100%", main_css, re.S) is not None),
    ]

    if not all(checks):
        print("VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_NATIVE_FLEX_CONSOLIDATION_000039H4H1=FAIL")
        raise SystemExit(1)

    print("RUN=npm.cmd run build")
    cp = subprocess.run(
        ["npm.cmd", "run", "build"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        check=False,
    )
    if cp.returncode != 0:
        print("BUILD=FAIL")
        decoded = cp.stdout.decode("utf-8", errors="backslashreplace")
        print(safe_ascii(decoded))
        raise SystemExit(cp.returncode)

    print("BUILD=PASS")
    print("WORKS_ALLOWED_VERIFICATION_PROGRAM=PYTHON_ONLY")
    print("SUBPROCESS_RAW_BYTES_DECODE_GUARD=PASS")
    print("VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_NATIVE_FLEX_CONSOLIDATION_000039H4H1=PASS")

if __name__ == "__main__":
    main()
