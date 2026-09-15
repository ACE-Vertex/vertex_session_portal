from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
INSPECTION = PORTAL / "src/main/shell/vxs/vxs-inspection-capabilities.ts"
DEV = PORTAL / "src/main/shell/vxs/vxs-dev-capabilities.ts"
VERTEX = PORTAL / "src/main/shell/vxs/vxs-vertex-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("INSPECTION", INSPECTION),
    ("DEV", DEV),
    ("VERTEX", VERTEX),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
it = INSPECTION.read_text(encoding="utf-8") if INSPECTION.is_file() else ""
dt = DEV.read_text(encoding="utf-8") if DEV.is_file() else ""
vt = VERTEX.read_text(encoding="utf-8") if VERTEX.is_file() else ""

ck("REGISTRY_MARKER", "VXS_INSPECTION_CAPABILITY_PACK_000011" in rt)
ck("INSPECTION_MARKER", "VXS_INSPECTION_CAPABILITY_PACK_000011" in it)
ck("MODULE_IMPORT", "createVxsInspectionCommands" in rt)

for token in ("vxs env", "vxs which <tool>", "vxs tree [1-4]", "vxs deps"):
    ck("HELP_" + token.replace(" ", "_").replace("<", "").replace(">", "").replace("[", "").replace("]", "").replace("-", "_").upper(), token in rt)

for token in (
    "name: 'env'",
    "name: 'which'",
    "name: 'tree'",
    "name: 'deps'",
    "Sensitive environment variable values are intentionally not displayed.",
    "maxEntries = 300",
    "TREE_SKIP",
    "where.exe",
    "package.json",
):
    ck("INSPECT_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("<", "").replace(">", "").replace("-", "_").upper(), token in it)

ck("TREE_DEPTH_BOUNDED", "depth < 1 || depth > 4" in it)
ck("WHICH_TOOL_VALIDATED", "/^[A-Za-z0-9._+-]+$/" in it)
ck("NO_ENV_SECRET_DUMP", "Object.entries(process.env)" not in it)
ck("000010_PRESERVED", "VXS_CODE_QUALITY_CAPABILITY_PACK_000010" in dt)
ck("000009_PRESERVED", "createVxsVertexCommands" in rt)
ck("WORKSTATION_LOOPBACK_PRESERVED", "http://127.0.0.1:47832" in vt)

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

print("VXS_INSPECTION_CAPABILITY_PACK_000011=PASS")
raise SystemExit(0)
