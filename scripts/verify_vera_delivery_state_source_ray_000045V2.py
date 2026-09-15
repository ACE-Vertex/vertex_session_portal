from pathlib import Path
import re, sys, traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()

TARGETS = [
    "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts",
    "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
    "src/shared/contracts.ts",
    "src/main/ipc/register-vra-dispatch-ipc.ts",
    "src/main/vra/vra-dispatch-service.ts",
]

TERMS = [
    "VERA_EVIDENCE_RETURN_RESULT_EVENT",
    "vertex-vera-evidence-return-result",
    "injectWorkstationEvidence",
    "acknowledgeVraEvidenceDelivery",
    "evidenceReturnState",
    "workstationEvidenceReturnState",
    "RETURN_QUEUED",
    "RETURNED",
    "delivered",
    "delivery",
    "ack",
    "evidenceId",
    "originSession",
    "cardId",
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
            merged[-1][1] = max(merged[-1][1], b)
    return merged

try:
    for rel in TARGETS:
        path = ROOT / rel
        if not path.exists():
            safe(f"FILE={rel} EXISTS=FALSE")
            continue

        lines = path.read_text(encoding="utf-8-sig").splitlines()
        hits=[]
        for i,line in enumerate(lines,1):
            if any(term.lower() in line.lower() for term in TERMS):
                hits.append(i)

        safe(f"=== FILE {rel} LINES={len(lines)} HITS={hits[:160]} ===")
        ranges = merge([(h-22,h+38) for h in hits[:55]], len(lines))
        for n,(a,b) in enumerate(ranges,1):
            safe(f"--- WINDOW {n} {a}-{b} ---")
            for i in range(a,b+1):
                safe(f"{i:05d}|{lines[i-1]}")
        safe("=== END FILE ===")

    safe("READ_ONLY=PASS")
    safe("PRODUCTION_MUTATION=ZERO")
    safe("PURPOSE=LOCATE_DURABLE_VERA_DELIVERY_AND_ACK_BOUNDARY")
except Exception as exc:
    safe("RAY_SCRIPT_FAILURE=YES")
    safe(f"TYPE={type(exc).__name__}")
    safe(f"MESSAGE={exc}")
    for line in traceback.format_exc().splitlines():
        safe(line)
    raise
