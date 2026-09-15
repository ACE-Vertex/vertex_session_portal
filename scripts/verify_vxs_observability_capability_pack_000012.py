from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
OBS = PORTAL / "src/main/shell/vxs/vxs-observability-capabilities.ts"
INSPECTION = PORTAL / "src/main/shell/vxs/vxs-inspection-capabilities.ts"
DEV = PORTAL / "src/main/shell/vxs/vxs-dev-capabilities.ts"
VERTEX = PORTAL / "src/main/shell/vxs/vxs-vertex-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, p in (
    ("REGISTRY", REGISTRY),
    ("OBS", OBS),
    ("INSPECTION", INSPECTION),
    ("DEV", DEV),
    ("VERTEX", VERTEX),
):
    ck(name + "_PRESENT", p.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
ot = OBS.read_text(encoding="utf-8") if OBS.is_file() else ""
it = INSPECTION.read_text(encoding="utf-8") if INSPECTION.is_file() else ""
dt = DEV.read_text(encoding="utf-8") if DEV.is_file() else ""
vt = VERTEX.read_text(encoding="utf-8") if VERTEX.is_file() else ""

ck("REGISTRY_MARKER", "VXS_OBSERVABILITY_CAPABILITY_PACK_000012" in rt)
ck("OBS_MARKER", "VXS_OBSERVABILITY_CAPABILITY_PACK_000012" in ot)
ck("MODULE_IMPORT", "createVxsObservabilityCommands" in rt)

for token in ("vxs logs", "vxs trace <job-id>"):
    ck("HELP_" + token.replace(" ", "_").replace("<", "").replace(">", "").replace("-", "_").upper(), token in rt)

for token in (
    "name: 'logs'",
    "name: 'trace'",
    "safeReadText",
    "maxBytes = 512 * 1024",
    "runtime\\\\headless\\\\job-registry",
    "JOB_ID_PATTERN",
    "No local trace matches were found.",
):
    ck("OBS_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("<", "").replace(">", "").replace("-", "_").replace("\\", "_").upper(), token in ot)

ck("LOG_LINE_BOUNDS", "count < 10 || count > 300" in ot)
ck("TRACE_HIT_BOUND", "hits.length >= 16" in ot)
ck("NO_WRITE_FILE", "writeFile" not in ot)
ck("NO_APPEND_FILE", "appendFile" not in ot)
ck("NO_UNLINK", "unlink" not in ot)
ck("NO_RM", "rmSync" not in ot)
ck("000011_PRESERVED", "VXS_INSPECTION_CAPABILITY_PACK_000011" in it)
ck("000010_PRESERVED", "VXS_CODE_QUALITY_CAPABILITY_PACK_000010" in dt)
ck("000009_PRESERVED", "http://127.0.0.1:47832" in vt)

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

cp = subprocess.run(
    ["npm.cmd", "run", "typecheck"],
    cwd=PORTAL,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=180,
)
print("TYPECHECK_EXIT=" + str(cp.returncode))
if cp.stdout:
    print("TYPECHECK_STDOUT_TAIL=" + " | ".join(cp.stdout.splitlines()[-20:]))
if cp.stderr:
    print("TYPECHECK_STDERR_TAIL=" + " | ".join(cp.stderr.splitlines()[-20:]))

if cp.returncode != 0:
    raise SystemExit(cp.returncode)

print("VXS_OBSERVABILITY_CAPABILITY_PACK_000012=PASS")
raise SystemExit(0)
