from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.css"
TS = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"
MAIN_CSS = ROOT / "src/renderer/src/components/MainFrame/MainFrame.css"

def report(name: str, ok: bool) -> bool:
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def ascii_safe(text: str) -> str:
    return text.encode("ascii", errors="backslashreplace").decode("ascii")

def main() -> None:
    print("VERTEX SESSION PORTAL / CHATGPT WEBVIEW INTERNAL FLEX REPAIR VERIFY 000039H3H3")
    print(f"ROOT={ROOT}")

    css = CSS.read_text(encoding="utf-8")
    ts = TS.read_text(encoding="utf-8")
    main_css = MAIN_CSS.read_text(encoding="utf-8")

    m = re.search(r"\.chatgptView\s*\{(?P<body>.*?)\}", css, flags=re.S)
    body = m.group("body") if m else ""
    compact = re.sub(r"\s+", "", body)

    checks = []
    checks.append(report("WEBVIEW_DISPLAY_FLEX", "display:flex;" in compact))
    checks.append(report("WEBVIEW_DISPLAY_BLOCK_RETIRED", "display:block;" not in compact))
    checks.append(report("WEBVIEW_WIDTH_100_PRESERVED", "width:100%;" in compact))
    checks.append(report("WEBVIEW_HEIGHT_100_PRESERVED", "height:100%;" in compact))
    checks.append(report("WEBVIEW_FLEX_FILL_PRESERVED", "flex:11auto;" in compact))
    checks.append(report("H2_RESIZE_OBSERVER_PRESERVED", "ResizeObserver" in ts))
    checks.append(report(
        "H2_EXACT_PIXEL_SYNC_PRESERVED",
        "getBoundingClientRect" in ts and
        "style.width" in ts and
        "style.height" in ts
    ))
    checks.append(report(
        "MAIN_HEIGHT_CHAIN_PRESERVED",
        ".sessionTrack" in main_css and "height: 100%" in main_css
    ))
    checks.append(report("PERSIST_PARTITION_PRESERVED", "persist:vertex-vera-chatgpt" in ts))
    checks.append(report("THREAD_BRIDGE_PRESERVED", "updateVeraSessionThread" in ts))
    checks.append(report("VRA_DOWNLOAD_BRIDGE_PRESERVED", "registerVraWebviewSource" in ts))
    checks.append(report(
        "NO_CHATGPT_DOM_SCRAPE",
        "executeJavaScript" not in ts
    ))
    checks.append(report("VERIFIER_FALSE_NEGATIVE_RETIRED", m is not None and all(checks[:5])))

    if not all(checks):
        print("VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_INTERNAL_FLEX_REPAIR_000039H3H3=FAIL")
        raise SystemExit(1)

    print("RUN=npm.cmd run build")
    # Important: capture raw bytes. Do not let Python decode npm output with the
    # Windows console codec (cp932), because electron-vite/Vite may emit UTF-8.
    cp = subprocess.run(
        ["npm.cmd", "run", "build"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        check=False,
    )

    if cp.returncode != 0:
        decoded = cp.stdout.decode("utf-8", errors="backslashreplace")
        print("BUILD=FAIL")
        print(ascii_safe(decoded))
        raise SystemExit(cp.returncode)

    print("BUILD=PASS")
    print("SUBPROCESS_RAW_BYTES_DECODE_GUARD=PASS")
    print("VERTEX_SESSION_PORTAL_CHATGPT_WEBVIEW_INTERNAL_FLEX_REPAIR_000039H3H3=PASS")

if __name__ == "__main__":
    main()
