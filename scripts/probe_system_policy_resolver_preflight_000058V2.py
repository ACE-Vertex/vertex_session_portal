
from pathlib import Path
import re, sys

ROOT = Path.cwd()
POLICY = ROOT / "src/shared/system-policy-registry.ts"
MAIN_INDEX = ROOT / "src/main/index.ts"
PRELOAD = ROOT / "src/preload/index.ts"
IPC_FILE = ROOT / "src/main/ipc/register-system-policy-ipc.ts"
MARKER = "VERTEX_SYSTEM_POLICY_RESOLVER_000057V2"

# Exit-code contract:
# 0  = all known 000057 preconditions/anchors are satisfied
# 21 = Phase 1 policy registry missing
# 22 = Phase 1 active vertex.vra.issue/1.0.0 missing
# 23 = Phase 1 read-only guard missing
# 24 = 000057 marker already exists in policy source
# 25 = 000057 marker already exists in main source
# 26 = 000057 marker already exists in preload source
# 27 = register-system-policy-ipc.ts already exists
# 28 = main import region not found
# 29 = main IPC registration anchor not found
# 30 = preload vertexSystemPolicy API already exists
# 31 = preload lacks contextBridge/ipcRenderer symbols
# 32 = vertexContractCatalog exposure found but block terminator not found
# 33 = main/preload/policy source unreadable
#
# Read-only probe: no production mutation.

def read(p):
    try:
        return p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return None

policy = read(POLICY)
main = read(MAIN_INDEX)
preload = read(PRELOAD)

if policy is None or main is None or preload is None:
    sys.exit(33)

if "SYSTEM_POLICY_REGISTRY_SCHEMA" not in policy:
    sys.exit(21)

if "vertex.vra.issue" not in policy or "1.0.0" not in policy:
    sys.exit(22)

if "NO_POLICY_MUTATION_API_IN_PHASE1" not in policy:
    sys.exit(23)

if MARKER in policy:
    sys.exit(24)
if MARKER in main:
    sys.exit(25)
if MARKER in preload:
    sys.exit(26)

if IPC_FILE.exists():
    sys.exit(27)

import_matches = list(re.finditer(r"^import .+$", main, flags=re.M))
if not import_matches:
    sys.exit(28)

anchor = re.search(r"^[ \t]*registerVraDispatchIpc\([^\n]*\)[ \t]*$", main, flags=re.M)
if anchor is None:
    generic = re.search(r"^(?P<indent>[ \t]*)register[A-Za-z0-9_]+Ipc\([^\n]*\)[ \t]*$", main, flags=re.M)
    if generic is None:
        sys.exit(29)

if "vertexSystemPolicy" in preload:
    sys.exit(30)

if "contextBridge" not in preload or "ipcRenderer" not in preload:
    sys.exit(31)

cat_pos = preload.find("contextBridge.exposeInMainWorld('vertexContractCatalog'")
if cat_pos >= 0:
    end = preload.find("\n})", cat_pos)
    if end < 0:
        sys.exit(32)

sys.exit(0)
