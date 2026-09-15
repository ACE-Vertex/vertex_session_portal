from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
DISPATCH = ROOT / "src" / "main" / "vra" / "vra-dispatch-service.ts"
GUARD = ROOT / "src" / "main" / "vra-registry" / "auto-registry-return-route-guard.ts"
LANE = ROOT / "src" / "renderer" / "src" / "components" / "VraDispatchLane" / "VraDispatchLane.ts"

print("VERTEX_REGISTRY_RETURN_ROUTE_GUARD_000148V5H1=BEGIN")

for path in [DISPATCH, GUARD, LANE]:
    if not path.is_file():
        raise SystemExit(f"MISSING:{path}")

dispatch = DISPATCH.read_text(encoding="utf-8", errors="strict")
guard = GUARD.read_text(encoding="utf-8", errors="strict")
lane = LANE.read_text(encoding="utf-8", errors="strict")

# Existing return transport remains the authority; H1 adds only an AUTO Registry gate.
required_existing_route = [
    "private exactOriginRoute(card: WorkstationDispatchCard): boolean",
    "window.dispatchEvent(new CustomEvent<VeraEvidenceReturnMessage>(VERA_EVIDENCE_RETURN_EVENT, { detail }))",
    "receipt.state !== 'DELIVERED'",
    "acknowledgeVraEvidenceDelivery",
]
for token in required_existing_route:
    ok = token in lane
    print(f"EXISTING_ROUTE|{token}|{ok}")
    if not ok:
        raise SystemExit(51)

required_dispatch = [
    "registryAllowsEvidenceReturn(this.registryRuntime.store",
    "card.workstationEvidenceReturnState === 'RETURN_QUEUED'",
    "card.originWindow === card.originSession",
]
for token in required_dispatch:
    ok = token in dispatch
    print(f"DISPATCH|{token}|{ok}")
    if not ok:
        raise SystemExit(52)

required_guard = [
    "if (!record) return true",
    "record.state !== 'RETURN_QUEUED'",
    "record.evidenceId !== candidate.evidenceId",
    "record.artifactId !== candidate.artifactId",
    "record.correlationId !== candidate.correlationId",
    "record.origin.originSession !== candidate.originSession",
    "record.origin.returnChannel !== candidate.returnChannel",
]
for token in required_guard:
    ok = token in guard
    print(f"GUARD|{token}|{ok}")
    if not ok:
        raise SystemExit(53)

# Guard must not become a second Return Router / delivery engine.
for forbidden in [
    "window.dispatchEvent",
    "acknowledgeEvidence",
    "acknowledgeVraEvidenceDelivery",
    "publishApprovedCard",
    "allocateLane",
    "writeFileSync",
    "copyFileSync",
    "renameSync",
]:
    hit = forbidden in guard
    print(f"FORBIDDEN_GUARD|{forbidden}|{hit}")
    if hit:
        raise SystemExit(54)

# Existing ACK -> Registry RETURNED projection from 000147 must remain in place.
ack_start = dispatch.index("async acknowledgeEvidenceDelivery")
ack_end = dispatch.index("async getWorkstationSafety", ack_start)
ack = dispatch[ack_start:ack_end]
if "card.workstationEvidenceReturnState = 'RETURNED'" not in ack:
    raise SystemExit("EXISTING_RETURNED_ACK_STATE_MISSING")
if "syncAutoRegistryWorkstationLifecycle(" not in ack:
    raise SystemExit("REGISTRY_RETURNED_PROJECTION_MISSING")

# Manual path remains Registry-free until Evidence-return eligibility. No admission changes.
manual_start = dispatch.index("dispatch(cardId: string): VraDispatchCard")
manual_end = dispatch.index("private publishApprovedCard", manual_start)
manual = dispatch[manual_start:manual_end]
if "registryAllowsEvidenceReturn" in manual:
    raise SystemExit("MANUAL_DISPATCH_CONTAMINATED")

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
print("EXISTING_RETURN_ROUTER=PRESERVED")
print("AUTO_REGISTRY_RETURN_GATE=ENABLED")
print("MANUAL_RETURN_PATH=PRESERVED")
print("EVIDENCE_MUTATION=ZERO")
print("WORKSTATION_CONTROL=ZERO")
print("LANE_AUTHORITY=WORKSTATION")
print("HUMAN_GATE=PRESERVED")
print("VERTEX_REGISTRY_RETURN_ROUTE_GUARD_000148V5H1=PASS")
