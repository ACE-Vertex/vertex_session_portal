from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[2]
MARKER = ROOT / "runtime/roundtrip-smoke/VERA05_000077V5.txt"

EXPECTED = {
    "VERTEX_NEW_FACTORY_ROUNDTRIP_SMOKE_000077V5=PASS",
    "ORIGIN_VERA=VERA05",
    "ORIGIN_SESSION=vera-05",
    "PURPOSE=E2E_FORWARD_EXECUTION_EVIDENCE_RETURN",
    "MUTATION_SCOPE=SMOKE_MARKER_ONLY",
}

print("=== VERTEX NEW FACTORY ROUNDTRIP SMOKE 000077V5 ===")
print(f"ROOT={ROOT}")
print("VERIFY_MODE=READ_ONLY")
print("HUMAN_GATE=REQUIRED")
print("EXPECTED_RETURN_ORIGIN=vera-05")

if not MARKER.is_file():
    print("MARKER_PRESENT=FAIL")
    raise SystemExit(1)

text = MARKER.read_text(encoding="utf-8-sig")
lines = {line.strip() for line in text.splitlines() if line.strip()}

missing = sorted(EXPECTED - lines)
print(f"MARKER_PRESENT=PASS")
print(f"MARKER_SHA256={hashlib.sha256(MARKER.read_bytes()).hexdigest()}")
print(f"EXPECTED_LINES={len(EXPECTED)}")
print(f"MISSING_LINES={len(missing)}")

if missing:
    for item in missing:
        print(f"MISSING={item}")
    print("VERTEX_NEW_FACTORY_ROUNDTRIP_SMOKE_000077V5=FAIL")
    raise SystemExit(1)

print("VERTEX_NEW_FACTORY_ROUNDTRIP_SMOKE_000077V5=PASS")
raise SystemExit(0)
