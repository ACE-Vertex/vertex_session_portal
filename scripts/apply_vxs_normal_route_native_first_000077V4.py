from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-command-registry.ts"
SERVICE = ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts"
NATIVE_PROVIDER = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-native-organ-provider.ts"
RESOLVER = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-provider-resolver.ts"
NATIVE_CAPS = ROOT / "src" / "main" / "shell" / "vxs" / "vxs-native-capabilities.ts"
DESCRIPTOR = ROOT / "runtime" / "vxs" / "native" / "providers" / "vxs-native-observer.json"


def fail(stage: str, code: int, extra: str = "") -> int:
    print("VXS_NORMAL_ROUTE=FAIL")
    print("STAGE=" + stage)
    if extra:
        print(extra)
    return code


def replace_once(text: str, old: str, new: str, stage: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{stage}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def run(args: list[str], timeout: int = 240) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=timeout,
    )


for path in (REGISTRY, SERVICE, NATIVE_PROVIDER, RESOLVER, NATIVE_CAPS, DESCRIPTOR):
    if not path.is_file():
        raise SystemExit(fail("FILE_LOOKUP", 20, "MISSING=" + str(path)))

registry = REGISTRY.read_text(encoding="utf-8-sig")
service = SERVICE.read_text(encoding="utf-8-sig")
provider = NATIVE_PROVIDER.read_text(encoding="utf-8-sig")
resolver = RESOLVER.read_text(encoding="utf-8-sig")

if "export interface VxsProviderRequest" not in registry:
    registry = replace_once(
        registry,
        """export interface VxsExecutionCommandResult {
  kind: 'execute'
  executionCommand: string
  executionCwd: string
  capability: string
  routeSummary: string
}""",
        """export interface VxsProviderRequest {
  resource: string
  action: string
  target?: string
  authority: 'AUTO_SAFE' | 'HUMAN_APPLY'
}

export interface VxsExecutionCommandResult {
  kind: 'execute'
  executionCommand: string
  executionCwd: string
  capability: string
  routeSummary: string
  providerRequest?: VxsProviderRequest
}""",
        "REGISTRY_RESULT_CONTRACT",
    )

native_import = "import { createVxsNativeCommands } from './vxs-native-capabilities'"
if native_import not in registry:
    anchor = "import { createVxsDevelopmentCommands } from './vxs-dev-capabilities'"
    registry = replace_once(
        registry,
        anchor,
        anchor + "\n" + native_import,
        "REGISTRY_NATIVE_IMPORT",
    )

if "...createVxsNativeCommands()," not in registry:
    anchor = "  ...createVxsDevelopmentCommands(),"
    registry = replace_once(
        registry,
        anchor,
        anchor + "\n  ...createVxsNativeCommands(),",
        "REGISTRY_NATIVE_COMMANDS",
    )

if "plan(request: VxsNativeCapabilityRequest)" not in provider:
    anchor = """  execute(
    request: VxsNativeCapabilityRequest,
  ): Promise<VxsNativeExecutionResult> {"""
    insertion = """  plan(request: VxsNativeCapabilityRequest): {
    providerId: string
    program: string
    args: string[]
  } | null {
    const probe = this.probe(request)
    if (!probe.available || !probe.binaryPath || !probe.descriptor) {
      return null
    }

    const args = mapInvocation(request)
    if (!args) {
      return null
    }

    return {
      providerId: probe.descriptor.provider_id,
      program: probe.binaryPath,
      args,
    }
  }

"""
    provider = replace_once(
        provider,
        anchor,
        insertion + anchor,
        "NATIVE_PROVIDER_PLAN",
    )

