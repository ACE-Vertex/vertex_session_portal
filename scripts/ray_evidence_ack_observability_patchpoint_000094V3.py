from pathlib import Path
import re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
TAP = ROOT / "src/main/observability/evidence-return-tap.ts"

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def fail(code, reason):
    emit("RAY_CLASSIFICATION=" + reason)
    emit("PRODUCTION_MUTATION=NONE")
    raise SystemExit(code)

def extract_block(text: str, marker: str):
    start = text.find(marker)
    if start < 0:
        return None
    brace = text.find("{", start)
    if brace < 0:
        return None
    depth = 0
    quote = None
    escape = False
    i = brace
    while i < len(text):
        ch = text[i]
        if quote:
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
                    return text[start:i+1]
        i += 1
    return None

for p in (SERVICE, TAP):
    if not p.exists():
        fail(84, "SOURCE_MISSING:" + str(p))

service = SERVICE.read_text(encoding="utf-8", errors="replace")
tap = TAP.read_text(encoding="utf-8", errors="replace")

ack = extract_block(service, "acknowledgeEvidenceDelivery")
tap_class = extract_block(tap, "class EvidenceReturnObservabilityTap") or extract_block(tap, "export class EvidenceReturnObservabilityTap")

if not ack:
    fail(84, "ACK_METHOD_EXTRACTION_FAILED")
if not tap_class:
    fail(84, "TAP_CLASS_EXTRACTION_FAILED")

# Discover actual callable methods on the tap class and existing service instance/member.
method_names = []
for m in re.finditer(r"(?m)^\s*(?:public\s+|private\s+|protected\s+)?(?:async\s+)?([A-Za-z_$][\w$]*)\s*\(", tap_class):
    name = m.group(1)
    if name not in ("constructor",):
        method_names.append(name)

service_member_candidates = []
for m in re.finditer(r"(?m)^\s*(?:private|public|protected)\s+(?:readonly\s+)?([A-Za-z_$][\w$]*)\s*[:=][^\n]*EvidenceReturnObservabilityTap", service):
    service_member_candidates.append(m.group(1))
for m in re.finditer(r"new\s+EvidenceReturnObservabilityTap\s*\(", service):
    window = service[max(0, m.start()-200):m.start()]
    mm = re.search(r"([A-Za-z_$][\w$]*)\s*=\s*$", window)
    if mm:
        service_member_candidates.append(mm.group(1))

# Durable sink / record semantics in tap implementation.
durable_markers = {
    "JSONL": "jsonl" in tap.lower(),
    "APPEND_FILE": "appendfile" in tap.lower() or "appendfilesync" in tap.lower(),
    "WRITE_FILE": "writefile" in tap.lower() or "writefilesync" in tap.lower(),
    "USER_DATA": "userData" in tap or "app.getPath('userData')" in tap or 'app.getPath("userData")' in tap,
}
for k,v in durable_markers.items():
    emit(f"TAP_{k}={'YES' if v else 'NO'}")

emit("TAP_METHODS=" + (",".join(sorted(set(method_names))) if method_names else "-"))
emit("SERVICE_TAP_MEMBERS=" + (",".join(sorted(set(service_member_candidates))) if service_member_candidates else "-"))

# Print bounded source needed for the next production-safe patch.
emit("=== ACK_METHOD ===")
for i,line in enumerate(ack.splitlines(),1):
    emit(f"{i:04d}: {line}")
emit("=== END_ACK_METHOD ===")

emit("=== TAP_CLASS ===")
for i,line in enumerate(tap_class.splitlines(),1):
    emit(f"{i:04d}: {line}")
emit("=== END_TAP_CLASS ===")

# Decide whether we have enough concrete source structure for a deterministic patch.
has_durable_sink = any(durable_markers.values())
has_callable_tap = len(method_names) > 0
has_service_tap_binding = len(service_member_candidates) > 0

if has_durable_sink and has_callable_tap and has_service_tap_binding:
    emit("RAY_CLASSIFICATION=PATCHPOINT_READY")
    emit("PRODUCTION_MUTATION=NONE")
    raise SystemExit(0)

if has_durable_sink and has_callable_tap and not has_service_tap_binding:
    fail(81, "DURABLE_TAP_EXISTS_BUT_SERVICE_BINDING_NOT_FOUND")

if has_durable_sink and not has_callable_tap:
    fail(82, "DURABLE_TAP_EXISTS_BUT_CALLABLE_METHOD_NOT_FOUND")

fail(83, "NO_DURABLE_TAP_SINK_FOUND")
