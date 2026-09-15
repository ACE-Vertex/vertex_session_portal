
from pathlib import Path
import subprocess, sys, shutil, time, re

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
TARGET = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / "EVIDENCE" / "VRA_CONTRACT_NEWLINE_REPAIR_000041V2" / STAMP
MARKER = "VERTEX_VRA_CONTRACT_NEWLINE_REPAIR_000041V2"

def log(v=""):
    print(str(v).encode("ascii","backslashreplace").decode("ascii"))

def read(p):
    if not p.exists():
        raise RuntimeError(f"MISSING:{p}")
    return p.read_text(encoding="utf-8-sig")

def write(p,s):
    p.write_text(s, encoding="utf-8")

def run_npm(args):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    p = subprocess.run([npm,*args], cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True)
    log(f"RUN={npm} {' '.join(args)}")
    log(f"EXIT={p.returncode}")
    for line in (p.stdout+"\n"+p.stderr).splitlines()[-80:]:
        log(line)
    return p.returncode

source0 = read(TARGET)

if MARKER in source0:
    raise SystemExit("ALREADY_APPLIED")
if "renderVraIssueContract" not in source0:
    raise SystemExit("VRA_RENDERER_NOT_FOUND")
if "VERTEX_ROUNDTRIP_CONTRACT_PACKET_000039V2" not in source0:
    raise SystemExit("ROUNDTRIP_BASE_NOT_FOUND")

start = source0.find("function renderVraIssueContract")
end = source0.find("async function evidencePayloadWithActiveContract", start)
if start < 0 or end < 0:
    raise SystemExit("VRA_RENDERER_BOUNDARY_NOT_FOUND")

block0 = source0[start:end]
bad = r"return lines.join('\\n')"
good = r"return lines.join('\n')"

if block0.count(bad) != 1:
    raise SystemExit(f"BAD_NEWLINE_ANCHOR_COUNT:{block0.count(bad)}")

BACKUP.mkdir(parents=True, exist_ok=True)
shutil.copy2(TARGET, BACKUP / TARGET.name)
log(f"BACKUP={BACKUP / TARGET.name}")

try:
    block = block0.replace(bad, good, 1)
    block = block.replace(
        "function renderVraIssueContract(raw: unknown): string {",
        "function renderVraIssueContract(raw: unknown): string {\n"
        f"  // {MARKER}: render real line breaks, not literal backslash-n text.",
        1
    )
    source = source0[:start] + block + source0[end:]
    write(TARGET, source)

    now = read(TARGET)
    fixed_block = now[start:now.find("async function evidencePayloadWithActiveContract", start)]
    checks = {
        "MARKER": MARKER in fixed_block,
        "BAD_LITERAL_NEWLINE_RETIRED": bad not in fixed_block,
        "REAL_NEWLINE_JOIN_PRESENT": good in fixed_block,
        "EVIDENCE_CONTRACT_PRESERVED": "renderEvidenceReadContract" in now,
        "VRA_CONTRACT_PRESERVED": "vertex.vra.issue/1" in now,
        "ROUNDTRIP_PACKET_PRESERVED": "Promise.all([" in now,
        "FAIL_OPEN_PRESERVED": "contract assistance must never block Evidence" in now,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    if run_npm(["run","typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run_npm(["run","build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("EVIDENCE_ROUTING_CHANGE=ZERO")
    log("ACK_CHANGE=ZERO")
    log("REGISTRY_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("VRA_CONTRACT_NEWLINE_REPAIR_000041V2=PASS")

except Exception:
    write(TARGET, source0)
    log("TRANSACTION_ROLLBACK=RESTORED")
    raise
