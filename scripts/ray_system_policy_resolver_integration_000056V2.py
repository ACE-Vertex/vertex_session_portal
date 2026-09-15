
from pathlib import Path
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()

TARGETS = [
    "src/shared/system-policy-registry.ts",
    "src/shared/vertex-contract-catalog.ts",
    "src/shared/contracts.ts",
    "src/main/ipc/register-vra-dispatch-ipc.ts",
    "src/main/index.ts",
    "src/preload/index.ts",
]

TERMS = [
    "vertexContractCatalog",
    "contract-resolve",
    "contract-list",
    "contextBridge",
    "ipcRenderer.invoke",
    "registerVraDispatchIpc",
    "getSystemPolicyRecord",
    "listSystemPolicyRecords",
    "window.",
    "declare global",
    "interface Window",
]

def safe(v=""):
    print(str(v).encode("ascii","backslashreplace").decode("ascii"))

def merge(ranges, total):
    merged=[]
    for a,b in sorted(ranges):
        a=max(1,a); b=min(total,b)
        if not merged or a > merged[-1][1] + 1:
            merged.append([a,b])
        else:
            merged[-1][1]=max(merged[-1][1],b)
    return merged

for rel in TARGETS:
    p = ROOT / rel
    safe(f"=== FILE {rel} EXISTS={p.exists()} ===")
    if not p.exists():
        continue
    lines = p.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    hits=[]
    for i,line in enumerate(lines,1):
        if any(term.lower() in line.lower() for term in TERMS):
            hits.append(i)
    safe(f"HITS={hits[:200]}")
    for n,(a,b) in enumerate(merge([(h-18,h+34) for h in hits[:60]], len(lines)),1):
        safe(f"--- WINDOW {n} {a}-{b} ---")
        for i in range(a,b+1):
            safe(f"{i:05d}|{lines[i-1]}")
    safe("=== END FILE ===")

safe("READ_ONLY=PASS")
safe("PRODUCTION_MUTATION=ZERO")
safe("PURPOSE=LOCATE_EXACT_READ_ONLY_POLICY_RESOLVER_API_WIRING")
