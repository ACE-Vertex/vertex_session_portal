from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "src/renderer/src/components/VeraBrowserSession"
TS = COMP / "VeraBrowserSession.ts"
CSS = COMP / "VeraBrowserSession.css"
INJECTOR = COMP / "VeraRelayInjector.ts"

def emit(name, ok):
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def safe_ascii(text):
    return text.encode("ascii", errors="backslashreplace").decode("ascii")

def main():
    print("VERTEX SESSION PORTAL / VERA PEER RELAY EXPERIMENT VERIFY 000042")
    print(f"ROOT={ROOT}")

    ts = TS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    injector = INJECTOR.read_text(encoding="utf-8")
    view_match = re.search(r"\.chatgptView\s*\{(?P<body>.*?)\}", css, re.S)
    view_body = re.sub(r"\s+", "", view_match.group("body") if view_match else "")

    checks = [
        emit("PEER_RELAY_EVENT", "vertex-vera-peer-relay" in ts),
        emit("THREE_VERA_TARGETS", all(x in ts for x in ("vera-01", "vera-02", "vera-03"))),
        emit("MANUAL_RELAY_TRIGGER", 'data-action="relay"' in ts and "window.prompt" in ts),
        emit("NO_SELF_RELAY", "Choose another Vera session" in ts),
        emit("WINDOW_EVENT_BUS", "window.dispatchEvent" in ts and "window.addEventListener" in ts),
        emit("WRITE_ONLY_INJECTOR_MODULE", "injectRelayMessage" in ts and "executeJavaScript" not in ts),
        emit("TARGET_COMPOSER_INJECTION", "#prompt-textarea" in injector and "prompt-textarea" in injector),
        emit("SEND_BUTTON_AUTOMATION", "send-button" in injector),
        emit("NO_RESPONSE_SCRAPE", all(token not in injector for token in (
            "data-message-author-role", "conversation-turn", ".markdown", "querySelectorAll"
        ))),
        emit("NO_BROADCAST", "broadcast" not in ts.lower() and "MAIN_VERA_IDS" in ts),
        emit("PERSIST_PARTITION_PRESERVED", "persist:vertex-vera-chatgpt" in ts),
        emit("THREAD_BRIDGE_PRESERVED", "updateVeraSessionThread" in ts),
        emit("VRA_DOWNLOAD_BRIDGE_PRESERVED", "registerVraWebviewSource" in ts),
        emit("RELAY_BUTTON_STYLE", ".relayButton" in css),
        emit("WEBVIEW_NATIVE_FLEX_PRESERVED", "display:flex;" in view_body),
    ]

    if not all(checks):
        print("VERTEX_SESSION_PORTAL_VERA_PEER_RELAY_EXPERIMENT_000042=FAIL")
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
        print(safe_ascii(cp.stdout.decode("utf-8", errors="backslashreplace")))
        raise SystemExit(cp.returncode)

    print("BUILD=PASS")
    print("EXPERIMENT_SCOPE=MANUAL_ONE_HOP_VERA_TO_VERA_RELAY")
    print("CHATGPT_DOM_READ_SCRAPE=DISABLED")
    print("CHATGPT_DOM_WRITE_INJECTION=EXPERIMENTAL")
    print("VERTEX_SESSION_PORTAL_VERA_PEER_RELAY_EXPERIMENT_000042=PASS")

if __name__ == "__main__":
    main()
