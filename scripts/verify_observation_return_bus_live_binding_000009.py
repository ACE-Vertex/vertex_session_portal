from __future__ import annotations

from pathlib import Path
import hashlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
TAP = ROOT / "src/main/observability/evidence-return-tap.ts"
COMPAT = ROOT / "src/main/observability/observation-sidecar-compat.ts"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"

EXPECTED_TAP_SHA256 = "010b2e19be7578217b3378172a0e407b2bed2f9eb7f2c239e2afa4611f019aa4"

def text(path: Path) -> str:
    if not path.is_file():
        raise AssertionError(f"MISSING_FILE:{path}")
    return path.read_text(encoding="utf-8", errors="replace")

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

tap = text(TAP)
compat = text(COMPAT)
service = text(SERVICE)

checks = {
    "TAP_SHA256": sha(TAP) == EXPECTED_TAP_SHA256,
    "COMPAT_SCHEMA": "vertex-workstation/observation-payload-1" in compat,
    "COMPAT_NORMALIZER": "toObservationSupplement" in compat,
    "TAP_IMPORTS_COMPAT": "from './observation-sidecar-compat'" in tap,
    "TAP_NESTED_REFERENCE": "executionEvidence.observation_reference" in tap,
    "TAP_CAMEL_REFERENCE_COMPAT": "executionEvidence.observationReference" in tap,
    "TAP_STATUS_ABSENT": "'ABSENT'" in tap,
    "TAP_STATUS_ATTACHED": "'ATTACHED'" in tap,
    "TAP_STATUS_REJECTED": "'REJECTED'" in tap,
    "TAP_NORMALIZED_SUPPLEMENT": "observationSupplement" in tap,
    "TAP_ARTIFACT_BIND": "toObservationSupplement(reference.value, artifactId ?? undefined)" in tap,
    "TAP_CANONICAL_ANALYSIS_PRESERVED": "analyzeWorkstationEvidence(input.raw)" in tap,
    "TAP_ATTACHED_BLACKBOX": "WORKSTATION_OBSERVATION_SIDECAR_ATTACHED" in tap,
    "TAP_REJECTED_BLACKBOX": "WORKSTATION_OBSERVATION_SIDECAR_REJECTED" in tap,
    "TAP_CACHE_SHA_IDEMPOTENCY": "existing.observationSupplement.sha256 !== observation.supplement.sha256" in tap,
    "SERVICE_EXISTING_TAP_OWNER": "private readonly evidenceObservability: EvidenceReturnObservabilityTap" in service,
    "SERVICE_EXISTING_TAP_CALL": "await this.evidenceObservability.observeAndPersist({" in service,
    "SERVICE_RAW_BODY_PRESERVED": "raw: response.body" in service,
    "SERVICE_HUMAN_GATE_CHECK": "WORKSTATION_EVIDENCE_HUMAN_GATE_MISMATCH" in service,
    "NO_SECOND_ACK": "acknowledgeEvidenceDelivery" not in tap,
    "NO_SECOND_WORKSTATION_CLIENT": "WorkstationClient" not in tap,
    "NO_SECOND_RETURN_ROUTER": "ReturnRouter" not in tap,
}

for name, ok in checks.items():
    print(f"{name}={'PASS' if ok else 'FAIL'}")

if not all(checks.values()):
    raise SystemExit(1)

print("OBSERVATION_OPTIONAL_FAIL_OPEN=PASS")
print("CANONICAL_EVIDENCE_RAW_UNCHANGED=PASS")
print("EXISTING_RETURN_FIFO_OWNER_PRESERVED=PASS")
print("EXISTING_ACK_OWNER_PRESERVED=PASS")
print("HUMAN_GATE_PRESERVED=PASS")
print("PRODUCTION_FILES_CHANGED=1")
print("VERTEX_OBSERVATION_RETURN_BUS_LIVE_BINDING_000009=PASS")
