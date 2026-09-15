// VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023
import {
  buildVxsAgentContextSnapshot,
  type AgentContextSnapshot
} from './vxs-agent-context-capabilities'
import {
  assessVxsReadiness,
  recommendVxsNextCommands,
  type ReadinessAssessment,
  type RecommendationSet
} from './vxs-agent-decision-capabilities'
import type {
  VxsCommandContext,
  VxsCommandDefinition,
  VxsCommandDispatchResult
} from './vxs-command-registry'

function line(value = ''): string {
  return `${value}\n`
}

function immediateError(
  message: string,
  hints: string[] = []
): VxsCommandDispatchResult {
  return {
    kind: 'immediate',
    output: [`ERROR: ${message}`, ...hints, ''].map(line).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

export interface VxsAgentHandoffPacket {
  schema: 'vxs-agent-handoff/1'
  generated_at: string
  context: AgentContextSnapshot
  readiness: ReadinessAssessment
  recommendations: RecommendationSet
  authority: {
    advisory_only: true
    human_gate_required_for_vra_execution: true
    workstation_lane_authority_preserved: true
    automatic_execution: false
  }
}

export function buildVxsAgentHandoffPacket(
  context: VxsCommandContext
): VxsAgentHandoffPacket {
  const snapshot = buildVxsAgentContextSnapshot(context)
  const readiness = assessVxsReadiness(snapshot)
  const recommendations = recommendVxsNextCommands(
    snapshot,
    readiness
  )

  return {
    schema: 'vxs-agent-handoff/1',
    generated_at: snapshot.generated_at,
    context: snapshot,
    readiness,
    recommendations,
    authority: {
      advisory_only: true,
      human_gate_required_for_vra_execution: true,
      workstation_lane_authority_preserved: true,
      automatic_execution: false
    }
  }
}

function renderHandoff(packet: VxsAgentHandoffPacket): string {
  const rows = [
    'VXS AGENT HANDOFF',
    `Schema: ${packet.schema}`,
    `Generated: ${packet.generated_at}`,
    '',
    'Workspace:',
    `  Root: ${packet.context.workspace.root}`,
    `  Type: ${packet.context.workspace.kind}`,
    `  Branch: ${packet.context.git.branch ?? '(none)'}`,
    `  Changed Rows: ${packet.context.git.changed_count}`,
    '',
    'Readiness:',
    `  State: ${packet.readiness.state}`,
    `  Score: ${packet.readiness.score}/100`,
    '',
    'Signals:'
  ]

  for (const signal of packet.readiness.signals.slice(0, 12)) {
    rows.push(
      `  [${signal.level}] ${signal.code} - ${signal.message}`
    )
  }

  rows.push('')
  rows.push('Recommended Next Commands:')

  if (!packet.recommendations.recommendations.length) {
    rows.push('  (none)')
  } else {
    for (
      const item of packet.recommendations.recommendations.slice(0, 8)
    ) {
      rows.push(
        `  P${item.priority} ${item.code}: ${item.command}`
      )
      rows.push(`    ${item.reason}`)
    }
  }

  rows.push('')
  rows.push('Recent Jobs:')

  if (!packet.context.jobs.recent.length) {
    rows.push('  (none)')
  } else {
    for (const job of packet.context.jobs.recent.slice(0, 6)) {
      rows.push(
        `  ${job.updated_at} | ${job.state || job.result || 'unknown'} | ${job.job_id}`
      )
    }
  }

  rows.push('')
  rows.push('Recent Failures:')

  if (!packet.context.jobs.failures.length) {
    rows.push('  (none)')
  } else {
    for (const job of packet.context.jobs.failures.slice(0, 5)) {
      rows.push(
        `  ${job.updated_at} | ${job.state || job.result || 'unknown'} | ${job.job_id}`
      )
    }
  }

  rows.push('')
  rows.push('Authority:')
  rows.push('  Advisory only: YES')
  rows.push('  Automatic execution: NO')
  rows.push('  Human Gate required for VRA execution: YES')
  rows.push('  Workstation lane authority preserved: YES')
  rows.push('')
  rows.push('HANDOFF_MUTATION=NONE')
  rows.push('')

  return rows.map(line).join('')
}

function handoffCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const option = (args[0] ?? '').trim()

  if (option && option !== '--json') {
    return immediateError(
      `Unknown option '${option}'.`,
      ['Usage: vxs handoff [--json]']
    )
  }

  const packet = buildVxsAgentHandoffPacket(context)

  return {
    kind: 'immediate',
    output:
      option === '--json'
        ? `${JSON.stringify(packet, null, 2)}\n`
        : renderHandoff(packet),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsAgentHandoffCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'handoff',
      aliases: ['brief'],
      usage: 'vxs handoff [--json]',
      summary: 'Bundle context, readiness and recommendations for agent handoff',
      execute: handoffCommand
    }
  ]
}
