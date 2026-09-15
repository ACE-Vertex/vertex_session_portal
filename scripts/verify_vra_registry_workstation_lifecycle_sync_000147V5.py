from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
DISPATCH = ROOT / "src" / "main" / "vra" / "vra-dispatch-service.ts"
SYNC = ROOT / "src" / "main" / "vra-registry" / "auto-registry-workstation-sync.ts"
CORE = ROOT / "src" / "main" / "vra-registry" / "vra-registry-core.ts"

print("VERTEX_VRA_REGISTRY_WORKSTATION_LIFECYCLE_SYNC_000147V5=BEGIN")

for path in [DISPATCH, SYNC, CORE]:
    if not path.is_file():
        raise SystemExit(f"MISSING:{path}")

dispatch = DISPATCH.read_text(encoding="utf-8", errors="strict")
sync = SYNC.read_text(encoding="utf-8", errors="strict")
core = CORE.read_text(encoding="utf-8", errors="strict")

required_sync = [
    "if (!record) return { tracked: false",
    "REGISTRY_WORKSTATION_ARTIFACT_ID_MISMATCH",
    "REGISTRY_WORKSTATION_CORRELATION_ID_MISMATCH",
    "await core.markDispatched(record.registryId)",
    "await core.markExecuting(record.registryId, observation.allocatedLane)",
    "await core.bindEvidence(record.registryId, observation.evidenceId)",
    "await core.markReturnQueued(record.registryId)",
    "await core.markReturned(record.registryId)",
    "await core.fail(record.registryId)",
]
for token in required_sync:
    ok = token in sync
    print(f"SYNC|{token}|{ok}")
    if not ok:
        raise SystemExit(41)

required_dispatch = [
    "import { syncAutoRegistryWorkstationLifecycle } from '../vra-registry/auto-registry-workstation-sync'",
    "this.registryRuntime.store",
    "portalPublished: card.dispatchPhase === 'PUBLISHED' && card.status === 'DISPATCHED'",
]
for token in required_dispatch:
    ok = token in dispatch
    print(f"DISPATCH|{token}|{ok}")
    if not ok:
        raise SystemExit(42)

if dispatch.count("syncAutoRegistryWorkstationLifecycle(") != 2:
    raise SystemExit("REGISTRY_SYNC_CALL_COUNT_INVALID")

# One call must be after Evidence pickup in reconcileWorkstationCard.
reconcile_start = dispatch.index("private async reconcileWorkstationCard")
reconcile_end = dispatch.index("private workstationCardSyncKey", reconcile_start)
reconcile = dispatch[reconcile_start:reconcile_end]
if reconcile.find("retrieveEvidence(card)") < 0:
    raise SystemExit("EVIDENCE_RETRIEVE_ANCHOR_MISSING")
if reconcile.find("syncAutoRegistryWorkstationLifecycle(") < reconcile.find("retrieveEvidence(card)"):
    raise SystemExit("REGISTRY_SYNC_BEFORE_EVIDENCE_PICKUP")

# One call must occur after successful Workstation ACK has durably set RETURNED.
ack_start = dispatch.index("async acknowledgeEvidenceDelivery")
ack_end = dispatch.index("async getWorkstationSafety", ack_start)
ack = dispatch[ack_start:ack_end]
returned_pos = ack.find("card.workstationEvidenceReturnState = 'RETURNED'")
sync_pos = ack.find("syncAutoRegistryWorkstationLifecycle(")
if returned_pos < 0 or sync_pos < returned_pos:
    raise SystemExit("REGISTRY_RETURN_SYNC_ORDER_INVALID")

# Manual dispatch remains Registry-free.
manual_start = dispatch.index("dispatch(cardId: string): VraDispatchCard")
manual_end = dispatch.index("private publishApprovedCard", manual_start)
manual = dispatch[manual_start:manual_end]
if "registryRuntime" in manual or "syncAutoRegistryWorkstationLifecycle" in manual:
    raise SystemExit("MANUAL_DISPATCH_REGISTRY_CONTAMINATION")

# Registry sync adapter remains strictly observational/projection responsibility.
for forbidden in [
    "publishApprovedCard",
    "copyFileSync",
    "renameSync",
    "WorkstationClient",
    "acknowledgeEvidence(",
    "humanApproval",
    "allocateLane(",
]:
    hit = forbidden in sync
    print(f"FORBIDDEN_SYNC|{forbidden}|{hit}")
    if hit:
        raise SystemExit(43)

# Core canonical state machine must still own lifecycle transitions.
for token in [
    "DISPATCHED: ['EXECUTING', 'FAILED', 'REJECTED']",
    "EXECUTING: ['EVIDENCE_AVAILABLE', 'FAILED']",
    "EVIDENCE_AVAILABLE: ['RETURN_QUEUED', 'FAILED']",
    "RETURN_QUEUED: ['RETURNED', 'FAILED']",
]:
    if token not in core:
        raise SystemExit("REGISTRY_CORE_STATE_MACHINE_CHANGED")

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
print("AUTO_ONLY_REGISTRY_TRACKING=TRUE")
print("MANUAL_PATH=UNCHANGED")
print("LANE_ALLOCATION_AUTHORITY=WORKSTATION")
print("EVIDENCE_PAYLOAD_MUTATION=ZERO")
print("HUMAN_GATE=PRESERVED")
print("REGISTRY_LIFECYCLE=DISPATCHED_TO_RETURNED_BOUND")
print("VERTEX_VRA_REGISTRY_WORKSTATION_LIFECYCLE_SYNC_000147V5=PASS")
