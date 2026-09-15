from __future__ import annotations

from pathlib import Path
import re
import socket
import sys

try:
    sys.stdout.reconfigure(errors="backslashreplace")
    sys.stderr.reconfigure(errors="backslashreplace")
except Exception:
    pass

DEV = Path(r"G:\Vertex_Project\Development")
PORTAL = DEV / "vertex_session_portal"
WS = DEV / "vertex_workstation"
INCOMING = DEV / "_incoming"

FAILED_IDENTITIES = [
    "vertex-session-portal-auto-dispatch-controller-unification-h5-000001V5H1",
    "job-vera05-auto-dispatch-controller-unification-h5h1-a8c6ceb2-0c5d-4a6d-8e71-b4e2bebef6a4",
    "vertex-session-portal-auto-dispatch-runtime-trigger-h6-reset-000001V5",
    "job-vera05-auto-dispatch-runtime-trigger-h6-reset-7cd6b70e-01b6-440d-a951-4a84eeaba457",
]

PORTAL_FILES = [
    PORTAL / "src/main/vra/vra-dispatch-service.ts",
    PORTAL / "src/main/ipc/register-vra-dispatch-ipc.ts",
]

WS_FILES = [
    WS / "headless/src/persistent_job_registry.rs",
    WS / "headless/src/main.rs",
    WS / "headless/src/lib.rs",
    WS / "src-tauri/src/work_dispatcher.rs",
    WS / "src-tauri/src/manifest_gate.rs",
    WS / "src-tauri/src/lane_manager.rs",
    WS / "src-tauri/src/lane_scheduler.rs",
]

TERMS = [
    "publishApprovedCard",
    "registerJob",
    "/v1/jobs",
    "127.0.0.1",
    "47832",
    "workstationLastError",
    "humanApproval",
    "dispatchPhase",
    "PUBLISHED",
    "DISPATCHED",
    "artifact_sha256",
    "human_approval",
    "allocated_lane",
    "requested_lane",
    "lane_policy",
    "ReceivingGateway",
    "JobRegistry",
    "persistent",
    "evidence",
]

def safe(x: object) -> str:
    return str(x).encode("ascii", "backslashreplace").decode("ascii")

def print_context(path: Path, terms: list[str], radius: int = 2, max_blocks: int = 35):
    print("FILE=" + safe(path))
    if not path.exists():
        print("EXISTS=NO")
        return
    print("EXISTS=YES")
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as exc:
        print("READ_ERROR=" + safe(repr(exc)))
        return

    seen = set()
    blocks = 0
    for idx, line in enumerate(lines):
        low = line.lower()
        matched = [t for t in terms if t.lower() in low]
        if not matched:
            continue
        start = max(0, idx - radius)
        end = min(len(lines), idx + radius + 1)
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        print("MATCH=" + ",".join(matched))
        for j in range(start, end):
            print(f"{j+1:05d}|{safe(lines[j].rstrip())}")
        print("--")
        blocks += 1
        if blocks >= max_blocks:
            print("BLOCK_LIMIT_REACHED=YES")
            break
    print(f"BLOCKS={blocks}")

def check_incoming():
    print("=== INCOMING_IDENTITY_CHECK ===")
    print("ROOT=" + safe(INCOMING))
    if not INCOMING.exists():
        print("INCOMING_EXISTS=NO")
        return
    print("INCOMING_EXISTS=YES")
    found = 0
    for p in INCOMING.iterdir():
        if not p.is_file():
            continue
        name = p.name
        if any(identity in name for identity in FAILED_IDENTITIES):
            print("FOUND|" + safe(name))
            found += 1
    print(f"FOUND_COUNT={found}")

def search_ws_state():
    print("=== WORKSTATION_DURABLE_IDENTITY_CHECK ===")
    roots = [
        WS / "runtime",
        WS / "state",
        WS / "data",
        WS / "headless",
        WS / "recovery",
    ]
    exts = {".json", ".jsonl", ".db", ".sqlite", ".log", ".txt", ".toml"}
    found = 0
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            try:
                if not p.is_file() or p.stat().st_size > 5_000_000:
                    continue
                if p.suffix.lower() not in exts:
                    continue
                if p.suffix.lower() in {".db", ".sqlite"}:
                    # Do not parse binary DBs; report their presence only.
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            matched = [i for i in FAILED_IDENTITIES if i in text]
            if matched:
                print("STATE_HIT|" + safe(p.relative_to(WS)) + "|" + safe(",".join(matched)))
                found += 1
                if found >= 30:
                    print("STATE_HIT_LIMIT_REACHED=YES")
                    print(f"STATE_HITS={found}")
                    return
    print(f"STATE_HITS={found}")

def probe_port():
    print("=== WORKSTATION_RUNTIME ===")
    try:
        with socket.create_connection(("127.0.0.1", 47832), timeout=0.35):
            print("PORT_47832=OPEN")
    except Exception as exc:
        print("PORT_47832=CLOSED_OR_SLEEPING")
        print("PORT_ERROR=" + safe(repr(exc)))

def main():
    print("VERTEX_NEW_FACTORY_PRODUCTION_NEURAL_PATH_PROBE_H2=BEGIN")
    print("MODE=READ_ONLY")
    probe_port()
    check_incoming()
    search_ws_state()

    print("=== PORTAL_PRODUCTION_SOURCE ===")
    for p in PORTAL_FILES:
        print_context(p, TERMS, radius=3, max_blocks=28)

    print("=== WORKSTATION_PRODUCTION_SOURCE ===")
    for p in WS_FILES:
        print_context(p, TERMS, radius=3, max_blocks=24)

    print("VERTEX_NEW_FACTORY_PRODUCTION_NEURAL_PATH_PROBE_H2=PASS")

if __name__ == "__main__":
    main()
