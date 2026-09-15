
from pathlib import Path
import json, sys

DEV = Path(r"G:\Vertex_Project\Development")

# Exit code map:
# 0  = exactly one valid canonical VRA manifest candidate found
# 31 = multiple valid canonical VRA manifest candidates found
# 32 = candidate files found, but none validate as current canonical vra/1
# 33 = no plausible canonical manifest candidate found
# 34 = search failed unexpectedly
#
# Read-only: no file writes, no source mutation.

def valid_manifest(path: Path) -> bool:
    try:
        if not path.is_file() or path.stat().st_size > 2_000_000:
            return False
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if data.get("schema_version") != "vra/1":
            return False
        if data.get("authority") != "HUMAN_APPLY":
            return False
        routing = data.get("routing") or {}
        if routing.get("contract_version") != "vra-routing/1":
            return False
        ops = data.get("operations")
        verification = data.get("verification")
        if not isinstance(ops, list) or not isinstance(verification, list):
            return False
        return True
    except Exception:
        return False

try:
    plausible = []

    # Strong-name search first.
    strong_names = {
        "VRA_CANONICAL_MANIFEST_vra-1_000150V5.json",
        "VRA_CANONICAL_MANIFEST_vra-1.json",
        "vra-canonical-manifest-vra-1.json",
        "vra_canonical_manifest_vra-1.json",
    }

    # Bounded recursive search under Development.
    for p in DEV.rglob("*.json"):
        try:
            if not p.is_file():
                continue
            name_lower = p.name.lower()
            path_lower = str(p).lower()

            strong = p.name in strong_names
            semantic = (
                ("canonical" in name_lower and "vra" in name_lower) or
                ("vra_manifest" in path_lower and "manifest" in name_lower) or
                ("vra-manifest" in path_lower and "canonical" in name_lower)
            )
            if strong or semantic:
                plausible.append(p)
        except Exception:
            pass

    # De-duplicate path identity.
    seen = set()
    dedup = []
    for p in plausible:
        s = str(p).lower()
        if s not in seen:
            seen.add(s)
            dedup.append(p)

    valid = [p for p in dedup if valid_manifest(p)]

    if len(valid) == 1:
        sys.exit(0)
    if len(valid) > 1:
        sys.exit(31)
    if dedup:
        sys.exit(32)
    sys.exit(33)

except Exception:
    sys.exit(34)
