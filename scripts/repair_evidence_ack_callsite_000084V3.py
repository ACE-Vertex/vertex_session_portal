from pathlib import Path
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
PRELOAD = ROOT / "src/preload/index.ts"
IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def die(msg, code=1):
    emit("REPAIR_STATUS=FAILED")
    emit("DETAIL=" + msg)
    raise SystemExit(code)

def extract_listener(text: str):
    marker = "private readonly evidenceResultListener"
    start = text.find(marker)
    if start < 0:
        die("LISTENER_NOT_FOUND", 10)

    brace = text.find("{", start)
    if brace < 0:
        die("LISTENER_OPEN_BRACE_NOT_FOUND", 11)

    depth = 0
    in_s = None
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        if in_s:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_s:
                in_s = None
        else:
            if ch in ("'", '"', "`"):
                in_s = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1, text[start:i+1]
        i += 1
    die("LISTENER_CLOSE_BRACE_NOT_FOUND", 12)

def run_npm(*args):
    cp = subprocess.run(
        ["npm.cmd", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=420,
    )
    emit(f"CMD=npm.cmd {' '.join(args)} EXIT={cp.returncode}")
    if cp.stdout:
        emit("STDOUT_TAIL=" + cp.stdout[-5000:].replace("\r", " ").replace("\n", "\\n"))
    if cp.stderr:
        emit("STDERR_TAIL=" + cp.stderr[-5000:].replace("\r", " ").replace("\n", "\\n"))
    return cp.returncode

for p in (LANE, PRELOAD, IPC, SERVICE):
    if not p.exists():
        die("SOURCE_MISSING:" + str(p), 13)

lane_before = LANE.read_text(encoding="utf-8")
preload = PRELOAD.read_text(encoding="utf-8", errors="replace")
ipc = IPC.read_text(encoding="utf-8", errors="replace")
service = SERVICE.read_text(encoding="utf-8", errors="replace")

backend_checks = {
    "PRELOAD_ACK": "acknowledgeVraEvidenceDelivery" in preload and "workstation:vra-evidence-ack" in preload,
    "IPC_ACK": "workstation:vra-evidence-ack" in ipc and "acknowledgeEvidenceDelivery" in ipc,
    "SERVICE_ACK": "acknowledgeEvidenceDelivery" in service,
}
for name, ok in backend_checks.items():
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        die("BACKEND_ACK_PATH_INCOMPLETE:" + name, 14)

start, end, listener = extract_listener(lane_before)

required = [
    "evidenceInFlight.has(result.deliveryId)",
    "evidenceInFlight.delete(result.deliveryId)",
    "candidate.evidenceIdentity === result.deliveryId",
    "candidate.jobId === result.jobId",
    "if (!card) return",
]
for anchor in required:
    if anchor not in listener:
        die("LISTENER_ANCHOR_MISSING:" + anchor, 15)

if "acknowledgeVraEvidenceDelivery" in listener:
    die("ACK_CALLSITE_ALREADY_PRESENT", 16)

delete_line = "    this.evidenceInFlight.delete(result.deliveryId)\n"
if listener.count(delete_line) != 1:
    die(f"DELETE_LINE_COUNT={listener.count(delete_line)}", 17)

card_anchor = "    if (!card) return\n"
if listener.count(card_anchor) != 1:
    die(f"CARD_ANCHOR_COUNT={listener.count(card_anchor)}", 18)

ack_block = '''    if (!card) return

    const returnedAt = new Date().toISOString()
    const acknowledge = (attempt: number): void => {
      void window.vertexPortal.acknowledgeVraEvidenceDelivery({
        cardId: card.id,
        evidenceId: result.deliveryId,
        artifactId: card.artifactId || card.filename || card.id,
        returnedAt
      }).then(ack => {
        if (
          ack.acknowledged ||
          ack.idempotent ||
          ack.evidenceReturnState === 'RETURNED'
        ) {
          this.evidenceInFlight.delete(result.deliveryId)
          return
        }

        if (attempt < 3) {
          window.setTimeout(() => acknowledge(attempt + 1), 500 * attempt)
        }
      }).catch(() => {
        if (attempt < 3) {
          window.setTimeout(() => acknowledge(attempt + 1), 500 * attempt)
        }
      })
    }

    acknowledge(1)
'''

listener_after = listener.replace(delete_line, "", 1)
listener_after = listener_after.replace(card_anchor, ack_block, 1)

guard_pos = listener_after.find("evidenceInFlight.has(result.deliveryId)")
card_pos = listener_after.find("if (!card) return")
ack_pos = listener_after.find("acknowledgeVraEvidenceDelivery")
delete_pos = listener_after.find("evidenceInFlight.delete(result.deliveryId)")
if not (0 <= guard_pos < card_pos < ack_pos < delete_pos):
    die(
        f"PATCH_ORDER_INVALID guard={guard_pos} card={card_pos} ack={ack_pos} delete={delete_pos}",
        19,
    )

lane_after = lane_before[:start] + listener_after + lane_before[end:]
changed = False

try:
    LANE.write_text(lane_after, encoding="utf-8", newline="\n")
    changed = True

    now = LANE.read_text(encoding="utf-8", errors="replace")
    _, _, listener_now = extract_listener(now)

    assertions = {
        "ACK_CALLSITE_PRESENT": "acknowledgeVraEvidenceDelivery" in listener_now,
        "DELETE_AFTER_ACK": listener_now.find("evidenceInFlight.delete(result.deliveryId)") >
                            listener_now.find("acknowledgeVraEvidenceDelivery"),
        "CARD_MISS_PRESERVES_INFLIGHT": listener_now.find("if (!card) return") <
                                      listener_now.find("acknowledgeVraEvidenceDelivery"),
        "BOUNDED_ACK_RETRY_PRESENT": "if (attempt < 3)" in listener_now and
                                     "window.setTimeout(() => acknowledge(attempt + 1)" in listener_now,
    }
    for name, ok in assertions.items():
        emit(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError("POST_PATCH_ASSERTION_FAILED:" + name)

    if run_npm("run", "typecheck") != 0:
        raise RuntimeError("TYPECHECK_FAILED")

    if run_npm("run", "build") != 0:
        raise RuntimeError("BUILD_FAILED")

    emit("REPAIR_SCOPE=1_FILE")
    emit("TARGET=src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
    emit("DURABLE_ACK_CALLSITE=ADDED")
    emit("INFLIGHT_CLEAR=AFTER_ACK_ONLY")
    emit("CARD_MISS_DROP=REMOVED")
    emit("ACK_RETRY=BOUNDED_3_ATTEMPTS")
    emit("RUNTIME_RESTART_REQUIRED=YES")
    emit("REPAIR_STATUS=SUCCEEDED")
    raise SystemExit(0)

except SystemExit:
    raise
except Exception as e:
    if changed:
        try:
            LANE.write_text(lane_before, encoding="utf-8", newline="\n")
            emit("SELF_ROLLBACK=RESTORED_RENDERER_SOURCE")
        except Exception as rollback_error:
            emit("SELF_ROLLBACK=FAILED")
            emit("SELF_ROLLBACK_DETAIL=" + repr(rollback_error))
    die(type(e).__name__ + ":" + str(e), 20)
