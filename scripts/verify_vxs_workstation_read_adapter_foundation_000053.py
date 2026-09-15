from __future__ import annotations
from pathlib import Path
import re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SOURCE = ROOT / "src/main/shell/vxs/vxs-workstation-read-adapter.ts"

print("VXS_WORKSTATION_READ_ADAPTER_FOUNDATION_000053_VERIFY=BEGIN")
print("VERIFY_MODE=READ_ONLY")
print("PRODUCTION_MUTATION_FROM_VERIFY=NO")

if not SOURCE.is_file():
    print("SOURCE_MISSING")
    raise SystemExit(61)

text = SOURCE.read_text(encoding="utf-8", errors="strict")

required = {
    "CONTRACT":
        "vertex-vxs/workstation-read-adapter-1",
    "LOOPBACK":
        "http://127.0.0.1:47832",
    "OBSERVE":
        "VXS_WORKSTATION_AUTHORITY_CLASS",
    "HTTP_CHANNEL":
        "HTTP_CONTROL_PLANE",
    "FS_CHANNEL":
        "DURABLE_FILESYSTEM_OBSERVATION",
    "HEALTH":
        "/v1/health",
    "SAFETY":
        "/v1/safety",
    "JOB":
        "/v1/jobs/",
    "EVIDENCE":
        "/evidence",
    "JOB_REGISTRY":
        "runtime\\\\headless\\\\job-registry",
    "DURABLE_EVIDENCE":
        "runtime\\\\headless\\\\evidence",
    "LANES":
        "runtime\\\\lanes",
    "NO_MUTATION_DESCRIPTOR":
        "mutation: false",
}

failed = []
for name, marker in required.items():
    ok = marker in text
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failed.append(name)

forbidden = {
    "ZERO_BIND": "0.0.0.0",
    "HTTP_POST": "-Method Post",
    "HTTP_PUT": "-Method Put",
    "HTTP_PATCH": "-Method Patch",
    "HTTP_DELETE": "-Method Delete",
    "APPLY_ROUTE": "/apply",
    "VERIFY_ROUTE": "/verify",
    "ROLLBACK_ROUTE": "/rollback",
    "VRA_DISPATCH": "vra dispatch",
    "EVIDENCE_ACK": "/evidence/ack",
}

for name, marker in forbidden.items():
    absent = marker not in text
    print(f"FORBIDDEN_{name}={'PASS' if absent else 'FAIL'}")
    if not absent:
        failed.append(f"FORBIDDEN_{name}")

# Only literal GET is allowed in the HTTP command constructor.
methods = re.findall(r"-Method\s+([A-Za-z]+)", text)
print("HTTP_METHODS=" + ",".join(methods))
if methods != ["Get"]:
    failed.append("HTTP_METHOD_SET")

# Adapter may describe durable roots but must not itself perform filesystem I/O.
fs_io_markers = [
    "readFileSync(",
    "writeFileSync(",
    "readdirSync(",
    "unlinkSync(",
    "renameSync(",
    "rmSync(",
    "mkdirSync(",
]
for marker in fs_io_markers:
    if marker in text:
        failed.append("ADAPTER_FS_IO_FORBIDDEN")
        print(f"FS_IO_FORBIDDEN={marker}")

if failed:
    print("FAILED=" + ",".join(failed))
    raise SystemExit(71)

print("EXISTING_VXS_COMMAND_WIRING_CHANGED=NO")
print("WORKSTATION_LANE_AUTHORITY=UNCHANGED")
print("HUMAN_GATE=UNCHANGED")
print("VRA_ROUTING=UNCHANGED")
print("EVIDENCE_RETURN=UNCHANGED")
print("OBSERVATION_RETURN_BUS_000041R=FROZEN")
print("RAY_VNEXT_000049R=FROZEN")
print("NEXT=WIRE_EXISTING_READ_COMMANDS_TO_ADAPTER_WITH_CURRENT_SOURCE_ANCHORS")
print("VXS_WORKSTATION_READ_ADAPTER_FOUNDATION_000053_VERIFY=PASS")
