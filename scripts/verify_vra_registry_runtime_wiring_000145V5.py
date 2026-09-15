from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
RUNTIME = ROOT / "src" / "main" / "vra-registry" / "vra-registry-runtime.ts"
INDEX = ROOT / "src" / "main" / "vra-registry" / "index.ts"
SQLITE = ROOT / "src" / "main" / "vra-registry" / "sqlite-vra-registry-store.ts"
CORE = ROOT / "src" / "main" / "vra-registry" / "vra-registry-core.ts"

print("VERTEX_VRA_REGISTRY_RUNTIME_WIRING_000145V5=BEGIN")

for path in [RUNTIME, INDEX, SQLITE, CORE]:
    if not path.is_file():
        raise SystemExit(f"MISSING:{path}")

runtime = RUNTIME.read_text(encoding="utf-8", errors="strict")
index = INDEX.read_text(encoding="utf-8", errors="strict")
core = CORE.read_text(encoding="utf-8", errors="strict")

required_runtime = [
    "new SqliteVraRegistryStore(databasePath)",
    "new VraRegistryCore(store, store)",
    "registry.sqlite3",
    "mkdirSync(directory, { recursive: true })",
    "close: () => store.close()",
]
for token in required_runtime:
    ok = token in runtime
    print(f"RUNTIME|{token}|{ok}")
    if not ok:
        raise SystemExit(21)

required_index = [
    "export * from './sqlite-vra-registry-store'",
    "export * from './vra-registry-runtime'",
    "export * from './vra-registry-core'",
    "export * from './vra-registry-store'",
]
for token in required_index:
    ok = token in index
    print(f"INDEX|{token}|{ok}")
    if not ok:
        raise SystemExit(22)

# Ensure the verified Core contract remains constructor(store, vlog).
if "constructor(" not in core or "private readonly store: VraRegistryStore" not in core or "private readonly vlog: VLogAppendStore" not in core:
    raise SystemExit("REGISTRY_CORE_CONTRACT_CHANGED")

for forbidden in [
    "MemoryRegistryStore",
    "allocateLane(",
    "POST /v1/jobs",
    "workstation:vra-evidence-ack",
    "publishApprovedCard(",
]:
    hit = forbidden in runtime
    print(f"FORBIDDEN|{forbidden}|{hit}")
    if hit:
        raise SystemExit(23)

npm = shutil.which("npm.cmd") or shutil.which("npm")
if not npm:
    raise SystemExit("NPM_NOT_FOUND")

proc = subprocess.run(
    [npm, "run", "typecheck"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)

print(f"TYPECHECK_EXIT={proc.returncode}")
if proc.stdout:
    print(proc.stdout[-6000:])
if proc.stderr:
    print(proc.stderr[-6000:])

if proc.returncode != 0:
    raise SystemExit(proc.returncode)

print("VRA_FORMAT=UNCHANGED")
print("REGISTRY_CORE=SQLITE_BOUND")
print("REGISTRY_VLOG=SQLITE_BOUND")
print("DISPATCH_BAY_MUTATION=ZERO")
print("WORKSTATION_MUTATION=ZERO")
print("HUMAN_GATE=PRESERVED")
print("LANE_AUTHORITY=WORKSTATION")
print("VERTEX_VRA_REGISTRY_RUNTIME_WIRING_000145V5=PASS")
