from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
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
    ("CHANGE", CHANGE),
    ("SOURCE", SOURCE),
    ("OBS", OBS),
    ("INSPECT", INSPECT),
    ("DEV", DEV),
    ("VERTEX", VERTEX),
):
    ck(name + "_PRESENT", p.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
ct = CHANGE.read_text(encoding="utf-8") if CHANGE.is_file() else ""
st = SOURCE.read_text(encoding="utf-8") if SOURCE.is_file() else ""
ot = OBS.read_text(encoding="utf-8") if OBS.is_file() else ""
it = INSPECT.read_text(encoding="utf-8") if INSPECT.is_file() else ""
dt = DEV.read_text(encoding="utf-8") if DEV.is_file() else ""
vt = VERTEX.read_text(encoding="utf-8") if VERTEX.is_file() else ""

ck("REGISTRY_MARKER", "VXS_CHANGE_INTELLIGENCE_CAPABILITY_PACK_000014" in rt)
ck("CHANGE_MARKER", "VXS_CHANGE_INTELLIGENCE_CAPABILITY_PACK_000014" in ct)
ck("MODULE_IMPORT", "createVxsChangeIntelligenceCommands" in rt)

for token in (
    "vxs changed",
    "vxs diffstat",
    "vxs refs <symbol>",
    "vxs todo [path]",
):
    ck("HELP_" + token.replace(" ", "_").replace("<", "").replace(">", "").replace("[", "").replace("]", "").replace("-", "_").upper(), token in rt)

for token in (
    "name: 'changed'",
    "name: 'diffstat'",
    "name: 'refs'",
    "name: 'todo'",
    "status', '--short'",
    "diff', '--stat'",
    "diff', '--cached', '--stat'",
    "maxFiles = 5000",
    "maxHits = 120",
    "TODO",
    "FIXME",
    "HACK",
    "XXX",
):
    ck("CHANGE_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("<", "").replace(">", "").replace("-", "_").replace(",", "_").upper(), token in ct)

ck("GIT_READONLY_STATUS", "['status', '--short', '--untracked-files=normal']" in ct)
ck("GIT_READONLY_DIFF", "['diff', '--stat']" in ct)
ck("GIT_READONLY_CACHED_DIFF", "['diff', '--cached', '--stat']" in ct)
# Guard only actual Git mutation invocations/arguments.
# Generic words such as `.push(...)` are valid TypeScript and must not trip the verifier.
git_mutation_patterns = (
    "['commit'",
    '["commit"',
    "['push'",
    '["push"',
    "['checkout'",
    '["checkout"',
    "['reset', '--hard'",
    '["reset", "--hard"',
    "['clean', '-f'",
    '["clean", "-f"',
    "git commit",
    "git push",
    "git checkout",
    "git reset --hard",
    "git clean -f",
)
for pattern in git_mutation_patterns:
    ck(
        "FORBID_GIT_MUTATION_" + pattern.replace(" ", "_").replace("-", "_").replace("[", "").replace("]", "").replace("'", "").replace('"', "").replace(",", "_").upper(),
        pattern.lower() not in ct.lower()
    )

ck("NO_WRITE_FILE", "writeFile" not in ct)
ck("NO_APPEND_FILE", "appendFile" not in ct)
ck("NO_UNLINK", "unlink" not in ct)
ck("NO_RM", "rmSync" not in ct)

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

print("VXS_CHANGE_INTELLIGENCE_CAPABILITY_PACK_000014=PASS")
raise SystemExit(0)
