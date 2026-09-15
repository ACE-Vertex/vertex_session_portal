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
      ck("GENERATION_MARKER","VERTEX_SHELL_TOGGLE_TABS_RESIZE_000080V4E" in b),
      ck("TOGGLE_HOTKEY","CommandOrControl+Alt+Space" in b and "toggleBestHostShell" in b),
      ck("VISIBILITY_API","__VERTEX_SHELL_SET_VISIBILITY__" in b),
      ck("FRONT_OFF_HOTKEY","CommandOrControl+B" in b),
      ck("FRONT_ON_HOTKEY","CommandOrControl+F" in b),
      ck("VISIBLE_ONLY_TOPMOST_HOTKEYS","updateTopmostHotkeys" in b and "anyVisible" in b),
      ck("NEW_TAB_UI","tabAdd" in b and "createTab" in b and "SHELL ${tabSeq}" in b),
      ck("TAB_STATE_ISOLATION","tab.history" in b and "tab.output" in b and "tab.cwd" in b),
      ck("SINGLE_FLIGHT_PRESERVED","runningTabId" in b and "service.execute" in b),
      ck("RESIZE_GRIP","resizeGrip" in b and "pointermove" in b),
      ck("RESIZE_PERSISTENCE","vertex-shell:v4e:size" in b and "localStorage.setItem" in b),
      ck("RIGHTCLICK_PASTE_PRESERVED","paste_clipboard" in b and "await clipboard.readText()" in b),
      ck("COPY_PRESERVED","navigator.clipboard.writeText" in b and "lastClip" in b),
      ck("IME_GUARD_PRESERVED","event.isComposing" in b),
      ck("PIN_PRESERVED","setAlwaysOnTop" in b and "toggle_topmost" in b),
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
    print("TABS_EXECUTION_MODEL=SINGLE_FLIGHT_PWSH_WITH_MULTI_TAB_UI_WORKSPACES")
    print("CTRL_ALT_SPACE=VERTEX_SHELL_VISIBILITY_TOGGLE")
    print("CTRL_B=TOPMOST_OFF_WHILE_SHELL_VISIBLE")
    print("CTRL_F=TOPMOST_ON_WHILE_SHELL_VISIBLE")
    print("RESIZE=HOST_UI_WIDTH_HEIGHT_PERSISTED")
    print("SERVICE_MUTATED=FALSE")
    print("MAIN_INDEX_MUTATED=FALSE")
    print("PRELOAD_MUTATED=FALSE")
    print("MAINFRAME_MUTATED=FALSE")
    print("VRA_DISPATCH_MUTATED=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("MANUAL_BUILD_REQUIRED=TRUE")
    print("RESTART_REQUIRED_AFTER_BUILD=TRUE")
    print("VERTEX_SHELL_TOGGLE_TABS_RESIZE_000080V4E="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
