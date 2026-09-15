from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
PRELOAD = ROOT / "src/preload/index.ts"
IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def die(msg, code):
    emit("ASSERT_RESULT=FAILED")
    emit("DETAIL=" + msg)
    raise SystemExit(code)

for p in (LANE, PRELOAD, IPC, SERVICE):
    if not p.exists():
        die("SOURCE_MISSING:" + str(p), 10)

lane = LANE.read_text(encoding="utf-8", errors="replace")
preload = PRELOAD.read_text(encoding="utf-8", errors="replace")
ipc = IPC.read_text(encoding="utf-8", errors="replace")
service = SERVICE.read_text(encoding="utf-8", errors="replace")

start = lane.find("private readonly evidenceResultListener")
if start < 0:
    die("LISTENER_NOT_FOUND", 11)

# Bound to next private member or 8k chars.
cands = []
for token in ("\n  private readonly ", "\n  private async ", "\n  private "):
    idx = lane.find(token, start + 10)
    if idx >= 0:
        cands.append(idx)
end = min(cands) if cands else min(len(lane), start + 8000)
body = lane[start:end]

checks = {
    "LISTENER_HAS_INFLIGHT_GUARD": "evidenceInFlight.has(result.deliveryId)" in body,
    "LISTENER_DELETES_INFLIGHT": "evidenceInFlight.delete(result.deliveryId)" in body,
    "LISTENER_RESOLVES_CARD": "candidate.evidenceIdentity === result.deliveryId" in body and "candidate.jobId === result.jobId" in body,
    "LISTENER_HAS_CARD_MISS_RETURN": "if (!card) return" in body,
    "LISTENER_CALLS_ACK_API": "acknowledgeVraEvidenceDelivery" in body,
    "PRELOAD_EXPOSES_ACK_API": "acknowledgeVraEvidenceDelivery" in preload and "workstation:vra-evidence-ack" in preload,
    "MAIN_IPC_HANDLES_ACK": "workstation:vra-evidence-ack" in ipc and "acknowledgeEvidenceDelivery" in ipc,
    "SERVICE_HAS_ACK_METHOD": "acknowledgeEvidenceDelivery" in service,
}

for name, ok in checks.items():
    emit(f"{name}={'YES' if ok else 'NO'}")

emit("=== LISTENER_SOURCE ===")
for n, line in enumerate(body.splitlines(), 1):
    emit(f"{n:04d}: {line}")
emit("=== END_LISTENER_SOURCE ===")

# Assertion we are testing:
# delivery result listener has local receipt handling but does NOT invoke the durable ACK API,
# while the API exists from preload through Main/service.
expected = (
    checks["LISTENER_HAS_INFLIGHT_GUARD"]
    and checks["LISTENER_DELETES_INFLIGHT"]
    and checks["LISTENER_RESOLVES_CARD"]
    and checks["LISTENER_HAS_CARD_MISS_RETURN"]
    and (not checks["LISTENER_CALLS_ACK_API"])
    and checks["PRELOAD_EXPOSES_ACK_API"]
    and checks["MAIN_IPC_HANDLES_ACK"]
    and checks["SERVICE_HAS_ACK_METHOD"]
)

if not expected:
    die("ACK_CALLSITE_GAP_NOT_CONFIRMED", 20)

emit("ASSERT_RESULT=CONFIRMED")
emit("BOUNDARY=Renderer evidenceResultListener handles delivery result locally but does not invoke durable acknowledgeVraEvidenceDelivery API; ACK API exists through preload/Main/service.")
emit("PRODUCTION_MUTATION=NONE")
raise SystemExit(0)
