
from pathlib import Path
import os
import re
import sys
import time

ROOT = Path.cwd().resolve()

ARTIFACT = b"vertex-os-production-launcher-resolution-ray-000049V1"
JOB = b"job-vera01-vertex-os-production-launcher-bcb5f361-24db-449f-8cb2-5ac15725b918"
CORR = b"7ae5dcbd-d52e-463f-940f-927956337f7e"
TOKENS = [ARTIFACT, JOB, CORR]

DB_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
SIDE_SUFFIXES = ("-wal", "-journal", "-shm")
MAX_FILE_BYTES = 1024 * 1024 * 1024
RECENT_CUTOFF = time.time() - 14 * 24 * 60 * 60

candidate_roots = [ROOT]
for env_name in ("LOCALAPPDATA", "APPDATA"):
    value = os.environ.get(env_name)
    if not value:
        continue
    base = Path(value)
    if not base.exists():
        continue
    try:
        for child in base.iterdir():
            if child.is_dir() and re.search(r"vertex|session|portal", child.name, re.I):
                candidate_roots.append(child)
    except Exception:
        pass

# De-duplicate roots.
roots = []
seen_roots = set()
for p in candidate_roots:
    try:
        key = str(p.resolve()).lower()
    except Exception:
        key = str(p).lower()
    if key not in seen_roots:
        seen_roots.add(key)
        roots.append(p)

db_files = []
for base in roots:
    try:
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            low_parts = {x.lower() for x in p.parts}
            if low_parts & {"node_modules", ".git", "dist", "build", "target"}:
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            if st.st_mtime < RECENT_CUTOFF or st.st_size > MAX_FILE_BYTES:
                continue
            suffix = p.suffix.lower()
            name_low = p.name.lower()
            if suffix in DB_SUFFIXES or any(name_low.endswith(sfx) for sfx in SIDE_SUFFIXES):
                db_files.append(p)
    except Exception:
        pass

# De-duplicate paths.
uniq = []
seen = set()
for p in db_files:
    try:
        key = str(p.resolve()).lower()
    except Exception:
        key = str(p).lower()
    if key not in seen:
        seen.add(key)
        uniq.append(p)
db_files = uniq

print(f"LOCK_INDEPENDENT_DB_FILES={len(db_files)}")
for i,p in enumerate(db_files[:40],1):
    print(f"LOCK_INDEPENDENT_DB_{i}={p}")

def scan_file(path: Path):
    # Lock-independent raw byte scan. No SQLite connection is opened.
    found = [False, False, False]
    nearby = {
        "approval": False,
        "registry": False,
        "dispatch": False,
        "queue": False,
        "workstation": False,
    }
    keywords = {
        "approval": (b"approved", b"approval", b"human_apply", b"human gate"),
        "registry": (b"registry", b"registered"),
        "dispatch": (b"dispatch", b"handoff", b"publish", b"forward"),
        "queue": (b"queue", b"queued", b"inbox", b"outbox"),
        "workstation": (b"workstation",),
    }

    chunk_size = 1024 * 1024
    overlap = 16384
    prev = b""

    try:
        with path.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                data = prev + chunk
                low = data.lower()

                for idx, tok in enumerate(TOKENS):
                    start = 0
                    while True:
                        pos = data.find(tok, start)
                        if pos < 0:
                            break
                        found[idx] = True
                        lo = max(0, pos - 8192)
                        hi = min(len(data), pos + len(tok) + 8192)
                        ctx = low[lo:hi]
                        for name, pats in keywords.items():
                            if any(pat in ctx for pat in pats):
                                nearby[name] = True
                        start = pos + 1

                prev = data[-overlap:]
    except Exception as exc:
        print(f"LOCK_INDEPENDENT_READ_ERROR={path}|{type(exc).__name__}:{exc}")
        return found, nearby

    return found, nearby

aggregate_found = [False, False, False]
aggregate_nearby = {
    "approval": False,
    "registry": False,
    "dispatch": False,
    "queue": False,
    "workstation": False,
}

hit_files = []
for p in db_files:
    found, nearby = scan_file(p)
    if any(found):
        hit_files.append((p, found, nearby))
        print(
            "LOCK_INDEPENDENT_TARGET_HIT="
            f"path:{p}|artifact:{found[0]}|job:{found[1]}|corr:{found[2]}|"
            f"approval:{nearby['approval']}|registry:{nearby['registry']}|"
            f"dispatch:{nearby['dispatch']}|queue:{nearby['queue']}|"
            f"workstation:{nearby['workstation']}"
        )
    for i,v in enumerate(found):
        aggregate_found[i] = aggregate_found[i] or v
    for k,v in nearby.items():
        aggregate_nearby[k] = aggregate_nearby[k] or v

all_three = all(aggregate_found)
some = any(aggregate_found)

print(f"LOCK_INDEPENDENT_ARTIFACT_FOUND={aggregate_found[0]}")
print(f"LOCK_INDEPENDENT_JOB_FOUND={aggregate_found[1]}")
print(f"LOCK_INDEPENDENT_CORR_FOUND={aggregate_found[2]}")
print(f"LOCK_INDEPENDENT_ALL_THREE={all_three}")
print(f"LOCK_INDEPENDENT_NEAR_APPROVAL={aggregate_nearby['approval']}")
print(f"LOCK_INDEPENDENT_NEAR_REGISTRY={aggregate_nearby['registry']}")
print(f"LOCK_INDEPENDENT_NEAR_DISPATCH={aggregate_nearby['dispatch']}")
print(f"LOCK_INDEPENDENT_NEAR_QUEUE={aggregate_nearby['queue']}")
print(f"LOCK_INDEPENDENT_NEAR_WORKSTATION={aggregate_nearby['workstation']}")

if all_three:
    if aggregate_nearby["dispatch"] or aggregate_nearby["queue"] or aggregate_nearby["workstation"]:
        print("LOCK_INDEPENDENT_STORE_RESULT=FULL_MATCH_WITH_LIFECYCLE_CONTEXT")
        sys.exit(0)
    print("LOCK_INDEPENDENT_STORE_RESULT=FULL_MATCH_NO_LIFECYCLE_CONTEXT")
    sys.exit(241)

if some:
    print("LOCK_INDEPENDENT_STORE_RESULT=PARTIAL_TARGET_MATCH")
    sys.exit(242)

print("LOCK_INDEPENDENT_STORE_RESULT=NO_TARGET_BYTES_FOUND")
sys.exit(243)
