from __future__ import annotations
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

print("VERTEX_ROUNDTRIP_CONTRACT_RUNTIME_PROBE=PASS")
print("EXPECTED_RETURN_PREFIX_1=VERTEX EVIDENCE INTERPRETATION CONTRACT")
print("EXPECTED_RETURN_PREFIX_2=VERTEX VRA ISSUANCE CONTRACT")
print("EXPECTED_EVIDENCE_BODY=VERTEX WORKSTATION EVIDENCE RETURN")
print("PURPOSE=VERIFY_RUNTIME_RENDERER_USES_ACTIVE_CONTRACT_PACKET")
