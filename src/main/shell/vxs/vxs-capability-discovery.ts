// VXS_AUTONOMOUS_PREPARATION_LOOP_000026
// VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025
// VXS_CAPABILITY_DISCOVERY_PACK_000024
import type {
  VxsCommandDefinition,
  VxsCommandDispatchResult
} from './vxs-command-registry'

export type SafetyClass = 'OBSERVE' | 'EXECUTE_LOCAL' | 'HUMAN_GATED'

export interface CapabilityDescriptor {
  name: string
  aliases: string[]
  usage: string
  summary: string
  safety_class: SafetyClass
  requires_human_gate: boolean
  automatic_execution: boolean
}

export interface CapabilityCatalog {
  schema: 'vxs-capabilities/1'
  command_count: number
  capabilities: CapabilityDescriptor[]
}

export interface CapabilityDetail {
  schema: 'vxs-capability/1'
  capability: CapabilityDescriptor
}

const EXECUTE_LOCAL = new Set([
  'build',
  'test',
  'lint',
  'run',
  'check',
  'verify',
  'prepare'
])

const HUMAN_GATED = new Set([
  'vra'
])

function classify(command: VxsCommandDefinition): {
  safetyClass: SafetyClass
  requiresHumanGate: boolean
  automaticExecution: boolean
} {
  if (HUMAN_GATED.has(command.name)) {
    return {
      safetyClass: 'HUMAN_GATED',
      requiresHumanGate: true,
      automaticExecution: false
    }
  }

  if (EXECUTE_LOCAL.has(command.name)) {
    return {
      safetyClass: 'EXECUTE_LOCAL',
      requiresHumanGate: false,
      automaticExecution: false
    }
  }

  return {
    safetyClass: 'OBSERVE',
    requiresHumanGate: false,
    automaticExecution: false
  }
}

export function describeVxsCapability(
  command: VxsCommandDefinition
): CapabilityDescriptor {
  const safety = classify(command)

  return {
    name: command.name,
    aliases: [...command.aliases],
    usage: command.usage,
    summary: command.summary,
    safety_class: safety.safetyClass,
    requires_human_gate: safety.requiresHumanGate,
    automatic_execution: safety.automaticExecution
  }
}


export function buildVxsCapabilityCatalog(
  commands: readonly VxsCommandDefinition[]
): CapabilityCatalog {
  const capabilities = commands
    .map(describeVxsCapability)
    .sort((a, b) => a.name.localeCompare(b.name))

  return {
    schema: 'vxs-capabilities/1',
    command_count: capabilities.length,
    capabilities
  }
}

function line(value = ''): string {
  return `${value}\n`
}

function errorResult(message: string, usage: string): VxsCommandDispatchResult {
  return {
    kind: 'immediate',
    output: [
      `ERROR: ${message}`,
      `Usage: ${usage}`,
      ''
    ].map(line).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

export function createVxsCapabilityDiscoveryCommands(
  getCommands: () => readonly VxsCommandDefinition[]
): VxsCommandDefinition[] {
  function capabilitiesCommand(
    args: string[]
  ): VxsCommandDispatchResult {
    const option = (args[0] ?? '').trim()

    if (option && option !== '--json') {
      return errorResult(
        `Unknown option '${option}'.`,
        'vxs capabilities [--json]'
      )
    }

    const catalog = buildVxsCapabilityCatalog(getCommands())
    const capabilities = catalog.capabilities

    if (option === '--json') {
      return {
        kind: 'immediate',
        output: `${JSON.stringify(catalog, null, 2)}\n`,
        exitCode: 0,
        stream: 'system'
      }
    }

    const rows = [
      'VXS CAPABILITIES',
      `Schema: ${catalog.schema}`,
      `Commands: ${catalog.command_count}`,
      ''
    ]

    for (const item of capabilities) {
      rows.push(
        `${item.name} | ${item.safety_class} | ${item.usage}`
      )
      rows.push(`  ${item.summary}`)
    }

    rows.push('')
    rows.push('CAPABILITY_DISCOVERY_EXECUTION=NONE')
    rows.push('')

    return {
      kind: 'immediate',
      output: rows.map(line).join(''),
      exitCode: 0,
      stream: 'system'
    }
  }

  function describeCommand(
    args: string[]
  ): VxsCommandDispatchResult {
    const token = (args[0] ?? '').trim().toLowerCase()
    const option = (args[1] ?? '').trim()

    if (!token) {
      return errorResult(
        'Command name is required.',
        'vxs describe <command> [--json]'
      )
    }

    if (option && option !== '--json') {
      return errorResult(
        `Unknown option '${option}'.`,
        'vxs describe <command> [--json]'
      )
    }

    const command = getCommands().find(
      item =>
        item.name.toLowerCase() === token ||
        item.aliases.some(alias => alias.toLowerCase() === token)
    )

    if (!command) {
      return {
        kind: 'immediate',
        output: [
          `ERROR: Unknown VXS command '${token}'.`,
          'Run: vxs capabilities',
          ''
        ].map(line).join(''),
        exitCode: 2,
        stream: 'stderr'
      }
    }

    const detail: CapabilityDetail = {
      schema: 'vxs-capability/1',
      capability: describeVxsCapability(command)
    }

    if (option === '--json') {
      return {
        kind: 'immediate',
        output: `${JSON.stringify(detail, null, 2)}\n`,
        exitCode: 0,
        stream: 'system'
      }
    }

    const item = detail.capability
    const rows = [
      'VXS CAPABILITY',
      `Schema: ${detail.schema}`,
      `Name: ${item.name}`,
      `Aliases: ${item.aliases.length ? item.aliases.join(', ') : '(none)'}`,
      `Usage: ${item.usage}`,
      `Summary: ${item.summary}`,
      `Safety: ${item.safety_class}`,
      `Human Gate: ${item.requires_human_gate ? 'REQUIRED' : 'NO'}`,
      `Automatic Execution: ${item.automatic_execution ? 'YES' : 'NO'}`,
      '',
      'CAPABILITY_DISCOVERY_EXECUTION=NONE',
      ''
    ]

    return {
      kind: 'immediate',
      output: rows.map(line).join(''),
      exitCode: 0,
      stream: 'system'
    }
  }

  return [
    {
      name: 'capabilities',
      aliases: ['caps'],
      usage: 'vxs capabilities [--json]',
      summary: 'List machine-discoverable VXS command capabilities',
      execute: capabilitiesCommand
    },
    {
      name: 'describe',
      aliases: ['capability'],
      usage: 'vxs describe <command> [--json]',
      summary: 'Describe one VXS command and its safety class',
      execute: describeCommand
    }
  ]
}
