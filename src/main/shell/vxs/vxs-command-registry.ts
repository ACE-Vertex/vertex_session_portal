// VXS_POWERSHELL_ENGINE_PROVIDER_000067V3
// VXS_AUTO_GIT_PUBLISH_000065V3
// VXS_AUTONOMOUS_PREPARATION_LOOP_000026
// VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025
// VXS_CAPABILITY_DISCOVERY_PACK_000024
// VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023
// VXS_AGENT_DECISION_CAPABILITY_PACK_000022
// VXS_AGENT_CONTEXT_CAPABILITY_PACK_000021
// VXS_JOB_INTELLIGENCE_CAPABILITY_PACK_000020
// VXS_FAILURE_INTELLIGENCE_CAPABILITY_PACK_000019
// VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018
// VXS_ORCHESTRATION_CAPABILITY_PACK_000017
// VXS_RUNTIME_DIAGNOSTICS_CAPABILITY_PACK_000016
// VXS_DEPENDENCY_INTELLIGENCE_CAPABILITY_PACK_000015
// VXS_CHANGE_INTELLIGENCE_CAPABILITY_PACK_000014
// VXS_SOURCE_INSPECTION_CAPABILITY_PACK_000013
// VXS_OBSERVABILITY_CAPABILITY_PACK_000012
// VXS_INSPECTION_CAPABILITY_PACK_000011
// VXS_CODE_QUALITY_CAPABILITY_PACK_000010
import { spawnSync } from 'node:child_process'
import * as fs from 'node:fs'
import {
  detectVxsWorkspace,
  type VxsWorkspaceInfo
} from './vxs-workspace-detector'
import { createVxsDevelopmentCommands } from './vxs-dev-capabilities'
import { createVxsNativeCommands } from './vxs-native-capabilities'
import { createVxsVertexCommands } from './vxs-vertex-capabilities'
import { createVxsInspectionCommands } from './vxs-inspection-capabilities'
import { createVxsObservabilityCommands } from './vxs-observability-capabilities'
import { createVxsSourceInspectionCommands } from './vxs-source-inspection-capabilities'
import { createVxsChangeIntelligenceCommands } from './vxs-change-intelligence-capabilities'
import { createVxsDependencyIntelligenceCommands } from './vxs-dependency-intelligence-capabilities'
import { createVxsRuntimeDiagnosticsCommands } from './vxs-runtime-diagnostics-capabilities'
import { createVxsOrchestrationCommands } from './vxs-orchestration-capabilities'
import { createVxsFailureIntelligenceCommands } from './vxs-failure-intelligence-capabilities'
import { createVxsJobIntelligenceCommands } from './vxs-job-intelligence-capabilities'
import { createVxsAgentContextCommands } from './vxs-agent-context-capabilities'
import { createVxsAgentDecisionCommands } from './vxs-agent-decision-capabilities'
import { createVxsAgentHandoffCommands } from './vxs-agent-handoff-capabilities'
import { createVxsCapabilityDiscoveryCommands } from './vxs-capability-discovery'
import { createVxsAutonomyFoundationCommands } from './vxs-autonomy-foundation-capabilities'
import { createVxsAutonomousPreparationCommands } from './vxs-autonomous-preparation-capabilities'
import { createVxsPowerShellCommands } from './vxs-powershell-capabilities'

export interface VxsCommandContext {
  cwd: string
  version: string
  canonicalName: string
  compatibilityBackend: string
}

export interface VxsImmediateCommandResult {
  kind: 'immediate'
  output: string
  exitCode: number
  stream: 'system' | 'stderr'
}

export interface VxsProviderRequest {
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
}

export type VxsCommandDispatchResult =
  | VxsImmediateCommandResult
  | VxsExecutionCommandResult

export interface VxsCommandDefinition {
  name: string
  aliases: string[]
  usage: string
  summary: string
  execute: (
    args: string[],
    context: VxsCommandContext
  ) => VxsCommandDispatchResult
}

function line(value = ''): string {
  return `${value}\n`
}

function executableName(base: string): string {
  if (process.platform !== 'win32') return base
  if (base === 'npm') return 'npm.cmd'
  if (base === 'pnpm') return 'pnpm.cmd'
  if (base === 'yarn') return 'yarn.cmd'
  return base.endsWith('.exe') || base.endsWith('.cmd')
    ? base
    : `${base}.exe`
}

