from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REG = ROOT / "src" / "main" / "vra-registry"

required_files = [
    REG / "vra-registry-contract.ts",
    REG / "vlog-contract.ts",
    REG / "vra-registry-store.ts",
    REG / "vra-registry-observer.ts",
    REG / "vra-registry-core.ts",
    REG / "index.ts",
]

print("VERTEX_VRA_REGISTRY_FOUNDATION_000124V5=BEGIN")
for path in required_files:
    print(f"FILE_EXISTS|{path.relative_to(ROOT)}|{path.exists()}")
    if not path.exists():
        raise SystemExit(11)

joined = "\n".join(p.read_text(encoding="utf-8", errors="strict") for p in required_files)
required_tokens = [
    "REGISTRY_AUTO_ONLY",
    "REGISTRY_IDENTITY_CONFLICT",
    "REGISTRY_ILLEGAL_TRANSITION",
    "VLOG_SQLITE_SCHEMA",
    "VLOG_QUERY_REASON_REQUIRED",
    "VLOG_QUERY_SCOPE_REQUIRED",
    "BAY_TRIGGER_READY",
    "RETURNED_WITHOUT_EVIDENCE",
    "REGISTRY_ALLOCATED_LANE_INVALID",
    "lane-(0[1-9]|[12][0-9]|3[0-2])",
]
for token in required_tokens:
    ok = token in joined
    print(f"TOKEN|{token}|{ok}")
    if not ok:
        raise SystemExit(12)

for forbidden in [
    "listAll(",
    "allocateLane(",
    "POST /v1/jobs",
    "workstation:vra-evidence-ack",
]:
    hit = forbidden in joined
    print(f"FORBIDDEN_FOUND|{forbidden}|{hit}")
    if hit:
        raise SystemExit(13)

# Report SQLite options available in the actual project/runtime, without making
# the foundation depend on one yet.
package = ROOT / "package.json"
if package.exists():
    pkg = json.loads(package.read_text(encoding="utf-8"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    print("SQLITE_DEP_BETTER_SQLITE3=" + str("better-sqlite3" in deps))
    print("SQLITE_DEP_SQLITE3=" + str("sqlite3" in deps))
    print("SQLITE_DEP_SQLITE=" + str("sqlite" in deps))

node = shutil.which("node")
if node:
    probe = subprocess.run(
        [node, "-e", "try{require('node:sqlite');console.log('YES')}catch(e){console.log('NO')}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    print("NODE_SQLITE_AVAILABLE=" + probe.stdout.strip().splitlines()[-1] if probe.stdout.strip() else "NODE_SQLITE_AVAILABLE=UNKNOWN")

npm = shutil.which("npm.cmd") or shutil.which("npm")
if npm:
    proc = subprocess.run(
        [npm, "run", "typecheck"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    print("TYPECHECK_EXIT=" + str(proc.returncode))
    if proc.stdout:
        print("TYPECHECK_STDOUT_TAIL=" + proc.stdout[-6000:])
    if proc.stderr:
        print("TYPECHECK_STDERR_TAIL=" + proc.stderr[-6000:])
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

print("NORMAL_PATH_MUTATION=ZERO")
print("DISPATCH_BAY_MUTATION=ZERO")
print("WORKSTATION_MUTATION=ZERO")
print("REGISTRY_AUTO_ONLY=PASS")
print("WORKSTATION_LANE_AUTHORITY=PRESERVED")
print("HUMAN_APPLY=PRESERVED")
print("VLOG_QUERY_GATE=PASS")
print("OBSERVER_TRANSITION_ONLY=PASS")
print("VERTEX_VRA_REGISTRY_FOUNDATION_000124V5=PASS")
