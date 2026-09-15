from __future__ import annotations
from pathlib import Path
import re, sys

try:
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
except Exception:
    pass

DEV = Path(r"G:\Vertex_Project\Development")
PORTAL = DEV / "vertex_session_portal"
WS = DEV / "vertex_workstation"

def safe(v):
    return str(v).encode("ascii", "backslashreplace").decode("ascii")

def emit_window(path: Path, pattern: str, before=18, after=70, max_hits=3):
    print("=== TARGET ===")
    print("FILE=" + safe(path))
    print("PATTERN=" + safe(pattern))
    if not path.exists():
        print("EXISTS=NO")
        return
    print("EXISTS=YES")
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    rx = re.compile(pattern, re.I)
    hits = 0
    for i, line in enumerate(lines):
        if not rx.search(line):
            continue
        print(f"HIT_LINE={i+1}")
        for j in range(max(0, i-before), min(len(lines), i+after+1)):
            print(f"{j+1:05d}|{safe(lines[j])}")
        print("--")
        hits += 1
        if hits >= max_hits:
            break
    print(f"HITS={hits}")

def scan_workstation_routes():
    print("=== WORKSTATION_ROUTE_FILES ===")
    roots = [WS / "headless" / "src", WS / "src-tauri" / "src"]
    pats = [re.compile(r"/v1/jobs", re.I), re.compile(r"register_job", re.I),
            re.compile(r"POST", re.I), re.compile(r"TcpListener|axum|tiny_http|hyper", re.I)]
    emitted = 0
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.rs"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if not any(rx.search(text) for rx in pats):
                continue
            print("ROUTE_FILE=" + safe(p.relative_to(WS)))
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if any(rx.search(line) for rx in pats):
                    for j in range(max(0, i-10), min(len(lines), i+36)):
                        print(f"{j+1:05d}|{safe(lines[j])}")
                    print("--")
                    emitted += 1
                    if emitted >= 12:
                        print("ROUTE_BLOCK_LIMIT=YES")
                        return

def scan_portal_workstation_dir():
    root = PORTAL / "src" / "main" / "workstation"
    print("=== PORTAL_WORKSTATION_FILES ===")
    if not root.exists():
        print("ROOT_EXISTS=NO")
        return
    for p in sorted(root.rglob("*.ts")):
        print("FILE_NAME=" + safe(p.relative_to(PORTAL)))

def main():
    print("VERTEX_REGISTRATION_HANDSHAKE_SOURCE_RAY_000115V5H1=BEGIN")
    print("MODE=READ_ONLY")

    service = PORTAL / "src/main/vra/vra-dispatch-service.ts"
    client = PORTAL / "src/main/workstation/workstation-client.ts"

    emit_window(service, r"publishApprovedCard", before=22, after=95, max_hits=4)
    emit_window(service, r"reconcileWorkstation", before=20, after=125, max_hits=5)
    emit_window(service, r"workstationRegistration\s*=\s*['\"]REGISTERING|workstationRegistration:\s*['\"]REGISTERING", before=25, after=85, max_hits=5)
    emit_window(service, r"registerJob", before=28, after=95, max_hits=5)

    scan_portal_workstation_dir()
    emit_window(client, r"class\s+WorkstationClient", before=8, after=220, max_hits=1)
    emit_window(client, r"registerJob", before=20, after=100, max_hits=4)
    emit_window(client, r"fetch\s*\(|AbortController|timeout", before=20, after=75, max_hits=8)

    scan_workstation_routes()

    print("VERTEX_REGISTRATION_HANDSHAKE_SOURCE_RAY_000115V5H1=PASS")

if __name__ == "__main__":
    main()