if "export function planVxsProviderExecution" not in resolver:
    resolver += "\nexport interface VxsProviderExecutionPlan {\n  route: 'NATIVE' | 'POWERSHELL'\n  program: string\n  args: string[]\n  providerId: string\n  reason: string\n}\n\nexport function planVxsProviderExecution(\n  projectRoot: string,\n  request: VxsNativeCapabilityRequest,\n  powerShellProgram: string,\n  powerShellCommand: string,\n): VxsProviderExecutionPlan {\n  if (request.authority !== 'AUTO_SAFE') {\n    throw new Error('HUMAN_APPLY_REQUIRED')\n  }\n\n  const nativeProvider = new VxsNativeOrganProvider(projectRoot)\n  const nativePlan = nativeProvider.plan(request)\n\n  if (nativePlan) {\n    return {\n      route: 'NATIVE',\n      program: nativePlan.program,\n      args: nativePlan.args,\n      providerId: nativePlan.providerId,\n      reason: 'NATIVE_PROVIDER_AVAILABLE',\n    }\n  }\n\n  return {\n    route: 'POWERSHELL',\n    program: powerShellProgram,\n    args: ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', powerShellCommand],\n    providerId: 'powershell',\n    reason: 'NATIVE_PROVIDER_UNAVAILABLE',\n  }\n}\n"

resolver_import = "import { planVxsProviderExecution } from './vxs/vxs-provider-resolver'"
if resolver_import not in service:
    anchor = "import { executeVxsCommand } from './vxs/vxs-command-registry'"
    service = replace_once(
        service,
        anchor,
        anchor + "\n" + resolver_import,
        "SERVICE_RESOLVER_IMPORT",
    )

old_block = """    const backend = resolveBackend()
    const executionCommand = routedExecution?.executionCommand ?? command
    const executionCwd = routedExecution?.executionCwd ?? cwd
    const executionBackend = routedExecution
      ? `VXS_${routedExecution.capability}`
      : backend
    const commandId = randomUUID()
    const startedAt = Date.now()
"""

new_block = """    const backend = resolveBackend()
    const executionCommand = routedExecution?.executionCommand ?? command
    const executionCwd = routedExecution?.executionCwd ?? cwd
    const providerPlan = routedExecution?.providerRequest
      ? planVxsProviderExecution(
          process.cwd(),
          routedExecution.providerRequest,
          backend,
          executionCommand
        )
      : null
    const executionBackend = providerPlan
      ? `VXS_${providerPlan.route}_${routedExecution?.capability ?? 'CAPABILITY'}`
      : routedExecution
        ? `VXS_${routedExecution.capability}`
        : backend
    const executionProgram = providerPlan?.program ?? backend
    const executionArgs = providerPlan?.args ?? [
      '-NoLogo',
      '-NoProfile',
      '-NonInteractive',
      '-Command',
      executionCommand
    ]
    const commandId = randomUUID()
    const startedAt = Date.now()
"""

if "const providerPlan = routedExecution?.providerRequest" not in service:
    service = replace_once(service, old_block, new_block, "SERVICE_PROVIDER_PLAN")

old_route_display = """          `Adapter: ${routedExecution.routeSummary}`,
          `Execute: ${executionCommand}`,"""
new_route_display = """          `Adapter: ${routedExecution.routeSummary}`,
          `Provider: ${providerPlan?.route ?? 'POWERSHELL'}${providerPlan ? ` (${providerPlan.reason})` : ''}`,
          `Execute: ${providerPlan ? [executionProgram, ...executionArgs].join(' ') : executionCommand}`,"""
if "Provider: ${providerPlan?.route" not in service:
    service = replace_once(
        service,
        old_route_display,
        new_route_display,
        "SERVICE_ROUTE_DISPLAY",
    )

old_spawn = """    const child = spawn(
      backend,
      ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', executionCommand],
      {
        cwd: executionCwd,
        windowsHide: true,
        shell: false,
        stdio: ['pipe', 'pipe', 'pipe']
      }
    )"""
new_spawn = """    const child = spawn(
      executionProgram,
      executionArgs,
      {
        cwd: executionCwd,
        windowsHide: true,
        shell: false,
        stdio: ['pipe', 'pipe', 'pipe']
      }
    )"""
