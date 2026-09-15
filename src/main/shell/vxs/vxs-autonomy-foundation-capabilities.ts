// VXS_AUTONOMOUS_PREPARATION_LOOP_000026
// VXS_AUTONOMOUS_PREPARATION_FOUNDATION_000025
import {
  buildVxsCapabilityCatalog,
  type CapabilityDescriptor
} from './vxs-capability-discovery'
import type {
  VxsCommandDefinition,
  VxsCommandDispatchResult
} from './vxs-command-registry'

function line(value = ''): string {
  return `${value}\n`
}

function errorResult(
  message: string,
  usage: string
): VxsCommandDispatchResult {
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

export interface SelfTestCheck {
  code: string
  status: 'PASS' | 'FAIL'
  detail: string
}

export interface SelfTestResult {
  schema: 'vxs-selftest/1'
  status: 'PASS' | 'FAIL'
  command_count: number
  checks: SelfTestCheck[]
}

export interface AutonomyPolicy {
  schema: 'vxs-autonomy-policy/1'
  mode: 'AUTONOMOUS_PREPARATION'
  automatic_observation: true
  automatic_local_verification: true
  automatic_execution_allowlist: string[]
  automatic_execution_denylist: string[]
  human_gated_commands: string[]
  rules: {
    human_gate_bypass: false
    workstation_lane_allocation_authority: 'WORKSTATION'
    observation_authoritative: false
    production_mutation_during_verify: false
    arbitrary_run_auto_execution: false
  }
}

const NAME_PATTERN = /^[a-z0-9][a-z0-9-]*$/
const ALIAS_PATTERN = /^(?:--?[a-z0-9][a-z0-9-]*|[a-z0-9][a-z0-9-]*)$/

const AUTO_LOCAL_ALLOWLIST = new Set([
  'check',
  'lint',
  'test',
  'build',
  'verify',
  'prepare'
])

const AUTO_EXECUTION_DENYLIST = new Set([
  'run',
  'vra'
])

function pushCheck(
  checks: SelfTestCheck[],
  code: string,
  ok: boolean,
  detail: string
): void {
  checks.push({
    code,
    status: ok ? 'PASS' : 'FAIL',
    detail
  })
}

function duplicateValues(values: string[]): string[] {
  const counts = new Map<string, number>()

  for (const raw of values) {
    const value = raw.toLowerCase()
    counts.set(value, (counts.get(value) ?? 0) + 1)
  }

  return [...counts.entries()]
    .filter(([, count]) => count > 1)
    .map(([value]) => value)
    .sort()
}

export function runVxsSelfTest(
  commands: readonly VxsCommandDefinition[]
): SelfTestResult {
  const checks: SelfTestCheck[] = []
  const catalog = buildVxsCapabilityCatalog(commands)

  const names = commands.map(command => command.name)
  const aliases = commands.flatMap(command => command.aliases)

  const duplicateNames = duplicateValues(names)
  pushCheck(
    checks,
    'UNIQUE_COMMAND_NAMES',
    duplicateNames.length === 0,
    duplicateNames.length
      ? `Duplicates: ${duplicateNames.join(', ')}`
      : 'All canonical command names are unique.'
  )

  const duplicateAliases = duplicateValues(aliases)
  pushCheck(
    checks,
    'UNIQUE_ALIASES',
    duplicateAliases.length === 0,
    duplicateAliases.length
      ? `Duplicates: ${duplicateAliases.join(', ')}`
      : 'All aliases are unique.'
  )

  const canonical = new Set(names.map(value => value.toLowerCase()))
  const shadowedAliases = aliases
    .map(value => value.toLowerCase())
    .filter(value => canonical.has(value))

  pushCheck(
    checks,
    'ALIASES_DO_NOT_SHADOW_COMMANDS',
    shadowedAliases.length === 0,
    shadowedAliases.length
      ? `Shadowing aliases: ${[...new Set(shadowedAliases)].join(', ')}`
      : 'No alias shadows a canonical command name.'
  )

  const invalidNames = names.filter(value => !NAME_PATTERN.test(value))
  pushCheck(
    checks,
    'COMMAND_NAME_FORMAT',
    invalidNames.length === 0,
    invalidNames.length
      ? `Invalid names: ${invalidNames.join(', ')}`
      : 'Canonical names satisfy the VXS command token contract.'
  )

  const invalidAliases = aliases.filter(
    value => !ALIAS_PATTERN.test(value)
  )
  pushCheck(
    checks,
    'ALIAS_FORMAT',
    invalidAliases.length === 0,
    invalidAliases.length
      ? `Invalid aliases: ${invalidAliases.join(', ')}`
      : 'Aliases satisfy the VXS token contract.'
  )

  const invalidUsage = commands
    .filter(command => !/^vxs(?:\s|$)/.test(command.usage))
    .map(command => command.name)

  pushCheck(
    checks,
    'USAGE_PREFIX',
    invalidUsage.length === 0,
    invalidUsage.length
      ? `Usage missing vxs prefix: ${invalidUsage.join(', ')}`
      : 'Every usage string starts with vxs.'
  )

  pushCheck(
    checks,
    'CATALOG_COUNT_MATCH',
    catalog.command_count === commands.length,
    `${catalog.command_count}/${commands.length} commands represented.`
  )

  const invalidHumanGate = catalog.capabilities
    .filter(item =>
      item.safety_class === 'HUMAN_GATED' &&
      (
        !item.requires_human_gate ||
        item.automatic_execution
      )
    )
    .map(item => item.name)

  pushCheck(
    checks,
    'HUMAN_GATE_CONTRACT',
    invalidHumanGate.length === 0,
    invalidHumanGate.length
      ? `Invalid HUMAN_GATED metadata: ${invalidHumanGate.join(', ')}`
      : 'HUMAN_GATED commands require Human Gate and disable auto execution.'
  )

  const vra = catalog.capabilities.find(item => item.name === 'vra')
  pushCheck(
    checks,
    'VRA_IS_HUMAN_GATED',
    Boolean(vra && vra.safety_class === 'HUMAN_GATED'),
    vra
      ? `vra safety=${vra.safety_class}`
      : 'vra capability was not found.'
  )

  const arbitraryRun = catalog.capabilities.find(
    item => item.name === 'run'
  )
  pushCheck(
    checks,
    'ARBITRARY_RUN_NOT_AUTOMATIC',
    Boolean(
      arbitraryRun &&
      arbitraryRun.safety_class === 'EXECUTE_LOCAL' &&
      !arbitraryRun.automatic_execution
    ),
    arbitraryRun
      ? `run safety=${arbitraryRun.safety_class}, automatic=${arbitraryRun.automatic_execution}`
      : 'run capability was not found.'
  )

  const status = checks.some(check => check.status === 'FAIL')
    ? 'FAIL'
    : 'PASS'

  return {
    schema: 'vxs-selftest/1',
    status,
    command_count: commands.length,
    checks
  }
}

export function buildVxsAutonomyPolicy(
  capabilities: CapabilityDescriptor[]
): AutonomyPolicy {
  const existing = new Set(capabilities.map(item => item.name))

  const automaticExecutionAllowlist = [...AUTO_LOCAL_ALLOWLIST]
    .filter(name => existing.has(name))
    .sort()

  const automaticExecutionDenylist = [...AUTO_EXECUTION_DENYLIST]
    .filter(name => existing.has(name))
    .sort()

  const humanGatedCommands = capabilities
    .filter(item => item.safety_class === 'HUMAN_GATED')
    .map(item => item.name)
    .sort()

  return {
    schema: 'vxs-autonomy-policy/1',
    mode: 'AUTONOMOUS_PREPARATION',
    automatic_observation: true,
    automatic_local_verification: true,
    automatic_execution_allowlist: automaticExecutionAllowlist,
    automatic_execution_denylist: automaticExecutionDenylist,
    human_gated_commands: humanGatedCommands,
    rules: {
      human_gate_bypass: false,
      workstation_lane_allocation_authority: 'WORKSTATION',
      observation_authoritative: false,
      production_mutation_during_verify: false,
      arbitrary_run_auto_execution: false
    }
  }
}

function renderSelfTest(result: SelfTestResult): string {
  const rows = [
    'VXS SELFTEST',
    `Schema: ${result.schema}`,
    `Status: ${result.status}`,
    `Commands: ${result.command_count}`,
    ''
  ]

  for (const check of result.checks) {
    rows.push(
      `  [${check.status}] ${check.code} - ${check.detail}`
    )
  }

  rows.push('')
  rows.push('SELFTEST_MUTATION=NONE')
  rows.push('')

  return rows.map(line).join('')
}

function renderPolicy(policy: AutonomyPolicy): string {
  const rows = [
    'VXS AUTONOMY POLICY',
    `Schema: ${policy.schema}`,
    `Mode: ${policy.mode}`,
    '',
    `Automatic Observation: ${policy.automatic_observation ? 'YES' : 'NO'}`,
    `Automatic Local Verification: ${policy.automatic_local_verification ? 'YES' : 'NO'}`,
    `Auto Execute Allowlist: ${
      policy.automatic_execution_allowlist.length
        ? policy.automatic_execution_allowlist.join(', ')
        : '(none)'
    }`,
    `Auto Execute Denylist: ${
      policy.automatic_execution_denylist.length
        ? policy.automatic_execution_denylist.join(', ')
        : '(none)'
    }`,
    `Human Gated Commands: ${
      policy.human_gated_commands.length
        ? policy.human_gated_commands.join(', ')
        : '(none)'
    }`,
    '',
    'Fixed Rules:',
    '  Human Gate bypass: NO',
    '  Lane Allocation Authority: WORKSTATION',
    '  Observation authoritative: NO',
    '  Production mutation during VERIFY: NO',
    '  Arbitrary run auto execution: NO',
    '',
    'POLICY_EXECUTION=NONE',
    ''
  ]

  return rows.map(line).join('')
}

export function createVxsAutonomyFoundationCommands(
  getCommands: () => readonly VxsCommandDefinition[]
): VxsCommandDefinition[] {
  function selftestCommand(
    args: string[]
  ): VxsCommandDispatchResult {
    const option = (args[0] ?? '').trim()

    if (option && option !== '--json') {
      return errorResult(
        `Unknown option '${option}'.`,
        'vxs selftest [--json]'
      )
    }

    const result = runVxsSelfTest(getCommands())

    return {
      kind: 'immediate',
      output:
        option === '--json'
          ? `${JSON.stringify(result, null, 2)}\n`
          : renderSelfTest(result),
      exitCode: result.status === 'PASS' ? 0 : 1,
      stream: result.status === 'PASS' ? 'system' : 'stderr'
    }
  }

  function policyCommand(
    args: string[]
  ): VxsCommandDispatchResult {
    const option = (args[0] ?? '').trim()

    if (option && option !== '--json') {
      return errorResult(
        `Unknown option '${option}'.`,
        'vxs policy [--json]'
      )
    }

    const catalog = buildVxsCapabilityCatalog(getCommands())
    const policy = buildVxsAutonomyPolicy(catalog.capabilities)

    return {
      kind: 'immediate',
      output:
        option === '--json'
          ? `${JSON.stringify(policy, null, 2)}\n`
          : renderPolicy(policy),
      exitCode: 0,
      stream: 'system'
    }
  }

  return [
    {
      name: 'selftest',
      aliases: ['contract-check'],
      usage: 'vxs selftest [--json]',
      summary: 'Validate VXS registry and authority contracts',
      execute: selftestCommand
    },
    {
      name: 'policy',
      aliases: ['authority-policy'],
      usage: 'vxs policy [--json]',
      summary: 'Describe autonomous preparation and Human Gate policy',
      execute: policyCommand
    }
  ]
}
