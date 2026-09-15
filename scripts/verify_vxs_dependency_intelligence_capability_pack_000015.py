from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
DEP = PORTAL / "src/main/shell/vxs/vxs-dependency-intelligence-capabilities.ts"
CHANGE = PORTAL / "src/main/shell/vxs/vxs-change-intelligence-capabilities.ts"
SOURCE = PORTAL / "src/main/shell/vxs/vxs-source-inspection-capabilities.ts"
OBS = PORTAL / "src/main/shell/vxs/vxs-observability-capabilities.ts"
INSPECT = PORTAL / "src/main/shell/vxs/vxs-inspection-capabilities.ts"
DEV = PORTAL / "src/main/shell/vxs/vxs-dev-capabilities.ts"
VERTEX = PORTAL / "src/main/shell/vxs/vxs-vertex-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, p in (
    ("REGISTRY", REGISTRY),
    ("DEP", DEP),
    ("CHANGE", CHANGE),
    ("SOURCE", SOURCE),
    ("OBS", OBS),
    ("INSPECT", INSPECT),
    ("DEV", DEV),
    ("VERTEX", VERTEX),
):
    ck(name + "_PRESENT", p.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
et = DEP.read_text(encoding="utf-8") if DEP.is_file() else ""
ct = CHANGE.read_text(encoding="utf-8") if CHANGE.is_file() else ""
st = SOURCE.read_text(encoding="utf-8") if SOURCE.is_file() else ""
ot = OBS.read_text(encoding="utf-8") if OBS.is_file() else ""
it = INSPECT.read_text(encoding="utf-8") if INSPECT.is_file() else ""
dt = DEV.read_text(encoding="utf-8") if DEV.is_file() else ""
vt = VERTEX.read_text(encoding="utf-8") if VERTEX.is_file() else ""

ck("REGISTRY_MARKER", "VXS_DEPENDENCY_INTELLIGENCE_CAPABILITY_PACK_000015" in rt)
ck("DEP_MARKER", "VXS_DEPENDENCY_INTELLIGENCE_CAPABILITY_PACK_000015" in et)
ck("MODULE_IMPORT", "createVxsDependencyIntelligenceCommands" in rt)

for token in (
    "vxs imports <path>",
    "vxs dependents <path>",
    "vxs impact <path>",
):
    ck("HELP_" + token.replace(" ", "_").replace("<", "").replace(">", "").replace("-", "_").upper(), token in rt)

for token in (
    "name: 'imports'",
    "name: 'dependents'",
    "name: 'impact'",
    "extractImports",
    "findDependents",
    "maxFiles = 5000",
    "maxHits = 120",
    "Impact Hint is a bounded static heuristic",
):
    ck("DEP_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("<", "").replace(">", "").replace("-", "_").upper(), token in et)

ck("PATH_ESCAPE_GUARD", "Requested file escapes the detected workspace." in et)
ck("READ_BOUND_2MIB", "2 * 1024 * 1024" in et)
ck("NO_WRITE_FILE", "writeFile" not in et)
ck("NO_APPEND_FILE", "appendFile" not in et)
ck("NO_UNLINK", "unlink" not in et)
ck("NO_RM", "rmSync" not in et)

ck("000014_PRESERVED", "VXS_CHANGE_INTELLIGENCE_CAPABILITY_PACK_000014" in ct)
ck("000013_PRESERVED", "VXS_SOURCE_INSPECTION_CAPABILITY_PACK_000013" in st)
ck("000012_PRESERVED", "VXS_OBSERVABILITY_CAPABILITY_PACK_000012" in ot)
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

print("VXS_DEPENDENCY_INTELLIGENCE_CAPABILITY_PACK_000015=PASS")
raise SystemExit(0)
