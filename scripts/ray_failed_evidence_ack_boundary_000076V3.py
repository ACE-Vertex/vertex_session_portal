from pathlib import Path
import re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

TARGETS = [
    ("src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts", [
        ("evidenceResultListener", 80, 170),
        ("copy_error_card_region", 1500, 1710),
    ]),
    ("src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts", [
        ("evidence_listener_and_delivery", 40, 140),
        ("delivery_method_search", 1, 520),
    ]),
    ("src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts", [
        ("injector", 1, 260),
    ]),
    ("src/main/vra/vra-dispatch-service.ts", [
        ("ack_method_search", 1, 3200),
    ]),
    ("src/main/vra-registry/auto-registry-workstation-sync.ts", [
        ("full_sync", 1, 220),
    ]),
    ("src/main/vra-registry/vra-registry-core.ts", [
        ("registry_core", 1, 260),
    ]),
]

def safe(s):
    return str(s).encode("ascii", "backslashreplace").decode("ascii")

def emit(s=""):
    print(safe(s))

def print_range(path, lines, label, start, end):
    emit(f"\n=== {label} :: {path.as_posix()} lines {start}-{min(end, len(lines))} ===")
    for n in range(max(1, start), min(end, len(lines)) + 1):
        emit(f"{n:05d}: {lines[n-1]}")

def print_function_by_marker(path, lines, marker, before=12, after=140):
    hits = [i for i,l in enumerate(lines) if marker in l]
    emit(f"\n=== MARKER {marker} :: {path.as_posix()} hits={len(hits)} ===")
    for idx in hits[:8]:
        start=max(0,idx-before); end=min(len(lines),idx+after)
        for j in range(start,end):
            emit(f"{j+1:05d}: {lines[j]}")
        emit("---")

emit("FAILED_EVIDENCE_ACK_BOUNDARY_RAY_000076V3=BEGIN")

for rel, ranges in TARGETS:
    path = ROOT / rel
    if not path.exists():
        emit(f"MISSING={rel}")
        continue
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        emit(f"READ_ERROR={rel}:{type(e).__name__}:{e}")
        continue

    for label,start,end in ranges:
        if label.endswith("_search"):
            # handled below by exact marker searches to keep output bounded
            continue
        print_range(path, lines, label, start, end)

    if rel.endswith("VraDispatchLane.ts"):
        for marker in [
            "evidenceInFlight",
            "VERA_EVIDENCE_RETURN_EVENT",
            "acknowledgeVraEvidenceDelivery",
            "evidenceDeliveryPayload",
            "writeClipboard",
            "COPY",
        ]:
            print_function_by_marker(path, lines, marker, before=10, after=55)

    if rel.endswith("VeraBrowserSession.ts"):
        for marker in [
            "deliverWorkstationEvidence",
            "VERA_EVIDENCE_RETURN_RESULT_EVENT",
            "evidenceReturnListener",
        ]:
            print_function_by_marker(path, lines, marker, before=12, after=90)

    if rel.endswith("VeraEvidenceReturnInjector.ts"):
        for marker in [
            "VERA_EVIDENCE_RETURN_EVENT",
            "VERA_EVIDENCE_RETURN_RESULT_EVENT",
            "inject",
            "dispatchEvent",
        ]:
            print_function_by_marker(path, lines, marker, before=10, after=90)

    if rel.endswith("vra-dispatch-service.ts"):
        for marker in [
            "acknowledgeEvidenceDelivery",
            "evidenceDeliveryPayload",
            "RETURN_QUEUED",
            "RETURNED",
            "syncAutoRegistryWorkstationLifecycle",
        ]:
            print_function_by_marker(path, lines, marker, before=18, after=120)

    if rel.endswith("auto-registry-workstation-sync.ts"):
        print_range(path, lines, "AUTO_REGISTRY_SYNC_FULL", 1, min(220, len(lines)))

    if rel.endswith("vra-registry-core.ts"):
        print_range(path, lines, "REGISTRY_CORE_FULL", 1, min(260, len(lines)))

emit("\nRAY_ASSERTIONS:")
emit("MUTATION=NONE")
emit("PURPOSE=Locate first durable disagreement between failed Workstation outcome and Evidence ACK/RETURNED lifecycle.")
emit("RAY_RESULT=SOURCE_BOUNDARIES_CAPTURED")
emit("FAILED_EVIDENCE_ACK_BOUNDARY_RAY_000076V3=PASS")
raise SystemExit(0)
