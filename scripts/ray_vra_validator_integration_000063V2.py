
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
    "src/main/ipc/register-system-policy-ipc.ts",
    "src/main/vra/vra-dispatch-service.ts",
    "src/main/ipc/register-vra-dispatch-ipc.ts",
    "src/preload/index.ts",
]

TERMS = [
    "schema_version",
    "authority",
    "vra-routing/1",
    "operations",
    "verification",
    "sha256",
    "manifest",
    "validate",
    "validator",
    "parse",
    "publish",
    "approve",
    "HUMAN_APPLY",
    "origin_vera",
    "origin_session",
    "return_channel",
    "lane_policy",
    "copy",
    "vertexSystemPolicy",
    "resolveActiveSystemPolicy",
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

    safe(f"HITS={hits[:250]}")
    for n,(a,b) in enumerate(merge([(h-20,h+38) for h in hits[:80]], len(lines)),1):
        safe(f"--- WINDOW {n} {a}-{b} ---")
        for i in range(a,b+1):
            safe(f"{i:05d}|{lines[i-1]}")
    safe("=== END FILE ===")

# Broader bounded source name search for validation-related files.
safe("=== VALIDATION RELATED PATHS ===")
count = 0
for p in ROOT.rglob("*"):
    try:
        if not p.is_file():
            continue
        rel = str(p.relative_to(ROOT)).replace("\\","/")
        low = rel.lower()
        if any(token in low for token in ["vra", "validator", "validation", "manifest"]):
            safe(rel)
            count += 1
            if count >= 220:
                break
    except Exception:
        pass

safe("READ_ONLY=PASS")
safe("PRODUCTION_MUTATION=ZERO")
safe("PURPOSE=LOCATE_DETERMINISTIC_VRA_VALIDATOR_INTEGRATION_BOUNDARY")
