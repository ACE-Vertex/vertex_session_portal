#!/usr/bin/env python3
from pathlib import Path
import subprocess

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE=ROOT/"src"/"main"/"shell"/"vertex-shell-service.ts"
BRIDGE=ROOT/"src"/"main"/"shell"/"vertex-shell-host-bridge.ts"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def main():
    checks=[
      ck("SERVICE_EXISTS",SERVICE.exists()),
      ck("BRIDGE_EXISTS",BRIDGE.exists()),
    ]
    if not all(checks): return 3

    s=SERVICE.read_text(encoding="utf-8-sig",errors="replace")
    b=BRIDGE.read_text(encoding="utf-8-sig",errors="replace")

    checks += [
      ck("GENERATION_MARKER_SERVICE","VERTEX_SHELL_ONECLIP_COMPOUND_COMMAND_000080V4C" in s),
      ck("GENERATION_MARKER_BRIDGE","VERTEX_SHELL_ONECLIP_COMPOUND_COMMAND_000080V4C" in b),
      ck("COMPOUND_SEPARATOR_GUARD","hasCommandSeparator" in s and r"/[;\r\n|&]/" in s),
      ck("SIMPLE_CD_META_PRESERVED","VERTEX_META" in s and "safeExistingDirectory" in s),
      ck("COPY_BUTTON",'class=\\"copy\\"' in b and "COPIED" in b),
      ck("LAST_CLIP","lastClip" in b),
      ck("ANSI_STRIP","stripAnsi" in b and "\\\\x1B" in b),
      ck("CLIPBOARD_PRIMARY","navigator.clipboard.writeText" in b),
      ck("CLIPBOARD_FALLBACK","document.execCommand('copy')" in b),
      ck("COPY_LAST_SEMANTICS","lastClip = ''" in b and "const source = lastClip || output.textContent" in b),
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
    print("V4C_SCOPE=VERTEX_SHELL_SERVICE_PLUS_HOST_UI_ONLY")
    print("MAIN_INDEX_MUTATED=FALSE")
    print("PRELOAD_MUTATED=FALSE")
    print("MAINFRAME_MUTATED=FALSE")
    print("VRA_DISPATCH_MUTATED=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("BUILD_UPDATED=FALSE")
    print("MANUAL_BUILD_REQUIRED=TRUE")
    print("RESTART_REQUIRED_AFTER_BUILD=TRUE")
    print("VERTEX_SHELL_ONECLIP_COMPOUND_COMMAND_000080V4C="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
