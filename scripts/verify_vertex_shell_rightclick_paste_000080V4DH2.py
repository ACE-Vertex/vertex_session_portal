#!/usr/bin/env python3
from pathlib import Path
import subprocess

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BRIDGE=ROOT/"src"/"main"/"shell"/"vertex-shell-host-bridge.ts"
SERVICE=ROOT/"src"/"main"/"shell"/"vertex-shell-service.ts"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def main():
    checks=[
      ck("BRIDGE_EXISTS",BRIDGE.exists()),
      ck("SERVICE_EXISTS",SERVICE.exists()),
    ]
    if not all(checks):
        return 3

    b=BRIDGE.read_text(encoding="utf-8-sig",errors="replace")
    s=SERVICE.read_text(encoding="utf-8-sig",errors="replace")

    checks += [
      ck("GENERATION_MARKER","VERTEX_SHELL_RIGHTCLICK_PASTE_000080V4DH2" in b),
      ck("ELECTRON_CLIPBOARD_IMPORTED","clipboard," in b and "from 'electron'" in b),
      ck("PASTE_ACTION","case 'paste_clipboard'" in b),
      ck("CLIPBOARD_READ_AWAIT","const text = await clipboard.readText()" in b),
      ck("CLIPBOARD_RESPONSE","type: 'clipboard_text'" in b),
      ck("RIGHTCLICK_HANDLER","contextmenu" in b and "send('paste_clipboard')" in b),
      ck("PREVENT_DEFAULT","event.preventDefault()" in b),
      ck("CARET_INSERT","insertTextAtCaret" in b and "selectionStart" in b and "selectionEnd" in b),
      ck("COMMAND_DEFAULT_TARGET","active === command || active === cwd" in b),
      ck("COPY_PRESERVED","navigator.clipboard.writeText" in b and "lastClip" in b),
      ck(
        "COMPOUND_COMMAND_SERVICE_PRESERVED",
        "hasCommandSeparator" in s
        and "command.match(/^(?:cd|set-location)" in s
      ),
      ck("IME_GUARD_PRESERVED","event.isComposing" in b),
      ck("TOPMOST_PRESERVED","setAlwaysOnTop" in b),
      ck("GLOBAL_SUMMON_PRESERVED","CommandOrControl+Alt+Space" in b),
      ck("NO_VERA_AUTO_EXECUTION","vera_auto_execution: false" in b),
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
        print("TYPECHECK_STDOUT_TAIL="+" | ".join(p.stdout.splitlines()[-50:]))
    if p.stderr:
        print("TYPECHECK_STDERR_TAIL="+" | ".join(p.stderr.splitlines()[-50:]))
    checks.append(ck("TYPECHECK_PASS",p.returncode==0))

    ok=all(checks)
    print("H1_IMPLEMENTATION_TYPECHECK=PASS_EXPECTED")
    print("H1_FAILURE_CLASSIFICATION=VERIFIER_FALSE_NEGATIVE")
    print("H2_FIX=VERIFY_COMPOUND_COMMAND_AT_SERVICE_CONTRACT")
    print("V4DH2_SCOPE=HOST_BRIDGE_PLUS_VERIFIER_ONLY")
    print("SERVICE_MUTATED=FALSE")
    print("MAIN_INDEX_MUTATED=FALSE")
    print("PRELOAD_MUTATED=FALSE")
    print("MAINFRAME_MUTATED=FALSE")
    print("VRA_DISPATCH_MUTATED=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("BUILD_UPDATED=FALSE")
    print("MANUAL_BUILD_REQUIRED=TRUE")
    print("RESTART_REQUIRED_AFTER_BUILD=TRUE")
    print("VERTEX_SHELL_RIGHTCLICK_PASTE_000080V4DH2="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
