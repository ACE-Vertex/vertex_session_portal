from pathlib import Path
import subprocess,sys

ROOT=Path.cwd()
CJS=ROOT/"scripts/apply_vra_builder_core_000201V2.cjs"

def read(p):
    try:return p.read_text(encoding="utf-8-sig",errors="replace")
    except Exception:return ""

if "validateVraAgainstActivePolicy" not in read(ROOT/"src/shared/vra-policy-validator.ts"): sys.exit(45)
if "resolveActiveSystemPolicy" not in read(ROOT/"src/shared/system-policy-registry.ts"): sys.exit(46)
if not CJS.is_file(): sys.exit(47)

try:
    r=subprocess.run(
        ["node","scripts/apply_vra_builder_core_000201V2.cjs"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=240
    )
except subprocess.TimeoutExpired:
    sys.exit(48)
except Exception:
    sys.exit(49)

sys.exit(r.returncode if 0 <= r.returncode <= 32000 else 50)
