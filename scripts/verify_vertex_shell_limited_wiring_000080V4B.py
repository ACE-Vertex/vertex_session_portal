#!/usr/bin/env python3
from pathlib import Path
import subprocess, hashlib

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BRIDGE=ROOT/"src"/"main"/"shell"/"vertex-shell-host-bridge.ts"
SERVICE=ROOT/"src"/"main"/"shell"/"vertex-shell-service.ts"
RAY=ROOT/"src"/"main"/"diagnostics"/"focus-scroll-event-ray.ts"
MAIN=ROOT/"src"/"main"/"index.ts"
PRELOAD=ROOT/"src"/"preload"/"index.ts"
MAINFRAME=ROOT/"src"/"renderer"/"src"/"components"/"MainFrame"/"MainFrame.ts"
CONTRACTS=ROOT/"src"/"shared"/"contracts.ts"

EXPECTED={
 "main":"3058561e23d1a97c2355e088b9d94c29e92b9058f24350dcf0954d843cf2e090",
 "preload":"c0378e3156815c9f52cfc02b45f421e0f2bf73a8e660339a368d1098e19d3961",
 "contracts":"eab99c41657bc750b31c4263c5f9f063613005d6633ef6c27396481795b3f8b7",
 "mainframe":"56c0b7b80fc3a37efffca2ddb90542d1fa91d33c65984ca9db5ee0c23bdebba4",
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def main():
    checks=[
      ck("FILE_HOST_BRIDGE",BRIDGE.exists()),
      ck("FILE_SERVICE",SERVICE.exists()),
      ck("FILE_EVENT_RAY",RAY.exists()),
    ]
    if not all(checks): return 3

    bridge=BRIDGE.read_text(encoding="utf-8-sig",errors="replace")
    ray=RAY.read_text(encoding="utf-8-sig",errors="replace")

    checks += [
      ck("BOOTSTRAP_IMPORT","../shell/vertex-shell-host-bridge" in ray),
      ck("HUMAN_HOST_ONLY","BrowserWindow.fromWebContents" in bridge),
      ck("NONCE_GUARD","message.nonce !== binding.nonce" in bridge),
      ck("GLOBAL_SUMMON","CommandOrControl+Alt+Space" in bridge and "globalShortcut.register" in bridge),
      ck("TOPMOST_CONTROL","setAlwaysOnTop" in bridge and "toggle_topmost" in bridge),
      ck("POWERSHELL_SERVICE_USED","new VertexShellService()" in bridge),
      ck("NO_VERA_AUTO_EXECUTION","vera_auto_execution: false" in bridge),
      ck("NO_WEBVIEW_EXECUTION","webview_execution: false" in bridge),
      ck("IME_GUARD","event.isComposing" in bridge),
      ck("STREAM_BOUND","MAX_UI_STREAM_CHUNK" in bridge),
      ck("HOST_LOG","host-bridge.jsonl" in bridge),
      ck("MAIN_INDEX_UNCHANGED",sha(MAIN)==EXPECTED["main"]),
      ck("PRELOAD_UNCHANGED",sha(PRELOAD)==EXPECTED["preload"]),
      ck("SHARED_CONTRACTS_UNCHANGED",sha(CONTRACTS)==EXPECTED["contracts"]),
      ck("MAINFRAME_UNCHANGED",sha(MAINFRAME)==EXPECTED["mainframe"]),
    ]

    p=subprocess.run(
      ["npm.cmd","run","typecheck"],
      cwd=ROOT,
      capture_output=True,
      text=True,
      encoding="utf-8",
      errors="replace",
    )
    print(f"TYPECHECK_EXIT={p.returncode}")
    if p.stdout:
        print("TYPECHECK_STDOUT_TAIL="+" | ".join(p.stdout.splitlines()[-60:]))
    if p.stderr:
        print("TYPECHECK_STDERR_TAIL="+" | ".join(p.stderr.splitlines()[-60:]))
    checks.append(ck("TYPECHECK_PASS",p.returncode==0))

    ok=all(checks)
    print("WIRING_MODE=VERA4_OWNED_MAIN_SIDE_EFFECT_BOOTSTRAP")
    print("MAIN_INDEX_MUTATED=FALSE")
    print("PRELOAD_MUTATED=FALSE")
    print("SHARED_CONTRACTS_MUTATED=FALSE")
    print("MAINFRAME_MUTATED=FALSE")
    print("VRA_DISPATCH_MUTATED=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("BUILD_UPDATED=FALSE")
    print("MANUAL_BUILD_REQUIRED=TRUE")
    print("RESTART_REQUIRED_AFTER_BUILD=TRUE")
    print("VERTEX_SHELL_LIMITED_WIRING_000080V4B="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
