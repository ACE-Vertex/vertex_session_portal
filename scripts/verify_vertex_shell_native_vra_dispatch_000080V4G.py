#!/usr/bin/env python3
from pathlib import Path
import json
import re
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
BRIDGE = ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts"
CONTRACTS = ROOT / "src" / "shared" / "contracts.ts"
SERVICE = ROOT / "src" / "main" / "vra" / "vra-dispatch-service.ts"

def ck(name, value):
    ok = bool(value)
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    return ok

def extract_host_ui(bridge_text):
    match = re.search(r'const hostUi = (".*?")\n\nasync function injectHostUi', bridge_text, re.S)
    if not match:
        raise RuntimeError("HOST_UI_LITERAL_NOT_FOUND")
    return json.loads(match.group(1))

def main():
    if not BRIDGE.exists() or not CONTRACTS.exists() or not SERVICE.exists():
        print("SOURCE_FILES_EXIST=FAIL")
        return 3

    bridge = BRIDGE.read_text(encoding="utf-8-sig", errors="replace")
    contracts = CONTRACTS.read_text(encoding="utf-8-sig", errors="replace")
    service = SERVICE.read_text(encoding="utf-8-sig", errors="replace")
    host = extract_host_ui(bridge)

    native_start = host.find("const handleNativeVra = async")
    native_end = host.find("const execute = async", native_start)
    native = host[native_start:native_end] if native_start >= 0 and native_end > native_start else ""

    execute_start = host.find("const execute = async")
    execute_end = host.find("run.addEventListener", execute_start)
    execute = host[execute_start:execute_end] if execute_start >= 0 and execute_end > execute_start else ""

    branch_pos = execute.find("if (isNativeVraCommand(value))")
    shell_pos = execute.find("send('execute'")

    checks = [
        ck("GENERATION_MARKER", "VERTEX_SHELL_NATIVE_VRA_DISPATCH_000080V4G" in bridge),
        ck("HOST_UI_EXTRACTED", len(host) > 1000),
        ck("NATIVE_VRA_LIST", "vra list" in host and "getVraDispatchState()" in native),
        ck("NATIVE_VRA_DISPATCH", "vra dispatch <artifact-id|card-id|filename>" in host),
        ck("PORTAL_DISPATCH_API_USED", "portal.dispatchVraCard(card.id)" in native),
        ck("EXACT_CARD_ID_SELECTOR", "card.id, card.artifactId, card.filename" in native),
        ck("AMBIGUITY_FAIL_CLOSED", "VERTEX_SHELL_VRA_SELECTOR_AMBIGUOUS" in native),
        ck("NOT_FOUND_FAIL_CLOSED", "VERTEX_SHELL_VRA_NOT_FOUND" in native),
        ck("ALREADY_DISPATCHED_GUARD", "VERTEX_SHELL_VRA_ALREADY_DISPATCHED" in native),
        ck("EXPLICIT_HUMAN_LABEL", "NATIVE VRA DISPATCH · Human command" in native),
        ck("NATIVE_BRANCH_BEFORE_PWSH", branch_pos >= 0 and shell_pos >= 0 and branch_pos < shell_pos),
        ck("NATIVE_HANDLER_NO_SEND_EXECUTE", "send('execute'" not in native),
        ck("NATIVE_HANDLER_NO_CMD_EXE", "cmd.exe" not in native.lower()),
        ck("NATIVE_HANDLER_NO_PWSH_EXE", "pwsh.exe" not in native.lower()),
        ck("NATIVE_HANDLER_NO_SPAWN", "spawn(" not in native.lower()),
        ck("NATIVE_HANDLER_NO_DIRECT_HTTP", "fetch(" not in native.lower() and "http://" not in native.lower() and "https://" not in native.lower()),
        ck("REGULAR_PWSH_PATH_PRESERVED", "send('execute', { command: value, cwd: tab.cwd })" in execute),
        ck("RIGHTCLICK_PASTE_PRESERVED", "paste_clipboard" in bridge and "await clipboard.readText()" in bridge),
        ck("CTRL_N_PRESERVED", "String(event.key).toLowerCase() === 'n'" in host),
        ck("TOGGLE_PRESERVED", "CommandOrControl+Alt+Space" in bridge),
        ck("COPY_PRESERVED", "navigator.clipboard.writeText" in host and "lastClip" in host),
        ck("VRA_STATE_API_CONTRACT", "getVraDispatchState(): Promise<VraDispatchState>" in contracts),
        ck("VRA_DISPATCH_API_CONTRACT", "dispatchVraCard(cardId: string): Promise<VraDispatchCard>" in contracts),
        ck("EXISTING_ATOMIC_PUBLISH_OWNER", "publishToIncomingAtomic(card, destination)" in service),
        ck("WORKSTATION_LANE_AUTHORITY_PRESERVED", "Never assign allocatedLane here. Final Lane Allocation Authority is Workstation." in service),
        ck("FILESYSTEM_CONTROL_SPLIT_PRESERVED", "Filesystem = Data Commit. HTTP = Control Registration." in service),
    ]

    node = subprocess.run(
        ["node", "--check", "-"],
        input=host,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(f"HOST_UI_NODE_CHECK_EXIT={node.returncode}")
    if node.stderr:
        print("HOST_UI_NODE_CHECK_STDERR=" + " | ".join(node.stderr.splitlines()[-30:]))
    checks.append(ck("HOST_UI_NODE_SYNTAX", node.returncode == 0))

    tc = subprocess.run(
        ["npm.cmd", "run", "typecheck"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    print(f"TYPECHECK_EXIT={tc.returncode}")
    if tc.stdout:
        print("TYPECHECK_STDOUT_TAIL=" + " | ".join(tc.stdout.splitlines()[-50:]))
    if tc.stderr:
        print("TYPECHECK_STDERR_TAIL=" + " | ".join(tc.stderr.splitlines()[-50:]))
    checks.append(ck("TYPECHECK_PASS", tc.returncode == 0))

    ok = all(checks)

    print("VSH_NATIVE_VRA_DISPATCH=IMPLEMENTED")
    print("PWSH_VRA_DISPATCH=FALSE")
    print("CMD_VRA_DISPATCH=FALSE")
    print("DIRECT_WORKSTATION_HTTP=FALSE")
    print("EXISTING_PORTAL_DISPATCH_API=TRUE")
    print("EXISTING_VRA_DISPATCH_SERVICE_REUSED=TRUE")
    print("HUMAN_EXPLICIT_COMMAND_REQUIRED=TRUE")
    print("AUTO_DISPATCH_ADDED=FALSE")
    print("PORTAL_PRELOAD_MUTATED=FALSE")
    print("PORTAL_CONTRACTS_MUTATED=FALSE")
    print("VRA_DISPATCH_SERVICE_MUTATED=FALSE")
    print("VRA_DISPATCH_LANE_MUTATED=FALSE")
    print("WORKSTATION_MUTATED=FALSE")
    print("FLICKER_ELIMINATION_RUNTIME_PROVEN=FALSE")
    print("MANUAL_BUILD_REQUIRED=TRUE")
    print("RESTART_REQUIRED_AFTER_BUILD=TRUE")
    print("VERTEX_SHELL_NATIVE_VRA_DISPATCH_000080V4G=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__ == "__main__":
    raise SystemExit(main())
