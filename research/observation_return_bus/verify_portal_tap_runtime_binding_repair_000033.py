from pathlib import Path
import re
import subprocess
import sys

root = Path.cwd()
tap = root / "src/main/observability/evidence-return-tap.ts"
compat = root / "src/main/observability/observation-sidecar-compat.ts"

if not tap.is_file():
    print("TAP_MISSING")
    raise SystemExit(10)
if not compat.is_file():
    print("COMPAT_MISSING")
    raise SystemExit(11)

text = tap.read_text(encoding="utf-8", errors="replace")

required = [
    "toObservationSupplement",
    "extractObservationReference",
    "raw.evidence.envelope.evidence.observation_reference",
    "observationStatus: observation.status",
    "observationSupplement: observation.supplement",
    "WORKSTATION_OBSERVATION_ATTACHED",
    "WORKSTATION_OBSERVATION_REJECTED",
]
for marker in required:
    ok = marker in text
    print(f"MARKER_{marker}={ok}")
    if not ok:
        raise SystemExit(20)

method_start = text.find("async observeAndPersist")
method_end = text.find("\n  readByEvidenceId", method_start)
method = text[method_start:method_end if method_end >= 0 else len(text)]

if "observation_reference" not in text:
    raise SystemExit(21)
if len(re.findall(r"\bobservationStatus\s*:", method)) < 2:
    raise SystemExit(22)
if len(re.findall(r"\bobservationSupplement\s*:", method)) < 2:
    raise SystemExit(23)

print("STATIC_RUNTIME_BINDING=PASS")

npm = "npm.cmd"
cp = subprocess.run(
    [npm, "run", "typecheck"],
    cwd=root,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    encoding="utf-8",
    errors="replace",
)
print(cp.stdout[-12000:])
print(f"TYPECHECK_EXIT={cp.returncode}")
if cp.returncode != 0:
    raise SystemExit(30)

print("PORTAL_TAP_RUNTIME_BINDING_REPAIR_000033=PASS")
raise SystemExit(0)
