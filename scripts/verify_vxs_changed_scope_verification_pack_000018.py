from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
ORCH = PORTAL / "src/main/shell/vxs/vxs-orchestration-capabilities.ts"
RUNTIME = PORTAL / "src/main/shell/vxs/vxs-runtime-diagnostics-capabilities.ts"
DEP = PORTAL / "src/main/shell/vxs/vxs-dependency-intelligence-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, path in (
    ("REGISTRY", REGISTRY),
    ("ORCH", ORCH),
    ("RUNTIME", RUNTIME),
    ("DEP", DEP),
):
    ck(name + "_PRESENT", path.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
ot = ORCH.read_text(encoding="utf-8") if ORCH.is_file() else ""
xt = RUNTIME.read_text(encoding="utf-8") if RUNTIME.is_file() else ""
dt = DEP.read_text(encoding="utf-8") if DEP.is_file() else ""

ck("REGISTRY_MARKER", "VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018" in rt)
ck("ORCH_MARKER", "VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018" in ot)
ck("000017_PRESERVED", "VXS_ORCHESTRATION_CAPABILITY_PACK_000017" in ot)
ck("000016_PRESERVED", "VXS_RUNTIME_DIAGNOSTICS_CAPABILITY_PACK_000016" in xt)
ck("000015_PRESERVED", "VXS_DEPENDENCY_INTELLIGENCE_CAPABILITY_PACK_000015" in dt)

for token in (
    "vxs verify changed",
    "vxs verify-plan [mode]",
):
    ck("HELP_" + token.replace(" ", "_").replace("[", "").replace("]", "").replace("-", "_").upper(), token in rt)

for token in (
    "VERIFY_CHANGED",
    "createVerificationPlan",
    "changedFilesForWorkspace",
    "classifyChangedEcosystems",
    "renderVerificationPlan",
    "name: 'verify-plan'",
    "PLAN_ONLY=YES",
    "Clean working tree; no changed-scope verification required.",
):
    ck("ORCH_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace(".", "_").replace("-", "_").upper(), token in ot)

ck("CHANGED_GIT_READONLY",
   "['status', '--short', '--untracked-files=normal']" in ot)
ck("QUICK_FULL_CHANGED_GUARD",
   "rawMode !== 'changed'" in ot)
ck("CHANGED_NODE_CLASSIFICATION",
   "ecosystems.add('node')" in ot)
ck("CHANGED_RUST_CLASSIFICATION",
   "ecosystems.add('rust')" in ot)
ck("CHANGED_PYTHON_CLASSIFICATION",
   "ecosystems.add('python')" in ot)
ck("CONSERVATIVE_FALLBACK",
   "Conservative fallback" in ot)
ck("NO_GIT_COMMIT", "git commit" not in ot.lower())
ck("NO_GIT_PUSH", "git push" not in ot.lower())
ck("NO_TASKKILL", "taskkill" not in ot.lower())
ck("NO_STOP_PROCESS", "stop-process" not in ot.lower())

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

print("VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018=PASS")
raise SystemExit(0)
