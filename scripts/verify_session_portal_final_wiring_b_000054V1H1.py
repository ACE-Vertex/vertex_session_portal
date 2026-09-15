from __future__ import annotations
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WS_ROOT = ROOT.parent / "vertex_workstation"
PARENT = ROOT / "scripts" / "verify_session_portal_final_wiring_b_000054V1.py"
IPC = ROOT / "src" / "main" / "ipc" / "register-vra-dispatch-ipc.ts"
CONTRACTS = ROOT / "src" / "shared" / "contracts.ts"
PROJECT_TREE_SERVICE = ROOT / "src" / "main" / "project" / "project-tree-service.ts"
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

def run(cmd: list[str], label: str, env: dict[str, str] | None = None) -> int:
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
        env=env,
    )
    emit(p.stdout)
    emit(f"{label}_EXIT={p.returncode}")
    return p.returncode

def main() -> int:
    failures: list[str] = []
    emit("=== VERTEX SESSION PORTAL / FINAL WIRING B 000054V1H1 COMPAT REPAIR VERIFY ===")
    emit(f"ROOT={ROOT}")
    emit(f"WORKSTATION_READ_ONLY={WS_ROOT}")
    emit("PRODUCTION_MUTATION_FROM_VERIFY=NO")

    for name, path in [
        ("PARENT_FINAL_B_VERIFY", PARENT),
        ("REGISTER_VRA_DISPATCH_IPC", IPC),
        ("SHARED_CONTRACTS", CONTRACTS),
        ("PROJECT_TREE_SERVICE", PROJECT_TREE_SERVICE),
    ]:
        check(f"FILE_{name}", path.is_file(), failures)

    if failures:
        emit("RED=REQUIRED_FILE_MISSING")
        emit("FAILURES=" + ",".join(failures))
        return 2

    ipc = text(IPC)
    contracts = text(CONTRACTS)
    pts = text(PROJECT_TREE_SERVICE)

    # Repair 1: Electron clipboard may be sync or Promise-typed; IPC boundary is explicitly async.
    check(
        "CLIPBOARD_IPC_PROMISE_SAFE",
        "async (): Promise<string> => await clipboard.readText()" in ipc,
        failures,
    )
    check(
        "CLIPBOARD_PASTE_ONLY_CONTRACT_PRESERVED",
        "'portal:clipboard-read-text'" in ipc and "clipboard.readText()" in ipc,
        failures,
    )

    # Repair 2: restore exact legacy Project Tree exported contracts.
    check(
        "PROJECT_TREE_NODE_KIND_RESTORED",
        "export type ProjectTreeNodeKind = 'DIRECTORY' | 'FILE' | 'SYMLINK' | 'OTHER'" in contracts,
        failures,
    )
    check(
        "PROJECT_TREE_NODE_RESTORED",
        all(token in contracts for token in [
            "export interface ProjectTreeNode {",
            "relativePath: string",
            "kind: ProjectTreeNodeKind",
            "expandable: boolean",
        ]),
        failures,
    )
    check(
        "PROJECT_TREE_BREADCRUMB_RESTORED",
        "export interface ProjectTreeBreadcrumb {" in contracts and "name: string" in contracts and "path: string" in contracts,
        failures,
    )
    check(
        "PROJECT_TREE_LISTING_RESTORED",
        all(token in contracts for token in [
            "export interface ProjectTreeListing {",
            "rootPath: string",
            "workspaceRootPath: string",
            "parentPath: string | null",
            "breadcrumbs: ProjectTreeBreadcrumb[]",
            "directory: ProjectTreeNode",
            "children: ProjectTreeNode[]",
        ]),
        failures,
    )
    for type_name in ("ProjectTreeBreadcrumb", "ProjectTreeListing", "ProjectTreeNode", "ProjectTreeNodeKind"):
        check(f"PROJECT_TREE_SERVICE_IMPORT_{type_name.upper()}", type_name in pts, failures)

    # No regression of Final B core contracts.
    check("FINAL_B_ACK_CONTRACT_PRESERVED", "VraEvidenceDeliveryAckRequest" in contracts, failures)
    check("FINAL_B_DISPATCH_CONTRACT_PRESERVED", "VraDispatchState" in contracts, failures)
    check("FINAL_B_PORTAL_API_PRESERVED", "acknowledgeVraEvidenceDelivery" in contracts and "readClipboardText" in contracts, failures)
    check("HUMAN_GATE_PRESERVED", "HUMAN_APPLY" in contracts, failures)
    check("NO_AUTO_SEND_IN_IPC", "send-button" not in ipc.lower() and ".click()" not in ipc, failures)

    src_before = snapshot_src()
    ws_before = {p.as_posix(): digest(p) for p in WS_FILES if p.is_file()}

    # Re-run all parent Final B static gates, but do not duplicate its npm build pass.
    parent_env = dict(os.environ)
    parent_env["VERTEX_FINAL_B_INTERNAL_STATIC_ONLY"] = "1"
    parent_exit = run([sys.executable, str(PARENT)], "PARENT_FINAL_B_STATIC", parent_env)
    check("PARENT_FINAL_B_STATIC_VERIFY", parent_exit == 0, failures)

    npm = "npm.cmd" if os.name == "nt" else "npm"
    tc = run([npm, "run", "typecheck"], "TYPECHECK")
    check("TYPECHECK", tc == 0, failures)
    build = run([npm, "run", "build"], "BUILD")
    check("BUILD", build == 0, failures)

    src_after = snapshot_src()
    ws_after = {p.as_posix(): digest(p) for p in WS_FILES if p.is_file()}
    check("VERIFY_PORTAL_SOURCE_UNCHANGED", src_before == src_after, failures)
    check("WORKSTATION_PRODUCTION_UNCHANGED", ws_before == ws_after, failures)

    if failures:
        emit("RED=VERIFY_FAILURE")
        emit("YELLOW=REQUIRES_REPAIR")
        emit("FAILURES=" + ",".join(failures))
        emit("VERTEX_SESSION_PORTAL_FINAL_WIRING_B_000054V1H1=FAIL")
        return 1

    emit("ROOT_CAUSE_1=CLIPBOARD_HANDLER_SYNC_RETURN_ANNOTATION")
    emit("ROOT_CAUSE_2=SHARED_CONTRACTS_REPLACEMENT_DROPPED_PROJECT_TREE_EXPORTS")
    emit("FINAL_B_FUNCTIONAL_IMPLEMENTATION=PRESERVED")
    emit("WORKSTATION_MUTATION=NO")
    emit("RED=NONE")
    emit("YELLOW=NONE")
    emit("VERTEX_SESSION_PORTAL_FINAL_WIRING_B_000054V1H1=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
