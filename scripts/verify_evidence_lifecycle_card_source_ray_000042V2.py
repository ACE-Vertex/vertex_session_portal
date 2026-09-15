from pathlib import Path
import re, sys, traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
TARGETS = [
    "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
    "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css",
    "src/shared/contracts.ts",
    "src/main/vra/vra-dispatch-service.ts",
    "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts",
]

TERMS = [
    "workstationEvidenceState",
    "workstationEvidenceReturnState",
    "evidenceIdentity",
    "evidenceReturned",
    "returnedAt",
    "RETURN_QUEUED",
    "RETURNED",
    "AVAILABLE",
    "acknowledgeVraEvidenceDelivery",
    "VERA_EVIDENCE_RETURN_RESULT_EVENT",
    "cardErrorCopy",
    "removeCard",
    "dispatchPhase",
    "humanApproval",
    "allocatedLane",
]

def safe(v=""):
    print(str(v).encode("ascii","backslashreplace").decode("ascii"))

def merge(ranges, total):
    out=[]
    for a,b in sorted(ranges):
        a=max(1,a); b=min(total,b)
        if not out or a > out[-1][1]+1:
            out.append([a,b])
        else:
            out[-1][1]=max(out[-1][1],b)
    return out

try:
    for rel in TARGETS:
        path = ROOT / rel
        if not path.exists():
            safe(f"FILE={rel} EXISTS=FALSE")
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        safe(f"FILE={rel} EXISTS=TRUE LINES={len(lines)}")
        hits=[]
        for i,line in enumerate(lines,1):
            if any(term.lower() in line.lower() for term in TERMS):
                hits.append(i)
        safe(f"HITS={hits[:120]}")
        ranges = merge([(h-18,h+32) for h in hits[:45]], len(lines))
        for idx,(a,b) in enumerate(ranges,1):
            safe(f"--- WINDOW {idx} {a}-{b} ---")
            for i in range(a,b+1):
                safe(f"{i:05d}|{lines[i-1]}")
        safe("--- END FILE ---")

    safe("READ_ONLY=PASS")
    safe("PRODUCTION_MUTATION=ZERO")
    safe("PURPOSE=LOCATE_EXACT_CARD_LIFECYCLE_RENDER_AND_ACK_ANCHORS")
except Exception as exc:
    safe("RAY_SCRIPT_FAILURE=YES")
    safe(f"TYPE={type(exc).__name__}")
    safe(f"MESSAGE={exc}")
    for line in traceback.format_exc().splitlines():
        safe(line)
    raise
