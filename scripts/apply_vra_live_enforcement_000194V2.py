from pathlib import Path
import subprocess,sys

ROOT=Path.cwd()
VALIDATOR=ROOT/"src/shared/vra-policy-validator.ts"
POLICY=ROOT/"src/shared/system-policy-registry.ts"
CJS=ROOT/"scripts/apply_vra_live_enforcement_000194V2.cjs"

def read(p):
    try:return p.read_text(encoding="utf-8-sig",errors="replace")
    except Exception:return None

v=read(VALIDATOR)
p=read(POLICY)
if v is None or "validateVraAgainstActivePolicy" not in v: sys.exit(45)
if p is None or "resolveActiveSystemPolicy" not in p: sys.exit(46)
if not CJS.is_file(): sys.exit(47)

try:
    run=subprocess.run(
        ["node","scripts/apply_vra_live_enforcement_000194V2.cjs"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=150
    )
except subprocess.TimeoutExpired:
    sys.exit(48)
except Exception:
    sys.exit(49)

if run.returncode==0:
    sys.exit(0)

sys.exit(run.returncode if 1 <= run.returncode <= 32000 else 50)
