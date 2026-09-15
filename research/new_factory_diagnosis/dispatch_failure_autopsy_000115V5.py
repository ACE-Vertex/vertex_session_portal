from __future__ import annotations

from pathlib import Path
import os
import re
import sys
import json

try:
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
except Exception:
    pass

DEV = Path(r"G:\Vertex_Project\Development")
PORTAL = DEV / "vertex_session_portal"

FAILED = [
    "vertex-session-portal-auto-dispatch-controller-unification-h5-000001V5H1",
    "job-vera05-auto-dispatch-controller-unification-h5h1-a8c6ceb2-0c5d-4a6d-8e71-b4e2bebef6a4",
    "vertex-session-portal-auto-dispatch-runtime-trigger-h6-reset-000001V5",
    "job-vera05-auto-dispatch-runtime-trigger-h6-reset-7cd6b70e-01b6-440d-a951-4a84eeaba457",
]

SOURCE_FILES = [
    PORTAL / "src/main/vra/vra-dispatch-service.ts",
    PORTAL / "src/main/workstation/workstation-client.ts",
    PORTAL / "src/main/ipc/register-vra-dispatch-ipc.ts",
]

TERMS = [
    "publishApprovedCard",
    "reconcileWorkstation",
    "registerJob",
    "WorkstationHttpError",
    "/v1/jobs",
    "workstationLastError",
    "workstation_last_error",
    "dispatchPhase",
    "humanApproval",
    "renameSync",
    "copyFileSync",
    "sha256",
]

def safe(v: object) -> str:
    return str(v).encode("ascii", "backslashreplace").decode("ascii")

def print_context(path: Path, term: str, before=12, after=28, max_hits=4):
    print(f"=== SOURCE_TERM {safe(term)} ===")
    print("FILE=" + safe(path))
    if not path.exists():
        print("EXISTS=NO")
        return
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    hits = 0
    for i, line in enumerate(lines):
        if term.lower() not in line.lower():
            continue
        start = max(0, i-before)
        end = min(len(lines), i+after+1)
        print(f"HIT_LINE={i+1}")
        for j in range(start, end):
            print(f"{j+1:05d}|{safe(lines[j])}")
        print("--")
        hits += 1
        if hits >= max_hits:
            break
    print(f"HITS={hits}")

def source_autopsy():
    print("=== PRODUCTION_SOURCE_AUTOPSY ===")
    for p in SOURCE_FILES:
        if not p.exists():
            print("MISSING=" + safe(p))
            continue
        for term in TERMS:
            print_context(p, term)

def candidate_roots():
    roots = [PORTAL]
    for env in ("LOCALAPPDATA", "APPDATA"):
        value = os.environ.get(env)
        if value:
            base = Path(value)
            roots.extend([
                base / "VertexSessionPortal",
                base / "vertex_session_portal",
                base / "Vertex Session Portal",
                base / "VertexPortal",
            ])
            # Shallow discover Vertex/Portal named children only.
            try:
                for child in base.iterdir():
                    n = child.name.lower()
                    if child.is_dir() and ("vertex" in n or "portal" in n):
                        roots.append(child)
            except OSError:
                pass
    unique = []
    seen = set()
    for r in roots:
        key = str(r).lower()
        if key not in seen and r.exists():
            seen.add(key)
            unique.append(r)
    return unique

def scan_durable_failure_state():
    print("=== FAILED_CARD_DURABLE_STATE ===")
    exts = {".json", ".jsonl", ".txt", ".log", ".meta", ".metadata"}
    roots = candidate_roots()
    for root in roots:
        print("SCAN_ROOT=" + safe(root))
    hits = 0
    for root in roots:
        for p in root.rglob("*"):
            try:
                if not p.is_file():
                    continue
                if p.stat().st_size > 4_000_000:
                    continue
                if p.suffix.lower() not in exts and "ledger" not in p.name.lower() and "staging" not in p.name.lower():
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            matched = [x for x in FAILED if x in text]
            if not matched:
                continue
            print("STATE_FILE=" + safe(p))
            print("MATCHED=" + safe(",".join(matched)))
            lines = text.splitlines()
            interesting = []
            keys = (
                "artifact", "job_id", "correlation", "human_approval", "dispatch_phase",
                "status", "workstation_registration", "workstation_job_state",
                "workstation_last_error", "error", "published", "dispatched",
                "registered", "allocated_lane", "sha256"
            )
            for idx, line in enumerate(lines):
                low = line.lower()
                if any(x.lower() in line for x in matched) or any(k in low for k in keys):
                    interesting.append(idx)
            emitted = set()
            for idx in interesting[:80]:
                for j in range(max(0, idx-2), min(len(lines), idx+3)):
                    if j not in emitted:
                        print(f"{j+1:05d}|{safe(lines[j])}")
                        emitted.add(j)
            print("--")
            hits += 1
            if hits >= 20:
                print("STATE_FILE_LIMIT_REACHED=YES")
                print(f"STATE_FILES={hits}")
                return
    print(f"STATE_FILES={hits}")

def main():
    print("VERTEX_SESSION_PORTAL_DISPATCH_FAILURE_AUTOPSY_000115V5=BEGIN")
    print("MODE=READ_ONLY")
    scan_durable_failure_state()
    source_autopsy()
    print("VERTEX_SESSION_PORTAL_DISPATCH_FAILURE_AUTOPSY_000115V5=PASS")

if __name__ == "__main__":
    main()
