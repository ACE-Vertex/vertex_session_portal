from __future__ import annotations
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WS_ROOT = ROOT.parent / "vertex_workstation"
PARENT_H1 = ROOT / "scripts" / "verify_session_portal_final_wiring_b_000054V1H1.py"
CONTRACTS = ROOT / "src" / "shared" / "contracts.ts"
PRELOAD = ROOT / "src" / "preload" / "index.ts"
PROJECT_TREE_IPC = ROOT / "src" / "main" / "ipc" / "register-project-tree-ipc.ts"
WS_FILES = [
    WS_ROOT / "headless" / "src" / "evidence_api.rs",
    WS_ROOT / "headless" / "src" / "server_adapter.rs",
    WS_ROOT / "headless" / "src" / "core_bridge.rs",
]

def emit(value: str) -> None:
    print(str(value).encode("ascii", errors="backslashreplace").decode("ascii"))

def text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot_src() -> dict[str, str]:
    out: dict[str, str] = {}
    root = ROOT / "src"
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[p.relative_to(ROOT).as_posix()] = digest(p)
    return out

def check(name: str, ok: bool, failures: list[str]) -> None:
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def run(cmd: list[str], label: str) -> int:
    emit("RUN=" + " ".join(cmd))
    p = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        check=False,
    )
    emit(p.stdout)
    emit(f"{label}_EXIT={p.returncode}")
    return p.returncode

def main() -> int:
    failures: list[str] = []
    emit("=== VERTEX SESSION PORTAL / FINAL WIRING B 000054V1H2 PROJECT TREE API BRIDGE REPAIR VERIFY ===")
    emit(f"ROOT={ROOT}")
    emit(f"WORKSTATION_READ_ONLY={WS_ROOT}")
    emit("PRODUCTION_MUTATION_FROM_VERIFY=NO")

    for name, path in [
        ("PARENT_H1_VERIFY", PARENT_H1),
        ("SHARED_CONTRACTS", CONTRACTS),
        ("PRELOAD", PRELOAD),
        ("PROJECT_TREE_IPC", PROJECT_TREE_IPC),
    ]:
        check(f"FILE_{name}", path.is_file(), failures)
    if failures:
        emit("RED=REQUIRED_FILE_MISSING")
        emit("FAILURES=" + ",".join(failures))
        return 2

    contracts = text(CONTRACTS)
    preload = text(PRELOAD)
    pti = text(PROJECT_TREE_IPC)

    exact_api = [
        "listProjectTree(path?: string): Promise<ProjectTreeListing>",
        "resolveProjectTreePath(path: string): Promise<string>",
        "openProjectTreePath(path: string): Promise<void>",
        "revealProjectTreePath(path: string): Promise<void>",
        "copyProjectTreePath(path: string): Promise<void>",
    ]
    for token in exact_api:
        check("API_" + token.split("(",1)[0].upper(), token in contracts, failures)

    check("PROJECT_TREE_LISTING_IMPORT_PRELOAD", "ProjectTreeListing," in preload, failures)
    bridge_tokens = [
        "ipcRenderer.invoke('project-tree:list', path)",
        "ipcRenderer.invoke('project-tree:resolve', path)",
        "ipcRenderer.invoke('project-tree:open', path)",
        "ipcRenderer.invoke('project-tree:reveal', path)",
        "ipcRenderer.invoke('project-tree:copy-path', path)",
    ]
    for token in bridge_tokens:
        check("PRELOAD_" + token.split("'project-tree:",1)[1].split("'",1)[0].replace("-","_").upper(), token in preload, failures)

    check("PROJECT_TREE_CONTRACT_MARKER_RESTORED", "export const PROJECT_TREE_CONTRACT = {" in contracts, failures)
    check("PROJECT_TREE_READ_ONLY_CONTRACT", "writes: 'NO'" in contracts, failures)
    check("PROJECT_TREE_IPC_LIST_EXISTS", "'project-tree:list'" in pti, failures)
    check("PROJECT_TREE_IPC_RESOLVE_EXISTS", "'project-tree:resolve'" in pti, failures)
    check("PROJECT_TREE_IPC_OPEN_EXISTS", "'project-tree:open'" in pti, failures)
    check("PROJECT_TREE_IPC_REVEAL_EXISTS", "'project-tree:reveal'" in pti, failures)
    check("PROJECT_TREE_IPC_COPY_EXISTS", "'project-tree:copy-path'" in pti, failures)

    # Final B contracts must remain intact.
    check("FINAL_B_ACK_API_PRESERVED", "acknowledgeVraEvidenceDelivery" in contracts, failures)
    check("FINAL_B_CLIPBOARD_API_PRESERVED", "readClipboardText(): Promise<string>" in contracts, failures)
    check("FINAL_B_VRA_DISPATCH_PRESERVED", "getVraDispatchState(): Promise<VraDispatchState>" in contracts, failures)
    check("HUMAN_GATE_PRESERVED", "HUMAN_APPLY" in contracts, failures)

    src_before = snapshot_src()
    ws_before = {p.as_posix(): digest(p) for p in WS_FILES if p.is_file()}

    parent_exit = run([sys.executable, str(PARENT_H1)], "PARENT_H1")
    check("PARENT_H1_FULL_VERIFY", parent_exit == 0, failures)

    src_after = snapshot_src()
    ws_after = {p.as_posix(): digest(p) for p in WS_FILES if p.is_file()}
    check("VERIFY_PORTAL_SOURCE_UNCHANGED", src_before == src_after, failures)
    check("WORKSTATION_PRODUCTION_UNCHANGED", ws_before == ws_after, failures)

    if failures:
        emit("RED=VERIFY_FAILURE")
        emit("YELLOW=REQUIRES_REPAIR")
        emit("FAILURES=" + ",".join(failures))
        emit("VERTEX_SESSION_PORTAL_FINAL_WIRING_B_000054V1H2=FAIL")
        return 1

    emit("ROOT_CAUSE=FINAL_B_PRELOAD_AND_VERTEXPORTALAPI_DROPPED_EXISTING_PROJECT_TREE_BRIDGE")
    emit("REPAIR=RESTORE_VERIFIED_PROJECT_TREE_API_SIGNATURES_AND_PRELOAD_IPC")
    emit("FINAL_B_FUNCTIONAL_IMPLEMENTATION=PRESERVED")
    emit("WORKSTATION_MUTATION=NO")
    emit("RED=NONE")
    emit("YELLOW=NONE")
    emit("VERTEX_SESSION_PORTAL_FINAL_WIRING_B_000054V1H2=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