if "      executionProgram,\n      executionArgs," not in service:
    service = replace_once(service, old_spawn, new_spawn, "SERVICE_NATIVE_FIRST_SPAWN")

REGISTRY.write_text(registry, encoding="utf-8")
SERVICE.write_text(service, encoding="utf-8")
NATIVE_PROVIDER.write_text(provider, encoding="utf-8")
RESOLVER.write_text(resolver, encoding="utf-8")

checks = {
    "registry provider request": "providerRequest?: VxsProviderRequest" in registry,
    "registry native commands": "...createVxsNativeCommands()," in registry,
    "provider plan": "plan(request: VxsNativeCapabilityRequest)" in provider,
    "resolver normal plan": "export function planVxsProviderExecution" in resolver,
    "service provider plan": "const providerPlan = routedExecution?.providerRequest" in service,
    "service native spawn": "      executionProgram,\n      executionArgs," in service,
}
bad = [name for name, ok in checks.items() if not ok]
if bad:
    raise SystemExit(fail("STATIC_CONTRACT", 30, "FAILED=" + ";".join(bad)))

descriptor = json.loads(DESCRIPTOR.read_text(encoding="utf-8-sig"))
binary = Path(str((descriptor.get("binary") or {}).get("path") or ""))
if not binary.is_absolute():
    binary = ROOT / binary
if not binary.is_file():
    raise SystemExit(fail("NATIVE_BINARY_LOOKUP", 31, "EXPECTED=" + str(binary)))

native_smoke = run([str(binary), "system"], timeout=30)
if native_smoke.returncode != 0 or '"organ":"system"' not in native_smoke.stdout:
    raise SystemExit(fail("NATIVE_SYSTEM_SMOKE", 40))

npm_cmd = Path(r"C:\Program Files\nodejs\npm.cmd")
npm = str(npm_cmd) if npm_cmd.is_file() else shutil.which("npm")
if not npm:
    raise SystemExit(fail("NPM_LOOKUP", 60))

typecheck = run([npm, "run", "typecheck"])
if typecheck.returncode != 0:
    print("VXS_NORMAL_ROUTE=FAIL")
    print("STAGE=TYPECHECK")
    print("EXIT_CODE=" + str(typecheck.returncode))
    if typecheck.stdout:
        print("STDOUT=" + typecheck.stdout[-12000:].replace("\n", "\\n"))
    if typecheck.stderr:
        print("STDERR=" + typecheck.stderr[-12000:].replace("\n", "\\n"))
    raise SystemExit(61)

build = run([npm, "run", "build"])
if build.returncode != 0:
    print("VXS_NORMAL_ROUTE=FAIL")
    print("STAGE=BUILD")
    print("EXIT_CODE=" + str(build.returncode))
    if build.stdout:
        print("STDOUT=" + build.stdout[-12000:].replace("\n", "\\n"))
    if build.stderr:
        print("STDERR=" + build.stderr[-12000:].replace("\n", "\\n"))
    raise SystemExit(62)

print("VXS_NORMAL_ROUTE=PASS")
print("REGISTRY_PROVIDER_REQUEST=PASS")
print("NATIVE_COMMANDS_REGISTERED=PASS")
print("PROVIDER_PLAN=PASS")
print("RESOLVER_PLAN=PASS")
print("SHELL_SERVICE_NATIVE_FIRST=PASS")
print("NATIVE_SYSTEM_SMOKE=PASS")
print("TYPECHECK=PASS")
print("BUILD=PASS")
print("NORMAL_ROUTE=vxs command registry -> provider request -> resolver -> native/powershell")
print("NATIVE_COMMANDS=vxs system observe; vxs fs exists/meta/list")
print("HUMAN_APPLY_AUTO_EXECUTION=BLOCKED_BY_DESIGN")
raise SystemExit(0)
