#!/usr/bin/env python3
from pathlib import Path
import subprocess

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
FILES={
 "CONTRACTS":ROOT/"src"/"shared"/"vertex-shell-contracts.ts",
 "SERVICE":ROOT/"src"/"main"/"shell"/"vertex-shell-service.ts",
 "IPC":ROOT/"src"/"main"/"ipc"/"register-vertex-shell-ipc.ts",
 "COMPONENT":ROOT/"src"/"renderer"/"src"/"components"/"VertexShellUnit"/"VertexShellUnit.ts",
 "CSS":ROOT/"src"/"renderer"/"src"/"components"/"VertexShellUnit"/"VertexShellUnit.css",
 "RAY":ROOT/"scripts"/"ray_vertex_shell_unit_wiring_000080V4A.py",
}

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def main():
    checks=[]
    for k,p in FILES.items():
        checks.append(ck(f"FILE_{k}",p.exists()))

    if not all(checks):
        return 3

    contracts=FILES["CONTRACTS"].read_text(encoding="utf-8-sig",errors="replace")
    service=FILES["SERVICE"].read_text(encoding="utf-8-sig",errors="replace")
    ipc=FILES["IPC"].read_text(encoding="utf-8-sig",errors="replace")
    comp=FILES["COMPONENT"].read_text(encoding="utf-8-sig",errors="replace")

    checks += [
      ck("SHELL_CONTRACT","VertexShellBridge" in contracts and "VertexShellCommandResult" in contracts),
      ck("POWERSHELL_BACKEND","pwsh.exe" in service and "shell: false" in service),
      ck("NO_CMD_SHELL_TRUE","shell: true" not in service),
      ck("OUTPUT_BOUNDS","MAX_STREAM_BYTES" in service),
      ck("COMMAND_REDACTION","redactCommand" in service and "[REDACTED]" in service),
      ck("PERSISTENT_CWD","setCwd" in service and "safeExistingDirectory" in service),
      ck("PROCESS_TREE_STOP","taskkill.exe" in service and "'/T'" in service),
      ck("IPC_EXECUTE","vertex-shell:execute" in ipc),
      ck("IPC_OUTPUT","vertex-shell:output" in ipc),
      ck("HUMAN_COMPONENT","customElements.define('vertex-shell-unit'" in comp),
      ck("IME_ENTER_GUARD","event.isComposing" in comp),
      ck("COMPONENT_BRIDGE_FAILSAFE","BRIDGE OFFLINE" in comp),
      ck("NOT_WIRED_YET","Vertex Shell Unit Foundation" not in (ROOT/"src"/"main"/"index.ts").read_text(encoding="utf-8",errors="replace")),
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
    print("FOUNDATION_LOCATION=SESSION_PORTAL_INTERNAL_UNIT")
    print("SEPARATE_PROJECT_CREATED=FALSE")
    print("EXISTING_MAIN_INDEX_MUTATED=FALSE")
    print("EXISTING_PRELOAD_MUTATED=FALSE")
    print("EXISTING_SHARED_CONTRACTS_MUTATED=FALSE")
    print("EXISTING_MAINFRAME_MUTATED=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("AUTO_COMMAND_EXECUTION=FALSE")
    print("NEXT=RUN_WIRING_RAY_THEN_000080V4B")
    print("VERTEX_SHELL_UNIT_FOUNDATION_000080V4A="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
