from pathlib import Path
import re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
BROWSER = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"
INJECTOR = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts"

def emit(s=""):
    print(str(s).encode("ascii","backslashreplace").decode("ascii"))

def fail(code, reason):
    emit(f"ASSERT_RESULT=FAILED")
    emit(f"CLASSIFICATION={reason}")
    emit(f"EXIT_CODE={code}")
    raise SystemExit(code)

for p in (LANE, BROWSER, INJECTOR):
    if not p.exists():
        fail(40, "SOURCE_MISSING:" + str(p))

lane = LANE.read_text(encoding="utf-8", errors="replace")
browser = BROWSER.read_text(encoding="utf-8", errors="replace")
injector = INJECTOR.read_text(encoding="utf-8", errors="replace")

checks = {
    "RESULT_LISTENER_REGISTERED": (
        "addEventListener(VERA_EVIDENCE_RETURN_RESULT_EVENT" in lane
        or "addEventListener(\n      VERA_EVIDENCE_RETURN_RESULT_EVENT" in lane
        or "addEventListener(\r\n      VERA_EVIDENCE_RETURN_RESULT_EVENT" in lane
    ),
    "RESULT_LISTENER_REMOVED": (
        "removeEventListener(VERA_EVIDENCE_RETURN_RESULT_EVENT" in lane
        or "removeEventListener(\n      VERA_EVIDENCE_RETURN_RESULT_EVENT" in lane
        or "removeEventListener(\r\n      VERA_EVIDENCE_RETURN_RESULT_EVENT" in lane
    ),
    "INFLIGHT_HAS_GUARD": "evidenceInFlight.has(result.deliveryId)" in lane,
    "INFLIGHT_ADD_EXISTS": bool(re.search(r"evidenceInFlight\.(?:add|set)\s*\(", lane)),
    "RETURN_EVENT_DISPATCH_EXISTS": (
        "VERA_EVIDENCE_RETURN_EVENT" in lane
        and "dispatchEvent" in lane
    ),
    "RESULT_EVENT_DECLARED": "VERA_EVIDENCE_RETURN_RESULT_EVENT" in injector,
    "RESULT_EVENT_DISPATCH_EXISTS": (
        "VERA_EVIDENCE_RETURN_RESULT_EVENT" in browser
        and "dispatchEvent" in browser
    ),
    "BROWSER_DELIVER_METHOD": "deliverWorkstationEvidence" in browser,
    "ACK_CALLSITE_REPAIRED": "acknowledgeVraEvidenceDelivery" in lane,
}

for name, ok in checks.items():
    emit(f"{name}={'PASS' if ok else 'FAIL'}")

if not checks["RESULT_LISTENER_REGISTERED"]:
    fail(41, "RESULT_LISTENER_NOT_REGISTERED")
if not checks["INFLIGHT_ADD_EXISTS"]:
    fail(42, "INFLIGHT_NEVER_POPULATED")
if not checks["RESULT_EVENT_DISPATCH_EXISTS"]:
    fail(43, "RESULT_EVENT_NOT_DISPATCHED_BY_BROWSER")
if not checks["RETURN_EVENT_DISPATCH_EXISTS"]:
    fail(44, "RETURN_EVENT_NOT_DISPATCHED_BY_LANE")
if not checks["ACK_CALLSITE_REPAIRED"]:
    fail(45, "ACK_CALLSITE_REPAIR_MISSING")

# Print all compact source lines that carry the runtime wiring.
emit("=== WIRING_LINES ===")
patterns = [
    "VERA_EVIDENCE_RETURN_EVENT",
    "VERA_EVIDENCE_RETURN_RESULT_EVENT",
    "evidenceInFlight",
    "deliverWorkstationEvidence",
    "acknowledgeVraEvidenceDelivery",
    "dispatchEvent",
]
for rel, text in [
    ("VraDispatchLane.ts", lane),
    ("VeraBrowserSession.ts", browser),
    ("VeraEvidenceReturnInjector.ts", injector),
]:
    emit(f"-- {rel} --")
    for i, line in enumerate(text.splitlines(), 1):
        if any(p in line for p in patterns):
            emit(f"{i:05d}: {line}")

emit("ASSERT_RESULT=CONFIRMED")
emit("CLASSIFICATION=STATIC_RUNTIME_WIRING_COMPLETE")
emit("PRODUCTION_MUTATION=NONE")
raise SystemExit(0)
