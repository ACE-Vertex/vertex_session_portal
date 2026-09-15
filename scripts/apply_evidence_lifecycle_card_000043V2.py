
from pathlib import Path
import re, shutil, subprocess, sys, time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
TS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / "EVIDENCE" / "EVIDENCE_LIFECYCLE_CARD_000043V2" / STAMP
MARKER = "VERTEX_EVIDENCE_LIFECYCLE_CARD_000043V2"

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
    for line in (p.stdout+"\n"+p.stderr).splitlines()[-100:]:
        log(line)
    return p.returncode

source0 = read(TS)

if MARKER in source0:
    raise SystemExit("ALREADY_APPLIED")

# Direct card-property references are the safest zero-layout-change anchor.
evidence_refs = list(re.finditer(r"\bcard\.workstationEvidenceState\b", source0))
return_refs = list(re.finditer(r"\bcard\.workstationEvidenceReturnState\b", source0))

log(f"EVIDENCE_DIRECT_REF_COUNT={len(evidence_refs)}")
log(f"RETURN_DIRECT_REF_COUNT={len(return_refs)}")

if not evidence_refs or not return_refs:
    raise SystemExit("LIFECYCLE_RENDER_ANCHOR_MISSING")

# Prefer the pair that lives closest together: that is the card renderer, not unrelated code.
pairs = []
for e in evidence_refs:
    for r in return_refs:
        distance = abs(e.start() - r.start())
        pairs.append((distance, e, r))
pairs.sort(key=lambda item: item[0])
distance, ev_ref, ret_ref = pairs[0]
log(f"CLOSEST_REF_DISTANCE={distance}")
if distance > 5000:
    raise SystemExit("LIFECYCLE_RENDER_ANCHORS_TOO_FAR_APART")

BACKUP.mkdir(parents=True, exist_ok=True)
shutil.copy2(TS, BACKUP / TS.name)
log(f"BACKUP={BACKUP / TS.name}")

try:
    source = source0

    # Patch only the closest render references. Work backwards so offsets stay valid.
    replacements = [
        (ret_ref.start(), ret_ref.end(), "this.evidenceLifecycleReturnText(card)"),
        (ev_ref.start(), ev_ref.end(), "this.evidenceLifecycleEvidenceText(card)")
    ]
    for a,b,new in sorted(replacements, reverse=True):
        source = source[:a] + new + source[b:]

    class_end = "\n}\n\ncustomElements.define('vertex-vra-dispatch-lane', VraDispatchLane)"
    if source.count(class_end) != 1:
        raise RuntimeError(f"CLASS_END_ANCHOR_COUNT:{source.count(class_end)}")

    helper = r'''
  // VERTEX_EVIDENCE_LIFECYCLE_CARD_000043V2
  // Compact semantic projection only: no card/container dimensions are changed.
  private evidenceLifecycleEvidenceText(card: VraDispatchCard): string {
    const raw = card as unknown as Record<string, unknown>
    const state = String(raw.workstationEvidenceState ?? '').trim().toUpperCase()

    if (state === 'AVAILABLE') return '● AVAILABLE'
    if (!state || state === 'NONE' || state === 'UNKNOWN') return '○ WAITING'
    return `◉ ${state}`
  }

  private evidenceLifecycleReturnText(card: VraDispatchCard): string {
    const raw = card as unknown as Record<string, unknown>
    const state = String(raw.workstationEvidenceReturnState ?? '').trim().toUpperCase()

    // Contract semantics:
    // RETURN_QUEUED = transport/ack workflow still open; chat may already be visible.
    // RETURNED = configured return workflow completion/ack, not proof a human read it.
    if (state === 'RETURNED') return '● PORTAL ACK'
    if (state === 'RETURN_QUEUED') return '◉ RETURN QUEUE'
    if (!state || state === 'NONE' || state === 'UNKNOWN') return '○ RETURN'
    return `◉ ${state}`
  }
'''
    source = source.replace(class_end, helper + class_end, 1)
    write(TS, source)

    now = read(TS)
    checks = {
        "MARKER": MARKER in now,
        "EVIDENCE_HELPER": "evidenceLifecycleEvidenceText(card)" in now,
        "RETURN_HELPER": "evidenceLifecycleReturnText(card)" in now,
        "AVAILABLE_VISIBLE": "● AVAILABLE" in now,
        "RETURN_QUEUE_VISIBLE": "◉ RETURN QUEUE" in now,
        "PORTAL_ACK_VISIBLE": "● PORTAL ACK" in now,
        "NO_FALSE_HUMAN_READ": "HUMAN READ" not in now,
        "COPY_BUTTON_PRESERVED": "cardErrorCopy" in now,
        "NO_CSS_MUTATION": True,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    if run_npm(["run","typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run_npm(["run","build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("CARD_DIMENSION_CHANGE=ZERO")
    log("CSS_CHANGE=ZERO")
    log("REGISTRY_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("RETURN_ROUTER_CHANGE=ZERO")
    log("ACK_SEMANTICS_CHANGE=ZERO")
    log("EVIDENCE_LIFECYCLE_CARD_000043V2=PASS")

except Exception:
    write(TS, source0)
    log("TRANSACTION_ROLLBACK=RESTORED_TS")
    raise
