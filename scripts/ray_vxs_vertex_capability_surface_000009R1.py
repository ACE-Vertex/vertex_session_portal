from pathlib import Path
import hashlib
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
WORKSTATION = Path(r"G:\Vertex_Project\Development\vertex_workstation")

def safe(value):
    return str(value).encode("ascii", "backslashreplace").decode("ascii")

def emit(*parts):
    print(" ".join(safe(p) for p in parts))

def sha256(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_files(root: Path):
    allowed = {
        ".ts", ".tsx", ".js", ".jsx", ".rs", ".py",
        ".json", ".toml", ".md", ".ps1", ".cmd"
    }
    skip = {
        "node_modules", "target", ".git", "dist", "out",
        "runtime", ".vite", "coverage"
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip for part in path.parts):
            continue
        if path.suffix.lower() not in allowed:
            continue
        yield path

def scan(root: Path, label: str, patterns, limit=140):
    emit("")
    emit("===", label, "===")
    if not root.is_dir():
        emit("ROOT_PRESENT=NO", root)
        return []

    emit("ROOT_PRESENT=YES", root)
    hits = []

    for path in source_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue

        for line_no, line in enumerate(text.splitlines(), 1):
            matched = []
            for name, regex in patterns:
                if re.search(regex, line, re.IGNORECASE):
                    matched.append(name)
            if not matched:
                continue

            hits.append({
                "file": str(path.relative_to(root)),
                "line": line_no,
                "labels": matched,
                "text": line.strip(),
            })

    emit("MATCHES=" + str(len(hits)))
    for item in hits[:limit]:
        emit(
            item["file"]
            + ":"
            + str(item["line"])
            + " ["
            + ",".join(item["labels"])
            + "] "
            + item["text"]
        )
    if len(hits) > limit:
        emit("TRUNCATED=" + str(len(hits) - limit))

    return hits

portal_patterns = [
    ("VRA_LIST", r"\bvra\s+list\b|vra.*list"),
    ("VRA_DISPATCH", r"\bvra\s+dispatch\b|dispatch.*vra|vra.*dispatch"),
    ("VRA_CAPTURE", r"vra.*capture|capture.*vra"),
    ("VRA_STAGING", r"staging|_incoming"),
    ("HUMAN_GATE", r"HUMAN_APPLY|human.*approval|human.*gate"),
    ("RETURN_QUEUE", r"return-queue|return_channel"),
    ("EVIDENCE", r"\bevidence\b"),
    ("RAY", r"\bray\b|deep ray|x-ray|xray"),
    ("VXS", r"\bvxs\b"),
]

workstation_patterns = [
    ("HTTP_ROUTE", r'/(?:v1/)?(?:jobs|lanes|status|health|evidence)\b'),
    ("ROUTER_ROUTE", r'route|router|endpoint'),
    ("HEADLESS", r'headless|127\.0\.0\.1|TcpListener|axum|warp|hyper'),
    ("JOB_REGISTRY", r'JobRegistry|job_registry|job registry'),
    ("JOB_ID", r'\bjob_id\b'),
    ("EVIDENCE", r'\bevidence\b'),
    ("LANE", r'lane.*status|lane.*list|allocation'),
    ("VRA", r'\bvra\b|vra_manifest'),
    ("SERVER", r'\bserver\b|serve\b'),
    ("CLI", r'\bcli\b|clap|subcommand'),
]

ray_patterns = [
    ("RAY", r"\bray\b|deep ray|x-ray|xray"),
    ("VERIFY", r"\bverify\b|verification"),
    ("OBSERVE", r"observe|observation|inspect"),
]

portal_hits = scan(PORTAL, "SESSION PORTAL CAPABILITY SURFACE", portal_patterns)
ws_hits = scan(WORKSTATION, "WORKSTATION CAPABILITY SURFACE", workstation_patterns)

emit("")
emit("=== RAY / OBSERVATION ASSET SWEEP ===")
ray_hits = []
for root, root_label in ((PORTAL, "portal"), (WORKSTATION, "workstation")):
    if not root.is_dir():
        continue
    for path in source_files(root):
        rel = str(path.relative_to(root))
        if not re.search(r"ray|verify|observ|inspect", rel, re.IGNORECASE):
            continue
        ray_hits.append((root_label, rel, sha256(path), path.stat().st_size))

emit("RAY_ASSETS=" + str(len(ray_hits)))
for root_label, rel, digest, size in ray_hits[:120]:
    emit(f"{root_label}:{rel} bytes={size} sha256={digest}")
if len(ray_hits) > 120:
    emit("TRUNCATED=" + str(len(ray_hits) - 120))

emit("")
emit("=== KNOWN TARGET FILE HASHES ===")
known = [
    PORTAL / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts",
    PORTAL / "src" / "main" / "shell" / "vertex-shell-service.ts",
    PORTAL / "src" / "main" / "shell" / "vxs" / "vxs-command-registry.ts",
    PORTAL / "src" / "main" / "shell" / "vxs" / "vxs-dev-capabilities.ts",
    WORKSTATION / "src-tauri" / "src" / "main.rs",
    WORKSTATION / "src-tauri" / "src" / "lane_manager.rs",
    WORKSTATION / "src-tauri" / "src" / "lane_scheduler.rs",
    WORKSTATION / "src-tauri" / "src" / "vra_manifest.rs",
]
for path in known:
    if path.is_file():
        root = PORTAL if str(path).startswith(str(PORTAL)) else WORKSTATION
        emit(
            str(path.relative_to(root))
            + " sha256="
            + sha256(path)
            + " bytes="
            + str(path.stat().st_size)
        )
    else:
        emit(str(path) + " MISSING")

emit("")
emit("=== CANDIDATE CONTRACT SUMMARY ===")

def has(hits, label):
    return any(label in item["labels"] for item in hits)

summary = {
    "portal_vra_list_anchor": has(portal_hits, "VRA_LIST"),
    "portal_vra_dispatch_anchor": has(portal_hits, "VRA_DISPATCH"),
    "portal_return_queue_anchor": has(portal_hits, "RETURN_QUEUE"),
    "portal_evidence_anchor": has(portal_hits, "EVIDENCE"),
    "portal_ray_anchor": has(portal_hits, "RAY"),
    "workstation_http_route_anchor": has(ws_hits, "HTTP_ROUTE"),
    "workstation_headless_anchor": has(ws_hits, "HEADLESS"),
    "workstation_job_registry_anchor": has(ws_hits, "JOB_REGISTRY"),
    "workstation_evidence_anchor": has(ws_hits, "EVIDENCE"),
    "workstation_lane_anchor": has(ws_hits, "LANE"),
    "workstation_cli_anchor": has(ws_hits, "CLI"),
    "ray_asset_count": len(ray_hits),
}
emit(json.dumps(summary, ensure_ascii=True, separators=(",", ":")))

emit("")
emit("PRODUCTION_SOURCE_MUTATION=NONE")
emit("PORTAL_PRODUCTION_MUTATION=NONE")
emit("WORKSTATION_PRODUCTION_MUTATION=NONE")
emit("READ_ONLY_RAY=PASS")

if not PORTAL.is_dir() or not WORKSTATION.is_dir():
    raise SystemExit(2)

raise SystemExit(0)
