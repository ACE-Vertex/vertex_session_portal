from pathlib import Path
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")
INCOMING = Path(r"G:\Vertex_Project\Development\_incoming")
TARGET_ARTIFACT = 'vertex-session-portal-vxs-vertex-capability-pack-000009'
TARGET_JOB = 'job-vera03-vxs-vertex-capability-42f4e345-e5ec-4506-affd-79778057c607'
EXPECTED_SHA256 = '4219224c24b4644d57f8446d374b99e93a4f5b80478029b54181eef7ca208212'
BASE = "http://127.0.0.1:47832"

def safe(v):
    return str(v).encode("ascii", "backslashreplace").decode("ascii")

def emit(*parts):
    print(" ".join(safe(p) for p in parts))

def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def http_get(path):
    url = BASE + path
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=4) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as e:
        return None, repr(e)

def candidate_roots():
    roots = [PORTAL, INCOMING, WORKSTATION]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        local_path = Path(local)
        for name in ["VertexSessionPortal","vertex-session-portal","VertexReceiver","VertexWorkstation","vertex-workstation"]:
            p = local_path / name
            if p.exists():
                roots.append(p)
    return roots

def relevant_files(root: Path):
    if not root.exists():
        return
    skip = {".git","node_modules","target","dist","out","coverage",".vite","__pycache__",".venv","venv"}
    allowed = {".json",".meta",".txt",".log",".ndjson",".jsonl",".vra",".md"}
    count = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            p = Path(base) / name
            count += 1
            if count > 15000:
                return
            if TARGET_ARTIFACT.lower() in name.lower() or TARGET_JOB.lower() in name.lower() or p.suffix.lower() in allowed:
                yield p

emit("=== VXS 000009 REGISTRATION FAILURE RAY 000009R2 ===")
emit("MODE=READ_ONLY")
emit("TARGET_ARTIFACT=" + TARGET_ARTIFACT)
emit("TARGET_JOB=" + TARGET_JOB)
emit("EXPECTED_SHA256=" + EXPECTED_SHA256)
emit("")

emit("=== WORKSTATION CONTROL PLANE ===")
for route in ["/v1/health", f"/v1/jobs/{TARGET_JOB}", f"/v1/jobs/{TARGET_JOB}/evidence"]:
    status, body = http_get(route)
    emit("GET", route, "STATUS=" + str(status))
    emit("BODY=" + body[:5000].replace("\n", " "))
emit("")

emit("=== INCOMING ARTIFACT ===")
incoming_candidates = []
if INCOMING.exists():
    for p in INCOMING.glob(TARGET_ARTIFACT + "*"):
        incoming_candidates.append(p)
        emit("FOUND", p)
        if p.is_file():
            emit("BYTES=" + str(p.stat().st_size))
            try:
                digest = sha256(p)
                emit("SHA256=" + digest)
                emit("SHA_MATCH=" + str(digest.lower() == EXPECTED_SHA256.lower()))
            except Exception as e:
                emit("SHA_ERROR=" + repr(e))
else:
    emit("INCOMING_PRESENT=NO")
emit("INCOMING_MATCH_COUNT=" + str(len(incoming_candidates)))
emit("")

emit("=== TRACE SEARCH ===")
hits = []
for root in candidate_roots():
    emit("ROOT", root, "PRESENT=" + str(root.exists()))
    if not root.exists():
        continue
    for p in relevant_files(root):
        name_hit = TARGET_ARTIFACT.lower() in p.name.lower() or TARGET_JOB.lower() in p.name.lower()
        content_hit = False
        text = None
        if p.suffix.lower() != ".vra":
            try:
                if p.stat().st_size <= 4 * 1024 * 1024:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    content_hit = TARGET_ARTIFACT in text or TARGET_JOB in text or EXPECTED_SHA256 in text
            except Exception:
                pass
        if not name_hit and not content_hit:
            continue
        item = {"root": str(root), "path": str(p), "name_hit": name_hit, "content_hit": content_hit}
        hits.append(item)
        emit("HIT", json.dumps(item, ensure_ascii=True))
        if text is not None:
            shown = 0
            for i, line in enumerate(text.splitlines(), 1):
                lower = line.lower()
                if TARGET_ARTIFACT in line or TARGET_JOB in line or EXPECTED_SHA256 in line or "workstation_last_error" in lower or "registration" in lower or "incoming" in lower:
                    emit(f"  L{i}:", line[:1500])
                    shown += 1
                    if shown >= 12:
                        break
emit("TRACE_HIT_COUNT=" + str(len(hits)))
emit("")

emit("=== BOUNDARY CLASSIFICATION ===")
incoming_vra = next((p for p in incoming_candidates if p.suffix.lower() == ".vra"), None)
job_status, _job_body = http_get(f"/v1/jobs/{TARGET_JOB}")
if incoming_vra is None:
    emit("LIKELY_BOUNDARY=PORTAL_PUBLISH_OR_ATOMIC_INCOMING_COMMIT")
elif sha256(incoming_vra).lower() != EXPECTED_SHA256.lower():
    emit("LIKELY_BOUNDARY=INCOMING_ARTIFACT_SHA_MISMATCH")
elif job_status == 404:
    emit("LIKELY_BOUNDARY=WORKSTATION_JOB_REGISTRATION_REJECTED_OR_NOT_SUBMITTED")
elif job_status == 200:
    emit("LIKELY_BOUNDARY=POST_REGISTRATION_PRE_ALLOCATION_OR_REGISTRY_STATE")
else:
    emit("LIKELY_BOUNDARY=UNRESOLVED")
    emit("JOB_STATUS=" + str(job_status))
emit("")
emit("PRODUCTION_MUTATION=NONE")
emit("HTTP_METHODS=GET_ONLY")
emit("HUMAN_GATE_CHANGE=NONE")
emit("WORKSTATION_CHANGE=NONE")
emit("READ_ONLY_RAY=PASS")
raise SystemExit(0)
