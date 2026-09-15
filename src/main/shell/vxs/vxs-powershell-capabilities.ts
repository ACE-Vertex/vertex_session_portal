// VXS_POWERSHELL_ENGINE_PROVIDER_000067V3
import type {
  VxsCommandContext,
  VxsCommandDefinition,
  VxsCommandDispatchResult
} from './vxs-command-registry'
import {
  buildVxsPowerShellEnginePlan,
  type VxsPowerShellEngineAction,
  type VxsPowerShellEngineRequest
} from './vxs-powershell-engine-adapter'

function line(value = ''): string {
  return `${value}\n`
}

function immediateError(
  message: string,
  hints: string[] = []
): VxsCommandDispatchResult {
  return {
    kind: 'immediate',
    output: [
      `ERROR: ${message}`,
      ...hints,
      ''
    ].map(line).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

function helpResult(): VxsCommandDispatchResult {
  return {
    kind: 'immediate',
    output: [
      'VXS POWERSHELL ENGINE PROVIDER',
      '',
      'PowerShell is treated as a structured engine provider, not only as a text shell.',
      '',
      'Commands:',
      '  vxs ps engine',
      '  vxs ps commands [pattern]',
      '  vxs ps describe <command>',
      '  vxs ps providers',
      '  vxs ps modules [pattern]',
      '  vxs ps plan <PowerShell script>',
      '  vxs ps invoke <PowerShell script>',
      '',
      'Safety:',
      '  plan never executes the script.',
      '  invoke executes only SAFE_READ scripts.',
      '  mutation/dynamic/untrusted constructs are recognized and BLOCKED_HUMAN_APPLY.',
      '  Human Gate remains the authority boundary.',
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function engineExecution(
  request: VxsPowerShellEngineRequest,
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const plan = buildVxsPowerShellEnginePlan(request)
  return {
    kind: 'execute',
    executionCommand: plan.executionCommand,
    executionCwd: context.cwd,
    capability: plan.capability,
    routeSummary: plan.routeSummary
  }
}

function psCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const actionToken = (args[0] ?? 'help').toLowerCase()

  if (actionToken === 'help' || actionToken === '--help' || actionToken === '-h') {
    return helpResult()
  }

  const simpleActions: Record<string, VxsPowerShellEngineAction> = {
    engine: 'engine',
    commands: 'commands',
    discover: 'commands',
    describe: 'describe',
    providers: 'providers',
    modules: 'modules',
    plan: 'plan',
    invoke: 'invoke'
  }

  const action = simpleActions[actionToken]
  if (!action) {
    return immediateError(
      `Unknown PowerShell engine action '${actionToken}'.`,
      ['Run: vxs ps help']
    )
  }

  if (action === 'engine' || action === 'providers') {
    return engineExecution({ action }, context)
  }

  if (action === 'commands' || action === 'modules') {
    const pattern = args.slice(1).join(' ').trim() || undefined
    return engineExecution({ action, pattern }, context)
  }

  if (action === 'describe') {
    const command = args.slice(1).join(' ').trim()
    if (!command) {
      return immediateError('PowerShell command name is required.', [
        'Example: vxs ps describe Get-Process'
      ])
    }
    return engineExecution({ action, command }, context)
  }

  const script = args.slice(1).join(' ').trim()
  if (!script) {
    return immediateError('PowerShell script is required.', [
      `Example: vxs ps ${action} Get-Process | Select-Object -First 5`
    ])
  }

  return engineExecution({ action, script }, context)
}

export function createVxsPowerShellCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'powershell',
      aliases: ['ps', 'pwsh'],
      usage: 'vxs ps <engine|commands|describe|providers|modules|plan|invoke> [...]',
      summary: 'Use PowerShell as a structured VXS engine provider with AST/metadata safety analysis',
      execute: psCommand
    }
  ]
}
