from pathlib import Path
import re
import subprocess

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
LANE = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def die(msg, code=1):
    emit("REPAIR_STATUS=FAILED")
    emit("DETAIL=" + msg)
    raise SystemExit(code)

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

def extract_method(text: str, marker: str):
    start = text.find(marker)
    if start < 0:
        die("METHOD_NOT_FOUND:" + marker, 10)
    brace = text.find("{", start)
    if brace < 0:
        die("METHOD_OPEN_BRACE_NOT_FOUND", 11)

    depth = 0
    quote = None
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        if quote is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
        else:
            if ch in ("'", '"', "`"):
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return start, i + 1, text[start:i+1]
        i += 1
    die("METHOD_CLOSE_BRACE_NOT_FOUND", 12)

if not LANE.exists():
    die("SOURCE_MISSING:" + str(LANE), 13)

before = LANE.read_text(encoding="utf-8")

# 000084 repair must already exist.
for anchor in (
    "private readonly evidenceResultListener",
    "evidenceInFlight.has(result.deliveryId)",
    "candidate.evidenceIdentity === result.deliveryId",
    "candidate.jobId === result.jobId",
    "acknowledgeVraEvidenceDelivery",
    "evidenceInFlight.delete(result.deliveryId)",
):
    if anchor not in before:
        die("REQUIRED_000084_ANCHOR_MISSING:" + anchor, 14)

if "evidenceCardResolveAttempts" in before:
    die("RETRY_REPAIR_ALREADY_PRESENT", 15)

# Locate the in-flight field exactly once.
field_matches = list(re.finditer(
    r"(?m)^(?P<indent>\s*)private readonly evidenceInFlight\s*=\s*new Set(?:<[^>]+>)?\(\)\s*$",
    before,
))
if len(field_matches) != 1:
    die(f"EVIDENCE_INFLIGHT_FIELD_MATCHES={len(field_matches)}", 16)

fm = field_matches[0]
field_line = fm.group(0)
indent = fm.group("indent")
field_replacement = (
    field_line
    + "\n"
    + indent
    + "private readonly evidenceCardResolveAttempts = new Map<string, number>()"
)

# Scope card-miss replacement strictly to evidenceResultListener.
mstart, mend, listener = extract_method(before, "private readonly evidenceResultListener")
card_miss_pattern = re.compile(r"(?m)^(?P<indent>\s*)if\s*\(\s*!card\s*\)\s*return\s*$")
card_matches = list(card_miss_pattern.finditer(listener))
if len(card_matches) != 1:
    die(f"LISTENER_CARD_MISS_MATCHES={len(card_matches)}", 17)

cm = card_matches[0]
ci = cm.group("indent")
retry_block = "\n".join([
    f"{ci}if (!card) {{",
    f"{ci}  const resolveAttempt = this.evidenceCardResolveAttempts.get(result.deliveryId) ?? 0",
    f"{ci}  if (resolveAttempt >= 8) return",
    "",
    f"{ci}  this.evidenceCardResolveAttempts.set(result.deliveryId, resolveAttempt + 1)",
    f"{ci}  window.setTimeout(() => {{",
    f"{ci}    this.evidenceResultListener(event)",
    f"{ci}  }}, Math.min(1000, 250 * (resolveAttempt + 1)))",
    f"{ci}  return",
    f"{ci}}}",
    "",
    f"{ci}this.evidenceCardResolveAttempts.delete(result.deliveryId)",
])

listener_after = (
    listener[:cm.start()]
    + retry_block
    + listener[cm.end():]
)

# Reconstruct file first with listener change, then field change.
after_listener = before[:mstart] + listener_after + before[mend:]
after = after_listener.replace(field_line, field_replacement, 1)

# Prewrite fail-closed assertions.
_, _, listener_check = extract_method(after, "private readonly evidenceResultListener")
ack_pos = listener_check.find("acknowledgeVraEvidenceDelivery")
clear_pos = listener_check.find("evidenceInFlight.delete(result.deliveryId)")
retry_pos = listener_check.find("evidenceCardResolveAttempts")
card_pos = listener_check.find("if (!card) {")

checks = {
    "RETRY_FIELD_ADDED": "private readonly evidenceCardResolveAttempts = new Map<string, number>()" in after,
    "CARD_MISS_RETRY_ADDED": card_pos >= 0 and retry_pos >= 0,
    "EVENT_REPLAY_ADDED": "this.evidenceResultListener(event)" in listener_check,
    "BOUNDED_RETRY": "resolveAttempt >= 8" in listener_check,
    "ACK_CALLSITE_PRESERVED": ack_pos >= 0,
    "INFLIGHT_CLEAR_AFTER_ACK": clear_pos > ack_pos >= 0,
    "IDENTITY_MATCH_PRESERVED": (
        "candidate.evidenceIdentity === result.deliveryId" in listener_check
        and "candidate.jobId === result.jobId" in listener_check
    ),
}
for name, ok in checks.items():
    emit(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        die("PREWRITE_ASSERTION_FAILED:" + name, 18)

changed = False
try:
    LANE.write_text(after, encoding="utf-8", newline="\n")
    changed = True

    now = LANE.read_text(encoding="utf-8", errors="replace")
    _, _, listener_now = extract_method(now, "private readonly evidenceResultListener")

    post = {
        "RETRY_FIELD_PRESENT": "evidenceCardResolveAttempts" in now,
        "LISTENER_REPLAY_PRESENT": "this.evidenceResultListener(event)" in listener_now,
        "ACK_CALLSITE_PRESENT": "acknowledgeVraEvidenceDelivery" in listener_now,
        "INFLIGHT_CLEAR_PRESENT": "evidenceInFlight.delete(result.deliveryId)" in listener_now,
    }
    for name, ok in post.items():
        emit(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError("POSTWRITE_ASSERTION_FAILED:" + name)

    if run_npm("run", "typecheck") != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run_npm("run", "build") != 0:
        raise RuntimeError("BUILD_FAILED")

    emit("REPAIR_SCOPE=1_FILE")
    emit("TARGET=src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts")
    emit("CARD_MISS_BEHAVIOR=BOUNDED_REPLAY")
    emit("MAX_CARD_RESOLVE_ATTEMPTS=8")
    emit("REPLAY_USES_ORIGINAL_RESULT_EVENT=YES")
    emit("INFLIGHT_PRESERVED_UNTIL_ACK=YES")
    emit("RUNTIME_RESTART_REQUIRED=YES")
    emit("REPAIR_STATUS=SUCCEEDED")
    raise SystemExit(0)

except SystemExit:
    raise
except Exception as e:
    if changed:
        try:
            LANE.write_text(before, encoding="utf-8", newline="\n")
            emit("SELF_ROLLBACK=RESTORED_RENDERER_SOURCE")
        except Exception as rollback_error:
            emit("SELF_ROLLBACK=FAILED")
            emit("SELF_ROLLBACK_DETAIL=" + repr(rollback_error))
    die(type(e).__name__ + ":" + str(e), 20)
