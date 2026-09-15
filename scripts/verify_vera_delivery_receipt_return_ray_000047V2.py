from pathlib import Path
import os, json, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
DEV = Path(r"G:\Vertex_Project\Development")
WS = DEV / "vertex_workstation"
INCOMING = DEV / "_incoming"
TARGET_ARTIFACT = 'vertex-session-portal-vera-delivery-receipt-card-000046V2'
TARGET_JOB = 'job-vera02-vera-delivery-receipt-card-cf9a1320-14a1-40b5-9efd-15f32c96bdc2'
MARKER = "VERTEX_VERA_DELIVERY_RECEIPT_CARD_000046V2"

def emit(k, v):
    print(f"{k}={v}")

def safe_read_text(p, limit=2_000_000):
    try:
        if not p.is_file() or p.stat().st_size > limit:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

emit("RAY", "VERA_DELIVERY_RECEIPT_RETURN_000047V2")
emit("AUTHORITY", "READ_ONLY_OBSERVATION")
emit("TARGET_ARTIFACT", TARGET_ARTIFACT)
emit("TARGET_JOB", TARGET_JOB)

# A. Did production patch land?
lane_ts = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
ts = safe_read_text(lane_ts) or ""
emit("PATCH_MARKER_PRESENT", MARKER in ts)
emit("RECEIPT_STORAGE_PRESENT", "vertex.portal.evidence-delivery.receipts.v1" in ts)
emit("ACK_CALL_PRESENT", "acknowledgeVraEvidenceDelivery" in ts)
emit("PORTAL_ACK_LABEL_PRESENT", "PORTAL ACK" in ts)
emit("VERA_LABEL_PRESENT", "VERA" in ts and "recordVeraDeliveryReceipt" in ts)

# B. Publication boundary: _incoming and sidecars.
incoming_hits = []
if INCOMING.exists():
    for p in INCOMING.glob("*"):
        if TARGET_ARTIFACT in p.name or TARGET_JOB in p.name:
            incoming_hits.append(p)
emit("INCOMING_HIT_COUNT", len(incoming_hits))
for p in incoming_hits[:20]:
    emit("INCOMING_HIT", str(p))
    txt = safe_read_text(p)
    if txt and p.suffix.lower() in (".json", ".txt"):
        compact = " ".join(txt.split())
        emit("INCOMING_TEXT", compact[:1800])

# C. Workstation runtime durable facts.
runtime = WS / "runtime"
runtime_name_hits = []
runtime_content_hits = []

if runtime.exists():
    for p in runtime.rglob("*"):
        try:
            if p.is_file():
                name = p.name
                full = str(p)
                if TARGET_ARTIFACT in name or TARGET_ARTIFACT in full or TARGET_JOB in name or TARGET_JOB in full:
                    runtime_name_hits.append(p)
                    continue

                if p.suffix.lower() in (".json", ".log", ".txt") and p.stat().st_size <= 2_000_000:
                    txt = safe_read_text(p)
                    if txt and (TARGET_ARTIFACT in txt or TARGET_JOB in txt):
                        runtime_content_hits.append(p)
        except Exception:
            pass

emit("WS_RUNTIME_NAME_HITS", len(runtime_name_hits))
for p in runtime_name_hits[:40]:
    emit("WS_NAME_HIT", str(p))

emit("WS_RUNTIME_CONTENT_HITS", len(runtime_content_hits))
for p in runtime_content_hits[:40]:
    emit("WS_CONTENT_HIT", str(p))

# D. Parse strongest Workstation evidence JSON if it exists.
evidence_files = []
for p in runtime_name_hits + runtime_content_hits:
    if p.name == "verification-evidence.json":
        evidence_files.append(p)

# Also search stage dirs by artifact, because file itself has generic name.
if runtime.exists():
    for p in runtime.glob(f"lanes/lane-*/evidence/stage-{TARGET_ARTIFACT}*"):
        ev = p / "verification-evidence.json"
        if ev.exists():
            evidence_files.append(ev)

dedup = []
seen = set()
for p in evidence_files:
    s = str(p)
    if s not in seen:
        seen.add(s); dedup.append(p)
evidence_files = dedup

emit("VERIFICATION_EVIDENCE_COUNT", len(evidence_files))
for p in evidence_files[:10]:
    emit("VERIFICATION_EVIDENCE_PATH", str(p))
    txt = safe_read_text(p)
    if txt:
        try:
            data = json.loads(txt)
            emit("VERIFY_SUCCESS", data.get("success"))
            emit("VERIFY_FINAL_STATE", data.get("final_state"))
            cmds = data.get("commands") or []
            emit("VERIFY_COMMAND_COUNT", len(cmds))
            if cmds:
                emit("VERIFY_EXIT_CODE", cmds[-1].get("exit_code"))
                emit("VERIFY_TIMED_OUT", cmds[-1].get("timed_out"))
            emit("VERIFY_WRITE_LOCK_RELEASED", data.get("write_lock_released"))
        except Exception as e:
            emit("VERIFY_PARSE_ERROR", type(e).__name__)

# E. Search Portal durable userData-like JSON for this exact artifact/job.
user_roots = []
for env_name in ("APPDATA", "LOCALAPPDATA"):
    val = os.environ.get(env_name)
    if val:
        base = Path(val)
        for cand in (
            base / "vertex-session-portal",
            base / "Vertex Session Portal",
            base / "vertex_session_portal",
            base / "VertexSessionPortal",
        ):
            if cand.exists():
                user_roots.append(cand)

emit("PORTAL_USERDATA_ROOTS", len(user_roots))
portal_hits = []
scanned = 0
for base in user_roots:
    for p in base.rglob("*"):
        if scanned >= 3000:
            break
        try:
            if not p.is_file():
                continue
            scanned += 1
            if p.suffix.lower() not in (".json", ".jsonl", ".txt"):
                continue
            txt = safe_read_text(p, 1_000_000)
            if txt and (TARGET_ARTIFACT in txt or TARGET_JOB in txt):
                portal_hits.append(p)
        except Exception:
            pass

emit("PORTAL_USERDATA_SCANNED", scanned)
emit("PORTAL_DURABLE_HITS", len(portal_hits))
for p in portal_hits[:30]:
    emit("PORTAL_DURABLE_HIT", str(p))
    txt = safe_read_text(p)
    if txt:
        compact = " ".join(txt.split())
        emit("PORTAL_DURABLE_TEXT", compact[:2200])

# F. Boundary classification based only on durable observations.
if evidence_files:
    emit("FIRST_BOUNDARY_CLASS", "WORKSTATION_EVIDENCE_EXISTS__CHECK_PORTAL_RETURN_DELIVERY_ACK")
elif runtime_name_hits or runtime_content_hits:
    emit("FIRST_BOUNDARY_CLASS", "WORKSTATION_RUNTIME_SEES_JOB__NO_VERIFICATION_EVIDENCE_FOUND")
elif incoming_hits:
    emit("FIRST_BOUNDARY_CLASS", "PORTAL_PUBLISHED__WORKSTATION_RUNTIME_NO_MATCH")
else:
    emit("FIRST_BOUNDARY_CLASS", "NO_PUBLICATION_OR_RUNTIME_FACT_FOUND")

emit("MUTATION", "ZERO")
emit("VERA_DELIVERY_RECEIPT_RETURN_RAY_000047V2", "PASS")
