from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
DISPATCH = ROOT / "src" / "main" / "vra" / "vra-dispatch-service.ts"
ADAPTER = ROOT / "src" / "main" / "vra-registry" / "auto-registry-intake-adapter.ts"
RUNTIME = ROOT / "src" / "main" / "vra-registry" / "vra-registry-runtime.ts"

print("VERTEX_VRA_REGISTRY_AUTO_INTAKE_GATE_000146V5=BEGIN")

for path in [DISPATCH, ADAPTER, RUNTIME]:
    if not path.is_file():
        raise SystemExit(f"MISSING:{path}")

dispatch = DISPATCH.read_text(encoding="utf-8", errors="strict")
adapter = ADAPTER.read_text(encoding="utf-8", errors="strict")

required_dispatch = [
    "createVraRegistryRuntime(userDataRoot)",
    "admitAutoRegistryCandidate(this.registryRuntime.core",
    "registryId: `auto:${card.id}`",
    "await this.registryRuntime.core.markDispatched(registryId)",
    "await this.reconcileAutoAuthorizedStagedCards()",
    "AUTO_VRA_REGISTRY_QUEUED",
]
for token in required_dispatch:
    ok = token in dispatch
    print(f"DISPATCH|{token}|{ok}")
    if not ok:
        raise SystemExit(31)

required_adapter = [
    "dispatchMode: 'AUTO'",
    "await core.registerAuto(intake)",
    "await core.markBayReady(candidate.registryId)",
    "REGISTRY_AUTO_ARTIFACT_ID_REQUIRED",
    "REGISTRY_AUTO_ORIGIN_VERA_MISMATCH",
]
for token in required_adapter:
    ok = token in adapter
    print(f"ADAPTER|{token}|{ok}")
    if not ok:
        raise SystemExit(32)

# The legacy synchronous renderer AUTO command must no longer publish directly.
auto_start = dispatch.index("private handleAutoDispatchCommand")
auto_end = dispatch.index("private requireActiveAutoAuthority", auto_start)
auto_block = dispatch[auto_start:auto_end]
if "publishApprovedCard(" in auto_block:
    raise SystemExit("AUTO_DIRECT_PUBLISH_BYPASS_REMAINS")
if "scheduleAutoAuthorizedDispatchScan(0)" not in auto_block:
    raise SystemExit("AUTO_QUEUE_SIGNAL_MISSING")

# Main-process AUTO reconciliation must enter Registry before publish.
reconcile_start = dispatch.index("private async reconcileAutoAuthorizedStagedCards")
reconcile_end = dispatch.index("private scheduleAutoAuthorizedDispatchScan", reconcile_start)
reconcile_block = dispatch[reconcile_start:reconcile_end]
registry_pos = reconcile_block.find("admitAutoRegistryCandidate(")
publish_pos = reconcile_block.find("publishApprovedCard(")
if registry_pos < 0 or publish_pos < 0 or registry_pos >= publish_pos:
    raise SystemExit("AUTO_REGISTRY_ORDER_INVALID")

# Manual Human dispatch remains direct and unchanged in responsibility.
manual_start = dispatch.index("dispatch(cardId: string): VraDispatchCard")
manual_end = dispatch.index("private publishApprovedCard", manual_start)
manual_block = dispatch[manual_start:manual_end]
if "publishApprovedCard(card)" not in manual_block:
    raise SystemExit("MANUAL_DISPATCH_PATH_CHANGED")
if "registryRuntime" in manual_block or "admitAutoRegistryCandidate" in manual_block:
    raise SystemExit("MANUAL_DISPATCH_ENTERED_REGISTRY")

# Registry adapter may not acquire Workstation/Bay/approval authority.
for forbidden in [
    "publishApprovedCard",
    "WorkstationClient",
    "worksIncomingRoot",
    "humanApproval",
    "allocateLane",
]:
    hit = forbidden in adapter
    print(f"FORBIDDEN_ADAPTER|{forbidden}|{hit}")
    if hit:
        raise SystemExit(33)

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
    print(proc.stdout[-8000:])
if proc.stderr:
    print(proc.stderr[-8000:])
if proc.returncode != 0:
    raise SystemExit(proc.returncode)

print("VRA_FORMAT=UNCHANGED")
print("AUTO_REGISTRY_GATE=MANDATORY")
print("MANUAL_REGISTRY_GATE=ZERO")
print("HUMAN_GATE=PRESERVED")
print("LANE_AUTHORITY=WORKSTATION")
print("AUTO_DIRECT_PUBLISH_BYPASS=CLOSED")
print("VERTEX_VRA_REGISTRY_AUTO_INTAKE_GATE_000146V5=PASS")
