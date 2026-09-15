from pathlib import Path
import hashlib, json, os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
DEV = Path(r"G:\Vertex_Project\Development")
PORTAL = DEV / "vertex_session_portal"
VRA_MANIFEST = DEV / "vra_manifest" / "VRA_CANONICAL_MANIFEST_vra-1_000150V5.json"

TARGET_FILES = [
    "src/shared/contracts.ts",
    "src/shared/vertex-contract-catalog.ts",
    "src/main/vra/vra-dispatch-service.ts",
    "src/main/ipc/register-vra-dispatch-ipc.ts",
    "src/main/observability/evidence-return-tap.ts",
    "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts",
    "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
    "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
    "src/main/index.ts",
]

TERMS = [
    "Registry",
    "policy",
    "contract",
    "HUMAN_APPLY",
    "RETURN_QUEUED",
    "RETURNED",
    "Evidence",
    "acknowledgeEvidenceDelivery",
    "acknowledgeVraEvidenceDelivery",
    "Firmware",
    "Change Gate",
    "Registrar",
    "Journal",
    "SQLite",
    "VLog",
    "lifecycle",
    "origin_session",
    "return_channel",
]

def emit(k, v):
    print(f"{k}={str(v).encode('ascii','backslashreplace').decode('ascii')}")

def read_text(p: Path, max_bytes=4_000_000):
    try:
        if not p.exists() or not p.is_file():
            return None
        if p.stat().st_size > max_bytes:
            return None
        return p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return None

def sha256_file(p: Path):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def windows(lines, hit_lines, before=10, after=18, max_windows=12):
    ranges = []
    for h in hit_lines:
        a = max(1, h-before)
        b = min(len(lines), h+after)
        if not ranges or a > ranges[-1][1] + 1:
            ranges.append([a,b])
        else:
            ranges[-1][1] = max(ranges[-1][1], b)
        if len(ranges) >= max_windows:
            break
    return ranges

emit("RAY", "VERTEX_SYSTEM_POLICY_LAYER_FOUNDATION_000050V2")
emit("MODE", "READ_ONLY_OBSERVATION")
emit("PORTAL_ROOT", PORTAL)
emit("PRODUCTION_MUTATION", "ZERO")

# 1) Canonical VRA manifest must be observed, not reconstructed from memory.
emit("SECTION", "CANONICAL_VRA_MANIFEST")
emit("CANONICAL_MANIFEST_EXISTS", VRA_MANIFEST.exists())
if VRA_MANIFEST.exists():
    emit("CANONICAL_MANIFEST_SHA256", sha256_file(VRA_MANIFEST))
    raw = read_text(VRA_MANIFEST)
    if raw:
        try:
            data = json.loads(raw)
            emit("CANONICAL_SCHEMA_VERSION", data.get("schema_version"))
            emit("CANONICAL_AUTHORITY", data.get("authority"))
            routing = data.get("routing") or {}
            emit("CANONICAL_ROUTING_CONTRACT", routing.get("contract_version"))
            ops = data.get("operations") or []
            emit("CANONICAL_OPERATION_COUNT", len(ops))
            emit("CANONICAL_OPERATION_NAMES", ",".join(str(x.get("op")) for x in ops if isinstance(x, dict)))
        except Exception as exc:
            emit("CANONICAL_PARSE_ERROR", type(exc).__name__)

# 2) Exact current source windows.
emit("SECTION", "PORTAL_SOURCE")
for rel in TARGET_FILES:
    p = PORTAL / rel
    txt = read_text(p)
    emit("FILE", rel)
    emit("EXISTS", p.exists())
    if txt is None:
        continue
    emit("SHA256", sha256_file(p))
    lines = txt.splitlines()
    hits = []
    for i, line in enumerate(lines, 1):
        if any(term.lower() in line.lower() for term in TERMS):
            hits.append(i)
    emit("HIT_COUNT", len(hits))
    emit("HIT_LINES", ",".join(map(str, hits[:80])))
    for wi,(a,b) in enumerate(windows(lines, hits),1):
        emit("WINDOW", f"{wi}:{a}-{b}")
        for n in range(a,b+1):
            print(f"{rel}:{n:05d}|{lines[n-1].encode('ascii','backslashreplace').decode('ascii')}")