function commandAvailable(base: string): boolean {
  const program = process.platform === 'win32' ? 'where.exe' : 'which'
  const name = executableName(base)

  try {
    const result = spawnSync(
      program,
      [name],
      {
        windowsHide: true,
        shell: false,
        stdio: 'ignore',
        timeout: 2_000
      }
    )
    return result.status === 0
  } catch {
    return false
  }
}

function workspaceLabel(workspace: VxsWorkspaceInfo): string {
  const pieces: string[] = []

  if (workspace.packageName) {
    pieces.push(
      workspace.packageVersion
        ? `${workspace.packageName}@${workspace.packageVersion}`
        : workspace.packageName
    )
  }

  if (workspace.frameworks.length > 0) {
    pieces.push(workspace.frameworks.join(' + '))
  }

  if (pieces.length === 0) {
    pieces.push(
      workspace.kind === 'directory'
        ? 'Generic directory'
        : workspace.kind.toUpperCase()
    )
  }

  return pieces.join(' · ')
}

function helpCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const rows = [
    'VXS COMMAND REGISTRY',
    `${context.canonicalName} ${context.version}`,
    '',
    'Core commands:',
    '  vxs --version          Show VXS identity',
    '  vxs --help             Show this command registry',
    '  vxs help               Alias for --help',
    '  vxs status             Inspect current workspace',
    '  vxs doctor             Diagnose current development environment',
    '',
    'Development commands:',
    '  vxs workspace          Show detected workspace details',
    '  vxs scripts            List detected package scripts',
    '  vxs check              Auto-route non-mutating code checks',
    '  vxs format --check     Auto-route formatting verification',
    '  vxs build              Auto-route workspace build',
    '  vxs test               Auto-route workspace tests',
    '  vxs lint               Auto-route workspace lint',
    '  vxs run <script>       Run a detected package script',
    '  vxs git help           Show Git observe + AUTO-gated mutation commands',
    '',
    'Inspection commands:',
    '  vxs env                Safe environment summary',
    '  vxs which <tool>       Resolve a tool path',
    '  vxs tree [1-4]         Bounded workspace tree',
    '  vxs deps               Inspect local package dependencies',
    '',
    'Observability commands:',
    '  vxs logs [scope] [n]   Tail bounded Portal/Workstation logs',
    '  vxs trace <job-id>     Find local traces for a Workstation Job',
    '',
    'Source inspection commands:',
    '  vxs find <text> [path] Search workspace source text',
    '  vxs inspect <path>     Read bounded source line ranges',
    '  vxs hash <path>        Compute SHA256 for a workspace file',
    '  vxs stat <path>        Show workspace path metadata',
    '',
    'Change intelligence commands:',
    '  vxs changed            Show changed/untracked files',
    '  vxs diffstat           Show staged/worktree diff statistics',
    '  vxs refs <symbol>      Find bounded source references',
    '  vxs todo [path]        Find TODO/FIXME/HACK/XXX markers',
    '',
    'Dependency intelligence commands:',
    '  vxs imports <path>     List detected imports',
    '  vxs dependents <path>  Find bounded direct dependents',
    '  vxs impact <path>      Summarize static change impact',
    '',
    'Runtime diagnostics commands:',
    '  vxs runtime            Inspect local VXS/Portal/Workstation runtime',
    '  vxs port <number>      Inspect TCP ownership for a port',
    '  vxs process <name|pid> Inspect Windows process rows',
    '  vxs versions           Show runtime/tool versions',
    '',
    'Orchestration commands:',
    '  vxs preflight          Summarize readiness without execution',
    '  vxs verify quick       Run fail-fast checks/tests',
    '  vxs verify full        Run checks/tests plus build validation',
    '  vxs verify changed     Verify only ecosystems touched by Git changes',
    '  vxs verify-plan [mode] Preview quick/full/changed verification plan',
    '',
    'Failure intelligence commands:',
    '  vxs triage <job-id>    Classify Portal/Workstation job failure state',
    '',
    'Job intelligence commands:',
    '  vxs jobs [n]           List recent durable Workstation jobs',
    '  vxs failures [n]       List recent failed/rejected jobs',
    '  vxs timeline <job-id>  Show durable Job lifecycle timestamps',
    '',
    'Agent context commands:',
    '  vxs context            Create a safe bounded development snapshot',
    '  vxs context --json     Emit machine-readable agent context',
    '',
    'Agent decision commands:',
    '  vxs readiness          Assess current development readiness',
    '  vxs readiness --json   Emit machine-readable readiness',
    '  vxs recommend          Recommend next VXS commands',
    '  vxs recommend --json   Emit machine-readable recommendations',
    '',
    'Agent handoff commands:',
    '  vxs handoff            Bundle context/readiness/recommendations',
    '  vxs handoff --json     Emit machine-readable agent handoff packet',
    '',
    'Capability discovery commands:',
    '  vxs capabilities       List VXS capabilities and safety classes',
    '  vxs capabilities --json Emit machine-readable capability catalog',
    '  vxs describe <command> Describe one VXS command',
    '  vxs describe <command> --json Emit machine-readable capability detail',
    '',
    'Autonomous preparation foundation:',
    '  vxs selftest           Validate VXS registry/authority contracts',
    '  vxs selftest --json    Emit machine-readable self-test result',
    '  vxs policy             Show autonomous preparation policy',
    '  vxs policy --json      Emit machine-readable autonomy policy',
    '',
    'Autonomous development preparation:',
    '  vxs prepare            Self-test, plan, safe-verify, then emit approval point',
    '  vxs prepare --plan     Preview autonomous preparation without execution',
    '  vxs prepare --json     Emit machine-readable preparation plan',
    '',
    'PowerShell engine provider:',
    '  vxs ps engine          Inspect the embedded PowerShell engine/runtime',
    '  vxs ps commands [pat]  Discover PowerShell commands through engine metadata',
    '  vxs ps describe <cmd>  Describe CommandMetadata/parameters/safety signals',
    '  vxs ps providers       Inspect PowerShell Providers and PSDrives',
    '  vxs ps modules [pat]   Inspect available PowerShell modules',
    '  vxs ps plan <script>   Parse AST and classify a PowerShell script without execution',
    '  vxs ps invoke <script> Execute only when engine analysis classifies SAFE_READ',
    '',
    'Vertex commands:',
    '  vxs ray [pattern]      Read-only workspace Ray',
    '  vxs vra ...            Alias to existing Native VRA commands',
    '  vxs workstation ...    Read Workstation control-plane state',
    '  vxs evidence <job-id>  Read Workstation Evidence',
    '',
    'Compatibility:',
    `  Non-VXS commands continue to ${context.compatibilityBackend}.`,
    '',
    'Foundation:',
    '  Command Registry       READY',
    '  Workspace Detector     READY',
    '  Capability adapters    EXTENSIBLE',
    ''
  ]

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function statusCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  const rows = [
    'VXS STATUS',
    `Version: ${context.version}`,
    `CWD: ${workspace.cwd}`,
    `Workspace Root: ${workspace.root}`,
    `Workspace Type: ${workspace.kind}`,
    `Workspace: ${workspaceLabel(workspace)}`,
    `Package Manager: ${workspace.packageManager ?? 'not detected'}`,
    `Frameworks: ${workspace.frameworks.length > 0 ? workspace.frameworks.join(', ') : 'not detected'}`,
    `Git: ${workspace.git ? 'detected' : 'not detected'}`,
    `Markers: ${workspace.markers.length > 0 ? workspace.markers.join(', ') : 'none'}`,
    `Scripts: ${workspace.scripts.length > 0 ? workspace.scripts.join(', ') : 'none detected'}`,
    `Backend: ${context.compatibilityBackend} (compatibility)`,
    'Command Registry: READY',
    'Workspace Detector: READY',
    ''
  ]

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

