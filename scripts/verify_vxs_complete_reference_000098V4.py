from pathlib import Path
import hashlib
import sys

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / r"docs/VXS_COMPLETE_REFERENCE.md"
EXPECTED_SHA = "bbe9379dca9001009f53b0188b3e7823ec36ac0c04b3d87e62cc326923c8647f"

def fail(message: str) -> int:
    print("VXS_COMPLETE_REFERENCE_VERIFY=FAIL")
    print("REASON=" + message)
    return 97

if not DOC.is_file():
    raise SystemExit(fail("DOC_MISSING:" + str(DOC)))

raw = DOC.read_bytes()
actual = hashlib.sha256(raw).hexdigest()
print("DOC_PATH=" + str(DOC))
print("DOC_BYTES=" + str(len(raw)))
print("DOC_SHA256=" + actual)

if actual != EXPECTED_SHA:
    raise SystemExit(fail("SHA_MISMATCH"))

text = raw.decode("utf-8")
required = [
    "# VXS Complete Reference",
    "# 5. Human Gate / AUTH",
    "# 7. Direct VRA → VXS loopback nerve",
    "127.0.0.1:47834",
    "VERA_VXS_HUMAN_GATE_REQUIRED",
    "# 9. Persistent VERA session workspace",
    "VERA04 · S04",
    "# 10. Command registry",
    "vxs capabilities --json",
    "# 11. PowerShell provider / compatibility",
    "vxs ps engine",
    "# 14. Evidence interpretation contract",
    "RETURN_QUEUED",
    "# 17. Production verification milestones",
    "vertex-session-portal-vxs-vera-persistent-workspace-tab-000097V4",
    "# 20. Design invariants",
    "There is one canonical `VertexShellService`",
    "# 24. Source-of-truth rule",
]
missing = [token for token in required if token not in text]
if missing:
    print("MISSING=" + "|".join(missing))
    raise SystemExit(fail("REQUIRED_CONTENT_MISSING"))

if len(raw) < 12000:
    raise SystemExit(fail("DOC_UNEXPECTEDLY_SHORT"))

print("REQUIRED_SECTIONS=" + str(len(required)))
print("VXS_COMPLETE_REFERENCE_VERIFY=PASS")
raise SystemExit(0)
