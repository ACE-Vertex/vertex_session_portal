from pathlib import Path
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
REGISTRY = PORTAL / "src/main/shell/vxs/vxs-command-registry.ts"
DISCOVERY = PORTAL / "src/main/shell/vxs/vxs-capability-discovery.ts"
FOUNDATION = PORTAL / "src/main/shell/vxs/vxs-autonomy-foundation-capabilities.ts"
ORCH = PORTAL / "src/main/shell/vxs/vxs-orchestration-capabilities.ts"
PREPARE = PORTAL / "src/main/shell/vxs/vxs-autonomous-preparation-capabilities.ts"
CONTEXT = PORTAL / "src/main/shell/vxs/vxs-agent-context-capabilities.ts"
DECISION = PORTAL / "src/main/shell/vxs/vxs-agent-decision-capabilities.ts"

failures = []

def ck(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

for name, p in (
    ("REGISTRY", REGISTRY),
    ("DISCOVERY", DISCOVERY),
    ("FOUNDATION", FOUNDATION),
    ("ORCH", ORCH),
    ("PREPARE", PREPARE),
    ("CONTEXT", CONTEXT),
    ("DECISION", DECISION),
):
    ck(name + "_PRESENT", p.is_file())

rt = REGISTRY.read_text(encoding="utf-8") if REGISTRY.is_file() else ""
dt = DISCOVERY.read_text(encoding="utf-8") if DISCOVERY.is_file() else ""
ft = FOUNDATION.read_text(encoding="utf-8") if FOUNDATION.is_file() else ""
ot = ORCH.read_text(encoding="utf-8") if ORCH.is_file() else ""
pt = PREPARE.read_text(encoding="utf-8") if PREPARE.is_file() else ""
ct = CONTEXT.read_text(encoding="utf-8") if CONTEXT.is_file() else ""
at = DECISION.read_text(encoding="utf-8") if DECISION.is_file() else ""

ck("REGISTRY_MARKER", "VXS_AUTONOMOUS_PREPARATION_LOOP_000026" in rt)
ck("DISCOVERY_MARKER", "VXS_AUTONOMOUS_PREPARATION_LOOP_000026" in dt)
ck("FOUNDATION_MARKER", "VXS_AUTONOMOUS_PREPARATION_LOOP_000026" in ft)
ck("ORCH_MARKER", "VXS_AUTONOMOUS_PREPARATION_LOOP_000026" in ot)
ck("PREPARE_MARKER", "VXS_AUTONOMOUS_PREPARATION_LOOP_000026" in pt)

ck("FOUNDATION_SELFTEST_EXPORT", "export function runVxsSelfTest" in ft)
ck("FOUNDATION_POLICY_EXPORT", "export function buildVxsAutonomyPolicy" in ft)
ck("ORCH_PLAN_EXPORT", "export function createVxsVerificationPlan" in ot)
ck("ORCH_CHAIN_EXPORT", "export function chainVxsVerificationCommands" in ot)

ck("PREPARE_REGISTERED", "createVxsAutonomousPreparationCommands(() => COMMANDS)" in rt)
ck("PREPARE_EXECUTE_LOCAL", "'prepare'" in dt)
ck("PREPARE_POLICY_ALLOWLIST", "'prepare'" in ft)

for token in (
    "vxs prepare",
    "vxs prepare --plan",
    "vxs prepare --json",
):
    ck("HELP_" + token.replace(" ", "_").replace("-", "_").upper(), token in rt)

for token in (
    "vxs-preparation-plan/1",
    "vxs-approval-point/1",
    "vxs-autonomous-preparation/1",
    "AUTONOMOUS_PREPARATION_SAFE_VERIFY",
    "PASS_IF_PACKET_EMITTED",
    "READY_FOR_HUMAN_REVIEW",
    "human_gate_bypass: false",
    "automatic_vra_dispatch: false",
    "arbitrary_run_auto_execution: false",
    "workstation_lane_allocation_authority: 'WORKSTATION'",
    "observation_authoritative: false",
    "No approval point was emitted.",
):
    ck("PREPARE_" + token.replace(" ", "_").replace("'", "").replace(":", "_").replace("/", "_").replace("-", "_").replace(".", "_").upper(), token in pt)

ck("CONTEXT_REUSED", "buildVxsAgentContextSnapshot" in pt and "buildVxsAgentContextSnapshot" in ct)
ck("DECISION_REUSED", "assessVxsReadiness" in pt and "recommendVxsNextCommands" in pt and "assessVxsReadiness" in at)
ck("SELFTEST_REUSED", "runVxsSelfTest" in pt)
ck("POLICY_REUSED", "buildVxsAutonomyPolicy" in pt)
ck("CHANGED_VERIFY_REUSED", "createVxsVerificationPlan" in pt)
ck("FAIL_CLOSED_SELFTEST", "VXS self-test failed" in pt)
ck("FAIL_CLOSED_POLICY", "Autonomy policy does not permit autonomous safe preparation." in pt)
# Do not ban the generic word "dispatch": TypeScript types such as
# VxsCommandDispatchResult legitimately contain it. Check concrete VRA
# dispatch/invocation surfaces instead.
lower_pt = pt.lower()
ck("NO_VRA_DISPATCH_COMMAND", "vxs vra dispatch" not in lower_pt and "vra dispatch " not in lower_pt)
ck("NO_VRA_DISPATCH_FUNCTION_CALL",
   ".dispatchvra(" not in lower_pt and
   "dispatchvra(" not in lower_pt and
   "dispatch_vra(" not in lower_pt)
ck("AUTO_VRA_DISPATCH_FALSE", "automatic_vra_dispatch: false" in pt)
ck("DISPATCH_RESULT_TYPE_ALLOWED", "VxsCommandDispatchResult" in pt)
ck("NO_HTTP_POST", "POST" not in pt)
ck("NO_WRITE_FILE", "writeFile" not in pt)
ck("NO_APPEND_FILE", "appendFile" not in pt)
ck("NO_UNLINK", "unlink" not in pt)
ck("NO_TASKKILL", "taskkill" not in pt.lower())
ck("NO_STOP_PROCESS", "stop-process" not in pt.lower())
ck("000025_PRESERVED", "VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025" in ft)
ck("000024_PRESERVED", "VXS_CAPABILITY_DISCOVERY_PACK_000024" in dt)
ck("000018_PRESERVED", "VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018" in ot)

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

print("VXS_AUTONOMOUS_PREPARATION_LOOP_000026=PASS")
raise SystemExit(0)
