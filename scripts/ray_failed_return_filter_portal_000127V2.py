
from pathlib import Path
import re, sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SCAN = ROOT / "src"
if not SCAN.exists():
    sys.exit(41)

EXTS = {".ts",".tsx",".js",".mjs",".cjs",".py",".rs"}
SKIP = {"node_modules",".git","dist","build","target",".next","coverage","runtime"}
success_terms = re.compile(r"\b(verified|succeeded|success|VERIFIED|SUCCESS)\b", re.I)
return_terms = re.compile(r"(RETURN_QUEUED|return_channel|return.?queue|evidence.?return|enqueue|publish|inject|rebind|deliver)", re.I)
failure_terms = re.compile(r"\b(failed|failure|FAILED|rollback|verify_failed)\b", re.I)
condition_terms = re.compile(r"\b(if|when|case|switch|filter|guard)\b", re.I)

hits = []
for p in SCAN.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in EXTS:
        continue
    if any(part.lower() in SKIP for part in p.parts):
        continue
    try:
        s = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    low = s.lower()
    if "evidence" not in low:
        continue

    # Examine windows around return/injection operations.
    for m in return_terms.finditer(s):
        a=max(0,m.start()-1200); b=min(len(s),m.end()+1200)
        w=s[a:b]
        if not success_terms.search(w):
            continue
        if not condition_terms.search(w):
            continue

        # Stronger suspicion: success/verified gate is close to return op,
        # while explicit failed/rollback handling is absent from same window.
        if not failure_terms.search(w):
            hits.append((str(p), m.group(0)))
            break

# Success means an explicit success-only-looking gate was found.
# Nonzero means "not proven by this Ray", not "system healthy".
sys.exit(0 if hits else 42)
