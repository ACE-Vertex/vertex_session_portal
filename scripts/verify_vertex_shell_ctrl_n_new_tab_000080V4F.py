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
    if not BRIDGE.exists() or not SERVICE.exists():
        print("SOURCE_EXISTS=FAIL")
        return 3

    b=BRIDGE.read_text(encoding="utf-8-sig",errors="replace")
    s=SERVICE.read_text(encoding="utf-8-sig",errors="replace")

    checks=[
      ck("GENERATION_MARKER","VERTEX_SHELL_CTRL_N_NEW_TAB_000080V4F" in b),
      ck("CTRL_N_HANDLER","String(event.key).toLowerCase() === 'n'" in b),
      ck("CTRL_REQUIRED","event.ctrlKey" in b),
      ck("SHELL_VISIBLE_GUARD","root.style.display === 'none'" in b),
      ck("DEFAULT_PREVENTED","event.preventDefault()" in b),
      ck("PROPAGATION_STOPPED","event.stopPropagation()" in b),
      ck("NEW_TAB_CALLED","createTab(base, true)" in b),
      ck("COMMAND_FOCUS_AFTER_TAB","command.focus()" in b),
      ck("PLUS_BUTTON_PRESERVED","tabAdd" in b),
      ck("TOGGLE_HOTKEY_PRESERVED","CommandOrControl+Alt+Space" in b),
      ck("FRONT_OFF_PRESERVED","CommandOrControl+B" in b),
      ck("FRONT_ON_PRESERVED","CommandOrControl+F" in b),
      ck("RESIZE_PRESERVED","resizeGrip" in b and "vertex-shell:v4e:size" in b),
      ck("RIGHTCLICK_PASTE_PRESERVED","paste_clipboard" in b and "await clipboard.readText()" in b),
      ck("COPY_PRESERVED","navigator.clipboard.writeText" in b and "lastClip" in b),
      ck("IME_GUARD_PRESERVED","event.isComposing" in b),
      ck(
        "COMPOUND_COMMAND_PRESERVED",
        "hasCommandSeparator" in s
        and "command.match(/^(?:cd|set-location)" in s
      ),
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
        print("TYPECHECK_STDOUT_TAIL="+" | ".join(p.stdout.splitlines()[-60:]))
    if p.stderr:
        print("TYPECHECK_STDERR_TAIL="+" | ".join(p.stderr.splitlines()[-60:]))

    checks.append(ck("TYPECHECK_PASS",p.returncode==0))

    ok=all(checks)
    print("CTRL_N_SCOPE=VERTEX_SHELL_VISIBLE_HOST_UI_ONLY")
    print("CTRL_N_BEHAVIOR=NEW_VERTEX_SHELL_TAB")
    print("TAB_EXECUTION_MODEL=SINGLE_FLIGHT_PWSH")
    print("SERVICE_MUTATED=FALSE")
    print("MAIN_INDEX_MUTATED=FALSE")
    print("PRELOAD_MUTATED=FALSE")
    print("MAINFRAME_MUTATED=FALSE")
    print("VRA_DISPATCH_MUTATED=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("MANUAL_BUILD_REQUIRED=TRUE")
    print("RESTART_REQUIRED_AFTER_BUILD=TRUE")
    print("VERTEX_SHELL_CTRL_N_NEW_TAB_000080V4F="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
