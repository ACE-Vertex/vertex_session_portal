from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
DEV = PORTAL / "src/main/shell/vxs/vxs-dev-capabilities.ts"
SERVICE = PORTAL / "src/main/shell/vertex-shell-service.ts"
VERTEX = PORTAL / "src/main/shell/vxs/vxs-vertex-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, p in (
    ("REGISTRY", REGISTRY),
    ("DEV", DEV),
    ("SERVICE", SERVICE),
    ("VERTEX", VERTEX),
):
    ck(name + "_PRESENT", p.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
dt = DEV.read_text(encoding="utf-8") if DEV.is_file() else ""
st = SERVICE.read_text(encoding="utf-8") if SERVICE.is_file() else ""
vt = VERTEX.read_text(encoding="utf-8") if VERTEX.is_file() else ""

ck("PACK_MARKER_REGISTRY", "VXS_CODE_QUALITY_CAPABILITY_PACK_000010" in rt)
ck("PACK_MARKER_DEV", "VXS_CODE_QUALITY_CAPABILITY_PACK_000010" in dt)

for token in (
    "vxs workspace",
    "vxs scripts",
    "vxs check",
    "vxs format --check",
):
    ck("HELP_" + token.replace(" ", "_").replace("-", "_").upper(), token in rt)

for token in (
    "name: 'workspace'",
    "name: 'scripts'",
    "name: 'check'",
    "name: 'format'",
    "cargo check",
    "cargo fmt --all -- --check",
    "python -m ruff check .",
    "python -m ruff format --check .",
    "format:check",
    "typecheck",
):
    ck("DEV_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace("-", "_").replace(".", "_").replace("/", "_").upper(),
       token in dt)

ck("FORMAT_MUTATION_FAIL_CLOSED", "Formatting mutation is not enabled in this pack." in dt)
ck("FORMAT_REQUIRES_CHECK_FLAG", "requested !== '--check'" in dt)

# Preserve previously VERIFIED capability layers.
ck("VERTEX_PACK_PRESERVED", "VXS_VERTEX_CAPABILITY_PACK_000009" in st)
ck("VRA_ALIAS_PRESERVED", "installNativeVraAlias" in st)
ck("VERTEX_COMMANDS_PRESERVED", "createVxsVertexCommands" in rt)
ck("WORKSTATION_LOOPBACK_PRESERVED", "http://127.0.0.1:47832" in vt)
ck("NO_VERTEX_HTTP_POST", "Invoke-RestMethod -Method Post" not in vt)

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

# TypeScript project-level validation; keep npm.cmd inside Python because
# Official VRA Inspector only permits top-level verification program=python.
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

print("VXS_CODE_QUALITY_CAPABILITY_PACK_000010=PASS")
raise SystemExit(0)
