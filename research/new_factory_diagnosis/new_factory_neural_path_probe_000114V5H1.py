from __future__ import annotations

from pathlib import Path
import re
import socket
import sys

# Old Works console commonly uses cp932. Never allow source Unicode to abort Ray.
try:
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
except Exception:
    pass

DEV = Path(r"G:\Vertex_Project\Development")
PORTAL = DEV / "vertex_session_portal"
WS = DEV / "vertex_workstation"

TEXT_EXTS = {
    ".rs", ".ts", ".tsx", ".js", ".jsx", ".json", ".toml",
    ".py", ".md", ".yml", ".yaml", ".cmd", ".ps1"
}

PATTERNS = [
    ("HTTP_JOB_ROUTE", re.compile(r"/v1/jobs\b", re.I)),
    ("WORKSTATION_PORT", re.compile(r"\b47832\b")),
    ("LOOPBACK_BIND", re.compile(r"127\.0\.0\.1")),
    ("INCOMING", re.compile(r"_incoming\b", re.I)),
    ("HUMAN_APPLY", re.compile(r"HUMAN_APPLY", re.I)),
    ("RECEIVING_GATEWAY", re.compile(r"ReceivingGateway|receiving_gateway|receiving gateway", re.I)),
    ("PUBLISH_APPROVED", re.compile(r"publishApprovedCard", re.I)),
    ("EXPORT_VRA", re.compile(r"exportVraCard", re.I)),
    ("WORKSTATION_LAST_ERROR", re.compile(r"workstationLastError", re.I)),
    ("LANE_POLICY", re.compile(r"lane_policy|LanePolicy", re.I)),
    ("LANE_ALLOC", re.compile(r"allocated_lane|lane allocation|allocate_lane", re.I)),
    ("EVIDENCE", re.compile(r"evidence", re.I)),
    ("JOB_REGISTRY", re.compile(r"JobRegistry|job_registry", re.I)),
    ("DISPATCH", re.compile(r"dispatch", re.I)),
]

SKIP_DIRS = {
    ".git", "node_modules", "target", "dist", "build", ".next",
    "coverage", "backups", "MIGRATION_BACKUPS"
}

def safe(s: object) -> str:
    return str(s).encode("ascii", "backslashreplace").decode("ascii")

def iter_files(root: Path):
    if not root.exists():
        return
    for p in root.rglob("*"):
        try:
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix.lower() not in TEXT_EXTS:
                continue
            if p.stat().st_size > 2_000_000:
                continue
            yield p
        except OSError:
            continue

def scan(root: Path, label: str):
    print(f"=== {label} ===")
    print("ROOT=" + safe(root))
    if not root.exists():
        print("ROOT_EXISTS=NO")
        return
    print("ROOT_EXISTS=YES")
    hits = 0
    files_scanned = 0
    for p in iter_files(root):
        files_scanned += 1
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = p.relative_to(root)
        for lineno, line in enumerate(text.splitlines(), start=1):
            for tag, rx in PATTERNS:
                if rx.search(line):
                    clipped = line.strip()
                    if len(clipped) > 220:
                        clipped = clipped[:217] + "..."
                    print(f"HIT|{tag}|{safe(rel)}|{lineno}|{safe(clipped)}")
                    hits += 1
                    if hits >= 320:
                        print("HIT_LIMIT_REACHED=YES")
                        print(f"FILES_SCANNED={files_scanned}")
                        print(f"HITS={hits}")
                        return
    print(f"FILES_SCANNED={files_scanned}")
    print(f"HITS={hits}")

def probe_port():
    print("=== NEW_WORKSTATION_RUNTIME ===")
    try:
        with socket.create_connection(("127.0.0.1", 47832), timeout=0.35):
            print("TCP_127_0_0_1_47832=OPEN")
            print("EXPECTED_WHILE_SLEEPING=NO")
    except (ConnectionRefusedError, TimeoutError, socket.timeout, OSError) as exc:
        print("TCP_127_0_0_1_47832=CLOSED_OR_SLEEPING")
        print("SOCKET_ERROR=" + safe(repr(exc)))
        print("EXPECTED_WHILE_SLEEPING=YES")

def main():
    print("VERTEX_NEW_FACTORY_READONLY_NEURAL_PATH_PROBE_H1=BEGIN")
    print("MODE=READ_ONLY")
    probe_port()
    scan(PORTAL, "SESSION_PORTAL")
    scan(WS, "NEW_WORKSTATION")
    print("VERTEX_NEW_FACTORY_READONLY_NEURAL_PATH_PROBE_H1=PASS")

if __name__ == "__main__":
    main()
