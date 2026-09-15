from pathlib import Path
import json, os, re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
INCOMING = Path(r"G:\Vertex_Project\Development\_incoming")
APPDATA = Path(os.environ.get("APPDATA","")) / "vertex-session-portal"

TARGET_ARTIFACT = "vertex-failed-evidence-return-canary-000079V3"
TARGET_JOB = "job-vera03-failed-evidence-return-canary-4b027406-f5d8-4752-a7e9-9d080798b308"
TARGET_CORR = "9d127011-4404-4618-8f8b-9be63c83d246"
TARGET_EVIDENCE = "ws-evidence-5e147d59ecfb5da104d32388f3a33d7c5776d43c6ee967cb164bc25089007a03"

def safe(s):
    return str(s).encode("ascii","backslashreplace").decode("ascii")

def emit(s=""):
    print(safe(s))

def print_marker_block(path, markers, before=16, after=110):
    emit(f"\n=== SOURCE {path.relative_to(ROOT).as_posix()} ===")
    if not path.exists():
        emit("MISSING")
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    seen = set()
    for marker in markers:
        hits = [i for i,l in enumerate(lines) if marker in l]
        emit(f"MARKER={marker} HITS={len(hits)}")
        for idx in hits[:6]:
            key=(idx,marker)
            if key in seen: continue
            seen.add(key)
            start=max(0,idx-before); end=min(len(lines),idx+after)
            emit(f"--- HIT line={idx+1} ---")
            for j in range(start,end):
                emit(f"{j+1:05d}: {lines[j]}")

print_marker_block(
    ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
    ["evidenceResultListener", "evidenceInFlight", "VERA_EVIDENCE_RETURN_EVENT",
     "acknowledgeVraEvidenceDelivery", "EvidenceDeliveryReceipt", "EVIDENCE_RECEIPTS_KEY"]
)
print_marker_block(
    ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    ["deliverWorkstationEvidence", "evidenceReturnListener",
     "VERA_EVIDENCE_RETURN_RESULT_EVENT", "dispatchEvent"]
)
print_marker_block(
    ROOT / "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts",
    ["VERA_EVIDENCE_RETURN_EVENT", "VERA_EVIDENCE_RETURN_RESULT_EVENT",
     "dispatchEvent", "deliveryId"]
)
print_marker_block(
    ROOT / "src/main/vra/vra-dispatch-service.ts",
    ["acknowledgeEvidenceDelivery", "returnedAt", "RETURNED",
     "workstationEvidenceReturnState", "syncAutoRegistryWorkstationLifecycle"]
)

emit("\n=== 000079 DURABLE METADATA ===")
meta = INCOMING / f"{TARGET_ARTIFACT}.vra.meta.json"
emit(f"META_PATH={meta}")
if meta.exists():
    text = meta.read_text(encoding="utf-8", errors="replace")
    emit(text)
else:
    emit("META_MISSING")

emit("\n=== PORTAL DURABLE TRACE SEARCH ===")
needles = [TARGET_ARTIFACT, TARGET_JOB, TARGET_CORR, TARGET_EVIDENCE]
allowed = {".json",".jsonl",".log",".txt"}
matches = 0
if APPDATA.exists():
    for p in APPDATA.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in allowed:
            continue
        try:
            if p.stat().st_size > 20 * 1024 * 1024:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if any(n in text for n in needles):
            emit(f"\nFILE={p}")
            lines=text.splitlines()
            shown=0
            for i,line in enumerate(lines):
                if any(n in line for n in needles):
                    start=max(0,i-2); end=min(len(lines),i+3)
                    for j in range(start,end):
                        emit(f"{j+1:05d}: {lines[j]}")
                    emit("---")
                    shown += 1
                    matches += 1
                    if shown >= 12:
                        break
else:
    emit("APPDATA_PORTAL_ROOT_MISSING")

emit("\n=== SUMMARY ===")
emit(f"TRACE_MATCH_GROUPS={matches}")
emit("PRODUCTION_MUTATION=NONE")
emit("RAY_RESULT=ACK_COMMIT_BOUNDARY_CAPTURED")
raise SystemExit(0)