interface DoctorCheck {
  level: 'PASS' | 'WARN' | 'FAIL'
  name: string
  detail: string
}

function doctorCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)
  const checks: DoctorCheck[] = []

  checks.push({
    level: fs.existsSync(workspace.cwd) ? 'PASS' : 'FAIL',
    name: 'CWD',
    detail: workspace.cwd
  })

  checks.push({
    level: 'PASS',
    name: 'Node runtime',
    detail: process.versions.node
  })

  checks.push({
    level: commandAvailable('pwsh') ? 'PASS' : 'FAIL',
    name: 'PowerShell',
    detail: commandAvailable('pwsh') ? 'pwsh.exe available' : 'pwsh.exe not found'
  })

  checks.push({
    level: commandAvailable('git') ? 'PASS' : 'WARN',
    name: 'Git',
    detail: commandAvailable('git') ? 'git available' : 'git not found'
  })

  if (workspace.packageManager) {
    const available = commandAvailable(workspace.packageManager)
    checks.push({
      level: available ? 'PASS' : 'FAIL',
      name: `Package manager (${workspace.packageManager})`,
      detail: available
        ? `${workspace.packageManager} available`
        : `${workspace.packageManager} not found`
    })
  }

  if (workspace.kind === 'rust' || workspace.kind === 'mixed') {
    const available = commandAvailable('cargo')
    checks.push({
      level: available ? 'PASS' : 'FAIL',
      name: 'Rust / Cargo',
      detail: available ? 'cargo available' : 'cargo not found'
    })
  }

  if (workspace.kind === 'python' || workspace.kind === 'mixed') {
    const pythonAvailable =
      commandAvailable('python') || commandAvailable('py')
    checks.push({
      level: pythonAvailable ? 'PASS' : 'FAIL',
      name: 'Python',
      detail: pythonAvailable
        ? 'Python launcher available'
        : 'python / py not found'
    })
  }

  if (workspace.kind === 'directory') {
    checks.push({
      level: 'WARN',
      name: 'Workspace markers',
      detail: 'No package.json / Cargo.toml / Python marker detected'
    })
  } else {
    checks.push({
      level: 'PASS',
      name: 'Workspace detection',
      detail: workspaceLabel(workspace)
    })
  }

  const pass = checks.filter(check => check.level === 'PASS').length
  const warn = checks.filter(check => check.level === 'WARN').length
  const fail = checks.filter(check => check.level === 'FAIL').length

  const rows = [
    'VXS DOCTOR',
    `Workspace Root: ${workspace.root}`,
    '',
    ...checks.map(
      check => `[${check.level}] ${check.name}: ${check.detail}`
    ),
    '',
    `Summary: PASS=${pass} WARN=${warn} FAIL=${fail}`,
    fail === 0 ? 'VXS DOCTOR RESULT: PASS' : 'VXS DOCTOR RESULT: FAILED',
    ''
  ]

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: fail === 0 ? 0 : 1,
    stream: 'system'
  }
}

