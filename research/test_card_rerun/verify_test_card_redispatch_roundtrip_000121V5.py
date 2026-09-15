\
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
RENDERER = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"

print("VERTEX_SESSION_PORTAL_TEST_CARD_REDISPATCH_ROUNDTRIP_000121V5=BEGIN")
print("VERIFY_MODE=READ_ONLY_SOURCE_CONTRACT_CHECK")
print(f"ROOT={ROOT}")

failures: list[str] = []

def check(label: str, condition: bool) -> None:
    state = "PASS" if condition else "FAIL"
    print(f"{label}={state}")
    if not condition:
        failures.append(label)

check("SERVICE_PRESENT", SERVICE.is_file())
check("RENDERER_PRESENT", RENDERER.is_file())

service = SERVICE.read_text(encoding="utf-8") if SERVICE.is_file() else ""
renderer = RENDERER.read_text(encoding="utf-8") if RENDERER.is_file() else ""

# Main-process authority: TEST is explicit and fail-closed; renderer-only hiding is insufficient.
check("MAIN_EXPLICIT_TEST_KIND", "VRA_TEST_CARD_KIND" in service)
check("MAIN_DURABLE_CARD_KIND", "card_kind" in service and "cardKind" in service)
check("MAIN_DURABLE_RERUN_PARENT", "rerun_of_job_id" in service and "rerunOfJobId" in service)
check("MAIN_DURABLE_TEST_RUN_ID", "test_run_id" in service and "testRunId" in service)
check("MAIN_TEST_RERUN_ENTRY", "stageTestCardRerun" in service)
check("MAIN_NON_TEST_FAIL_CLOSED", "VRA_TEST_RERUN_NON_TEST_DENIED" in service)
check("MAIN_TEST_RERUN_PREFIX", "TEST_RERUN_EXPORT_PREFIX" in service or "vertex-test-rerun:" in service)
check("MAIN_FRESH_HUMAN_GATE", "humanApproval: 'PENDING'" in service or "human_approval: 'PENDING'" in service)
check("MAIN_NEW_IDENTITY", "randomUUID" in service and "correlation" in service and "job" in service)
check("MAIN_ORIGIN_PRESERVATION", "originSession" in service and "originVera" in service and "originWindow" in service)

# Renderer contract: normal/production cards receive zero redispatch DOM.
check("RENDERER_EXPLICIT_TEST_KIND", "explicitTestCard" in renderer)
check("RENDERER_TEST_RERUN_ELIGIBLE", "testRerunEligible" in renderer)
check("RENDERER_TEST_RERUN_ACTION", 'data-action="rerun-test"' in renderer)
check("RENDERER_NON_TEST_ZERO_RERUN_DOM", "if (!this.explicitTestCard(card)) return ''" in renderer)
check("RENDERER_RERUN_TRANSPORT", "vertex-test-rerun:" in renderer)
check("RENDERER_HUMAN_APPROVAL_MESSAGE", "HUMAN APPROVAL REQUIRED" in renderer or "Human Approval" in renderer)

# Regression guard: do not infer TEST from artifact/title/filename substrings.
for forbidden in (
    "filename.includes('test')",
    'filename.includes("test")',
    "title.includes('test')",
    'title.includes("test")',
    "artifactId.includes('test')",
    'artifactId.includes("test")',
):
    check("NO_TEST_NAME_INFERENCE_" + str(abs(hash(forbidden))), forbidden not in service and forbidden not in renderer)

# Preserve Human Gate / lane authority language or fields used by current production path.
check("HUMAN_APPROVAL_STILL_PRESENT", "humanApproval" in service and "humanApproval" in renderer)
check("ALLOCATED_LANE_STILL_WORKSTATION_FACT", "allocatedLane" in service)
check("REQUESTED_LANE_STILL_PRESENT", "requestedLane" in service)

if failures:
    print("FAILED=" + ",".join(failures))
    print("VERTEX_SESSION_PORTAL_TEST_CARD_REDISPATCH_ROUNDTRIP_000121V5=FAIL")
    sys.exit(1)

print("CARD_KIND=TEST")
print("EXPECTED_AFTER_TERMINAL_RETURN=REDISPATCH_ACTION_VISIBLE_FOR_THIS_CARD_ONLY")
print("EXPECTED_NON_TEST=ZERO_REDISPATCH_DOM")
print("EXPECTED_RERUN=NEW_JOB_ID+NEW_CORRELATION_ID+HUMAN_APPROVAL_PENDING")
print("PRODUCTION_SOURCE_MUTATION_FROM_VERIFY=ZERO")
print("VERTEX_SESSION_PORTAL_TEST_CARD_REDISPATCH_ROUNDTRIP_000121V5=PASS")
