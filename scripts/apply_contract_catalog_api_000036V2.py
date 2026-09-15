from __future__ import annotations

from pathlib import Path
import subprocess, sys, shutil, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
PRELOAD = ROOT / "src/preload/index.ts"
CATALOG = ROOT / "src/shared/vertex-contract-catalog.ts"
DOC = ROOT / "docs/ARCHITECTURE/VERTEX_CONTRACT_CATALOG_API.md"

STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / "EVIDENCE" / "CONTRACT_CATALOG_API_000036V2" / STAMP
MARKER = "VERTEX_CONTRACT_CATALOG_API_000036V2"

def safe(v=""):
    print(str(v).encode("ascii","backslashreplace").decode("ascii"))

def read(p: Path) -> str:
    if not p.exists():
        raise RuntimeError(f"MISSING:{p}")
    return p.read_text(encoding="utf-8-sig")

def write(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def run_npm(args):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    p = subprocess.run([npm,*args],cwd=ROOT,text=True,encoding="utf-8",errors="replace",capture_output=True)
    safe(f"RUN={npm} {' '.join(args)}")
    safe(f"EXIT={p.returncode}")
    for line in (p.stdout+"\n"+p.stderr).splitlines()[-80:]:
        safe(line)
    return p.returncode

ipc0 = read(IPC)
pre0 = read(PRELOAD)
cat = read(CATALOG)

if MARKER in ipc0 or MARKER in pre0:
    raise SystemExit("ALREADY_APPLIED")
if "vertex.vra.issue/1" not in cat or "vertex.evidence.read/1" not in cat:
    raise SystemExit("CATALOG_CORE_MISSING")

BACKUP.mkdir(parents=True, exist_ok=True)
shutil.copy2(IPC, BACKUP / IPC.name)
shutil.copy2(PRELOAD, BACKUP / PRELOAD.name)

try:
    ipc = ipc0
    preload = pre0

    # Main-process import.
    import_anchor = "import { BrowserWindow, clipboard, ipcMain, screen } from 'electron'\n"
    if import_anchor not in ipc:
        raise RuntimeError("IPC_IMPORT_ANCHOR_MISSING")
    ipc = ipc.replace(
        import_anchor,
        import_anchor +
        "import { listVertexContracts, resolveVertexContract, type VertexContractId } from '../../shared/vertex-contract-catalog'\n",
        1
    )

    # Register a tiny read-only contract API alongside the existing VRA IPC owner.
    func_anchor = "export function registerVraDispatchIpc(service: VraDispatchService): void {\n"
    if func_anchor not in ipc:
        raise RuntimeError("IPC_FUNCTION_ANCHOR_MISSING")

    handler = f"""export function registerVraDispatchIpc(service: VraDispatchService): void {{
  // {MARKER}: read-only canonical system-contract catalog.
  ipcMain.removeHandler('vertex:contract-resolve')
  ipcMain.removeHandler('vertex:contract-list')
  ipcMain.handle('vertex:contract-resolve', (_event, id: VertexContractId) => resolveVertexContract(id))
  ipcMain.handle('vertex:contract-list', () => listVertexContracts())
"""
    ipc = ipc.replace(func_anchor, handler, 1)

    # Preload bridge is intentionally separate from workstation/VRA execution APIs.
    bridge = f"""

// {MARKER}: read-only canonical contract access for Portal renderer components.
contextBridge.exposeInMainWorld('vertexContractCatalog', Object.freeze({{
  resolve: (id: 'vertex.vra.issue/1' | 'vertex.evidence.read/1') =>
    ipcRenderer.invoke('vertex:contract-resolve', id),
  list: () =>
    ipcRenderer.invoke('vertex:contract-list')
}}))
"""
    preload = preload.rstrip() + bridge + "\n"

    write(IPC, ipc)
    write(PRELOAD, preload)

    doc = """# Vertex Contract Catalog API

Read-only Portal bridge for the active shared contract catalog.

Renderer access:

- `window.vertexContractCatalog.resolve('vertex.vra.issue/1')`
- `window.vertexContractCatalog.resolve('vertex.evidence.read/1')`
- `window.vertexContractCatalog.list()`

This API does not mutate Registry, Workstation, Evidence, VRA files, Human Gate, or routing state.

Its only purpose is to make canonical contract truth retrievable instead of reconstructed from LLM memory.
"""
    write(DOC, doc)

    ipc_now = read(IPC)
    pre_now = read(PRELOAD)
    checks = {
        "CORE_IMPORT": "resolveVertexContract" in ipc_now and "listVertexContracts" in ipc_now,
        "RESOLVE_HANDLER": "vertex:contract-resolve" in ipc_now,
        "LIST_HANDLER": "vertex:contract-list" in ipc_now,
        "PRELOAD_GLOBAL": "vertexContractCatalog" in pre_now,
        "VRA_CONTRACT_ID": "vertex.vra.issue/1" in pre_now,
        "EVIDENCE_CONTRACT_ID": "vertex.evidence.read/1" in pre_now,
        "READ_ONLY_NO_MUTATOR": "setVertexContract" not in pre_now and "updateVertexContract" not in pre_now,
    }
    for name, ok in checks.items():
        safe(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    if run_npm(["run","typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run_npm(["run","build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    safe("REGISTRY_MUTATION=ZERO")
    safe("WORKSTATION_MUTATION=ZERO")
    safe("RETURN_ROUTER_MUTATION=ZERO")
    safe("HUMAN_GATE_MUTATION=ZERO")
    safe("CONTRACT_API_MODE=READ_ONLY")
    safe("CONTRACT_CATALOG_API_000036V2=PASS")

except Exception:
    write(IPC, ipc0)
    write(PRELOAD, pre0)
    if DOC.exists():
        DOC.unlink()
    safe("TRANSACTION_ROLLBACK=RESTORED")
    raise
