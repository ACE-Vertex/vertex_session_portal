import type {
  VxsCommandContext,
  VxsCommandDefinition,
  VxsCommandDispatchResult,
  VxsExecutionCommandResult
} from './vxs-command-registry'

function psQuote(value: string): string {
  return `'${value.replace(/'/g, "''")}'`
}

function cleanTarget(args: string[]): string {
  const joined = args.join(' ').trim()
  return joined.replace(/^(['"])(.*)\1$/, '$2')
}

function systemCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const subcommand = (args[0] ?? 'observe').toLowerCase()

  if (subcommand !== 'observe') {
    return {
      kind: 'immediate',
      output: [
        `Unsupported vxs system command '${subcommand}'.`,
        'Usage: vxs system observe'
      ].join('\n'),
      exitCode: 2,
      stream: 'stderr'
    }
  }

  const result: VxsExecutionCommandResult = {
    kind: 'execute',
    executionCommand:
      '$PSVersionTable | Select-Object PSEdition,PSVersion,Platform,OS | ConvertTo-Json -Compress',
    executionCwd: context.cwd,
    capability: 'NATIVE_SYSTEM_OBSERVE',
    routeSummary: 'Native-first Rust SYSTEM observer with PowerShell fallback',
    providerRequest: {
      resource: 'SYSTEM',
      action: 'OBSERVE',
      authority: 'AUTO_SAFE'
    }
  }
  return result
}

function filesystemCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const subcommand = (args[0] ?? '').toLowerCase()
  const target = cleanTarget(args.slice(1))

  if (!['exists', 'meta', 'list'].includes(subcommand) || !target) {
    return {
      kind: 'immediate',
      output: [
        'Usage:',
        '  vxs fs exists <path>',
        '  vxs fs meta <path>',
        '  vxs fs list <path>'
      ].join('\n'),
      exitCode: 2,
      stream: 'stderr'
    }
  }

  const quoted = psQuote(target)

  if (subcommand === 'exists') {
    return {
      kind: 'execute',
      executionCommand: `Test-Path -LiteralPath ${quoted}`,
      executionCwd: context.cwd,
      capability: 'NATIVE_FILESYSTEM_EXISTS',
      routeSummary: 'Native-first Rust FILESYSTEM exists with PowerShell fallback',
      providerRequest: {
        resource: 'FILESYSTEM',
        action: 'TEST',
        target,
        authority: 'AUTO_SAFE'
      }
    }
  }

  if (subcommand === 'meta') {
    return {
      kind: 'execute',
      executionCommand:
        `Get-Item -LiteralPath ${quoted} | ` +
        'Select-Object FullName,Name,Length,Attributes,LastWriteTime | ConvertTo-Json -Compress',
      executionCwd: context.cwd,
      capability: 'NATIVE_FILESYSTEM_METADATA',
      routeSummary: 'Native-first Rust FILESYSTEM metadata with PowerShell fallback',
      providerRequest: {
        resource: 'FILESYSTEM',
        action: 'OBSERVE',
        target,
        authority: 'AUTO_SAFE'
      }
    }
  }

  return {
    kind: 'execute',
    executionCommand:
      `Get-ChildItem -LiteralPath ${quoted} | ` +
      'Select-Object -ExpandProperty Name | ConvertTo-Json -Compress',
    executionCwd: context.cwd,
    capability: 'NATIVE_FILESYSTEM_LIST',
    routeSummary: 'Native-first Rust FILESYSTEM list with PowerShell fallback',
    providerRequest: {
      resource: 'FILESYSTEM',
      action: 'FIND',
      target,
      authority: 'AUTO_SAFE'
    }
  }
}

export function createVxsNativeCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'system',
      aliases: ['sys'],
      usage: 'vxs system observe',
      summary: 'Observe the local system through the Native-first provider route',
      execute: systemCommand
    },
    {
      name: 'fs',
      aliases: ['filesystem'],
      usage: 'vxs fs <exists|meta|list> <path>',
      summary: 'Observe filesystem state through the Native-first provider route',
      execute: filesystemCommand
    }
  ]
}
