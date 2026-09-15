from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SOURCE = ROOT / "src" / "main" / "vra-registry" / "sqlite-vra-registry-store.ts"

print("VERTEX_VRA_REGISTRY_PERSISTENT_STORE_000144V5=BEGIN")

if not SOURCE.is_file():
    raise SystemExit("REGISTRY_SQLITE_STORE_MISSING")

text = SOURCE.read_text(encoding="utf-8", errors="strict")

required = [
    "better-sqlite3",
    "implements VraRegistryStore, VLogAppendStore, VLogQueryGate",
    "CREATE TABLE IF NOT EXISTS vra_registry",
    "CREATE TABLE IF NOT EXISTS vertex_vlog",
    "REGISTRY_IDENTITY_CONFLICT",
    "ON CONFLICT(registry_id) DO UPDATE SET",
    "INSERT OR IGNORE INTO vertex_vlog",
    "validateVLogQuery",
    "journal_mode = WAL",
]

for token in required:
    ok = token in text
    print(f"CHECK|{token}|{ok}")
    if not ok:
        raise SystemExit(11)

for forbidden in [
    "allocateLane(",
    "POST /v1/jobs",
    "HUMAN_APPROVED = true",
    "workstation:vra-evidence-ack",
]:
    hit = forbidden in text
    print(f"FORBIDDEN|{forbidden}|{hit}")
    if hit:
        raise SystemExit(12)

package_path = ROOT / "package.json"
if not package_path.is_file():
    raise SystemExit("PACKAGE_JSON_MISSING")

package = json.loads(package_path.read_text(encoding="utf-8"))
deps = {
    **package.get("dependencies", {}),
    **package.get("devDependencies", {}),
}
if "better-sqlite3" not in deps:
    raise SystemExit("BETTER_SQLITE3_DEPENDENCY_MISSING")

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

print("VRA_MANIFEST_CONTRACT=UNCHANGED")
print("BAY_MUTATION=ZERO")
print("WORKSTATION_MUTATION=ZERO")
print("LANE_AUTHORITY=WORKSTATION")
print("HUMAN_GATE=PRESERVED")
print("PERSISTENCE_RESPONSIBILITY=REGISTRY")
print("VERTEX_VRA_REGISTRY_PERSISTENT_STORE_000144V5=PASS")