# 3) Search project source for Firmware Change Gate / System Policy remnants.
emit("SECTION", "FIRMWARE_CHANGE_GATE_AND_POLICY_SURFACE")
surface_hits = []
for p in PORTAL.rglob("*"):
    try:
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".ts",".tsx",".js",".json",".md",".css"):
            continue
        if any(part in ("node_modules","dist","out","build",".git") for part in p.parts):
            continue
        txt = read_text(p, 1_500_000)
        if not txt:
            continue
        low = txt.lower()
        score_terms = []
        for term in ("firmware change gate","system policy","policy registry","policy resolver",
                     "firmware registrar","signed approval","change proposal"):
            if term in low:
                score_terms.append(term)
        if score_terms:
            surface_hits.append((str(p.relative_to(PORTAL)), score_terms))
    except Exception:
        pass

emit("POLICY_SURFACE_FILE_COUNT", len(surface_hits))
for rel, terms in surface_hits[:80]:
    emit("POLICY_SURFACE_FILE", rel + "|" + ",".join(terms))

# 4) Detect R2 implementation status without claiming success merely from source presence.
emit("SECTION", "FIRMWARE_GATE_R2_STATUS")
r2_tokens = [
    "000151V3R2",
    "FIRMWARE_CHANGE_GATE",
    "FirmwareChangeGate",
    "firmware-change-gate",
]
r2_files = []
for p in PORTAL.rglob("*"):
    try:
        if not p.is_file() or p.suffix.lower() not in (".ts",".tsx",".js",".json",".md",".py"):
            continue
        if any(part in ("node_modules","dist","out","build",".git") for part in p.parts):
            continue
        txt = read_text(p, 1_500_000)
        if txt and any(tok.lower() in txt.lower() for tok in r2_tokens):
            r2_files.append(str(p.relative_to(PORTAL)))
    except Exception:
        pass
emit("R2_SOURCE_HIT_COUNT", len(r2_files))
for rel in r2_files[:80]:
    emit("R2_SOURCE_HIT", rel)
emit("R2_VERIFIED_CLAIM", "NOT_INFERRED_FROM_SOURCE")

# 5) Registry / SQLite / Journal topology.
emit("SECTION", "REGISTRY_SQLITE_JOURNAL")
topology = []
for p in PORTAL.rglob("*"):
    try:
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".ts",".tsx",".js",".json",".md",".sql"):
            continue
        if any(part in ("node_modules","dist","out","build",".git") for part in p.parts):
            continue
        txt = read_text(p, 1_500_000)
        if not txt:
            continue
        low = txt.lower()
        tags = []
        for label, needle in (
            ("SQLITE","sqlite"),
            ("REGISTRY","registry"),
            ("JOURNAL","journal"),
            ("VLOG","vlog"),
            ("RETURN_GUARD","return guard"),
            ("RETURN_STATE","return_queued"),
        ):
            if needle in low:
                tags.append(label)
        if tags:
            topology.append((str(p.relative_to(PORTAL)), tags))
    except Exception:
        pass
emit("TOPOLOGY_FILE_COUNT", len(topology))
for rel,tags in topology[:120]:
    emit("TOPOLOGY_FILE", rel + "|" + ",".join(tags))

# 6) Placement evidence: existing Contract Catalog.
catalog = PORTAL / "src/shared/vertex-contract-catalog.ts"
emit("SECTION", "CONTRACT_CATALOG")
emit("CONTRACT_CATALOG_EXISTS", catalog.exists())
if catalog.exists():
    txt = read_text(catalog) or ""
    emit("HAS_VRA_ISSUE_CONTRACT", "vertex.vra.issue/1" in txt)
    emit("HAS_EVIDENCE_READ_CONTRACT", "vertex.evidence.read/1" in txt)
    emit("CATALOG_SHA256", sha256_file(catalog))

# 7) Report bounded conclusions based only on observed source existence.
emit("SECTION", "BOUNDARY_CONCLUSIONS")
emit("POLICY_LAYER_PRODUCTION_IMPLEMENTATION", "DO_NOT_ASSUME")
emit("PHASE1_CANDIDATE", "POLICY_REGISTRY_FOUNDATION")
emit("FIRST_POLICY_CANDIDATE", "vertex.vra.issue/1.0.0")
emit("REUSE_DECISION", "DEFER_UNTIL_RAY_OUTPUT_REVIEW")
emit("NEW_PRODUCTION_WRITE", "NONE")
emit("RAY_COMPLETE", "PASS")
