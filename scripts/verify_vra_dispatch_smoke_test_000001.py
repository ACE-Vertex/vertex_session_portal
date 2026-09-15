from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = ROOT / "docs" / "TESTS" / "VRA_DISPATCH_SMOKE_TEST_000001.md"

print("VERTEX SESSION PORTAL / VRA DISPATCH SMOKE TEST 000001")
print(f"ROOT={ROOT}")

if not MARKER.exists():
    raise SystemExit("MARKER_FILE=FAIL")

text = MARKER.read_text(encoding="utf-8")
if "VRA_DISPATCH_SMOKE_TEST_000001=READY" not in text:
    raise SystemExit("MARKER_CONTENT=FAIL")

print("MARKER_FILE=PASS")
print("MARKER_CONTENT=PASS")
print("VERTEX_SESSION_PORTAL_VRA_DISPATCH_SMOKE_TEST_000001=PASS")