const COMMANDS: VxsCommandDefinition[] = [
  {
    name: 'help',
    aliases: ['--help', '-h'],
    usage: 'vxs --help',
    summary: 'Show VXS commands',
    execute: helpCommand
  },
  {
    name: 'status',
    aliases: [],
    usage: 'vxs status',
    summary: 'Inspect the current workspace',
    execute: statusCommand
  },
  {
    name: 'doctor',
    aliases: [],
    usage: 'vxs doctor',
    summary: 'Diagnose the development environment',
    execute: doctorCommand
  },
  ...createVxsDevelopmentCommands(),
  ...createVxsNativeCommands(),
  ...createVxsInspectionCommands(),
  ...createVxsObservabilityCommands(),
  ...createVxsSourceInspectionCommands(),
  ...createVxsChangeIntelligenceCommands(),
  ...createVxsDependencyIntelligenceCommands(),
  ...createVxsRuntimeDiagnosticsCommands(),
  ...createVxsOrchestrationCommands(),
  ...createVxsFailureIntelligenceCommands(),
  ...createVxsJobIntelligenceCommands(),
  ...createVxsAgentContextCommands(),
  ...createVxsAgentDecisionCommands(),
  ...createVxsAgentHandoffCommands(),
  ...createVxsPowerShellCommands(),
  ...createVxsVertexCommands(),
  ...createVxsCapabilityDiscoveryCommands(() => COMMANDS),
  ...createVxsAutonomyFoundationCommands(() => COMMANDS),
  ...createVxsAutonomousPreparationCommands(() => COMMANDS)
]

function resolveCommand(token: string): VxsCommandDefinition | null {
  const normalized = token.toLowerCase()
  return COMMANDS.find(
    command =>
      command.name === normalized ||
      command.aliases.includes(normalized)
  ) ?? null
}

export function executeVxsCommand(
  rawCommand: string,
  context: VxsCommandContext
): VxsCommandDispatchResult | null {
  const trimmed = rawCommand.trim()

  if (!/^vxs(?:\s|$)/i.test(trimmed)) return null

  const body = trimmed.replace(/^vxs\b/i, '').trim()
  const tokens = body ? body.split(/\s+/) : ['help']
  const commandToken = tokens[0] ?? 'help'
  const args = tokens.slice(1)

  if (commandToken === '--version') {
    return null
  }

  const command = resolveCommand(commandToken)

  if (!command) {
    return {
      kind: 'immediate',
      output: [
        `ERROR: Unknown VXS command '${commandToken}'.`,
        'Run: vxs --help',
        ''
      ].map(line).join(''),
      exitCode: 2,
      stream: 'stderr'
    }
  }

  return command.execute(args, context)
}

export function vxsCommandRegistrySummary(): string[] {
  return COMMANDS.map(command => `${command.usage} — ${command.summary}`)
}
