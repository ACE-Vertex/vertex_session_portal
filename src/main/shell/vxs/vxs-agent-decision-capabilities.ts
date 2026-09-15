// VXS_AGENT_HANDOFF_CAPABILITY_PACK_000023
// VXS_AGENT_DECISION_CAPABILITY_PACK_000022
import {
  buildVxsAgentContextSnapshot,
  type AgentContextSnapshot
} from './vxs-agent-context-capabilities'
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

type ReadinessState = 'READY' | 'ACTIVE' | 'ATTENTION'

export interface ReadinessAssessment {
  schema: 'vxs-agent-readiness/1'
  generated_at: string
  state: ReadinessState
  score: number
  signals: Array<{
    level: 'INFO' | 'WARN'
    code: string
    message: string
  }>
}

export interface Recommendation {
  priority: number
  code: string
  command: string
  reason: string
}

export interface RecommendationSet {
  schema: 'vxs-agent-recommendations/1'
  generated_at: string
  readiness: ReadinessState
  recommendations: Recommendation[]
}

function clampScore(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)))
}

export function assessVxsReadiness(snapshot: AgentContextSnapshot): ReadinessAssessment {
  const signals: ReadinessAssessment['signals'] = []
  let score = 100

  if (snapshot.workspace.kind === 'directory') {
    signals.push({
      level: 'WARN',
      code: 'WORKSPACE_UNTYPED',
      message: 'No Node/Rust/Python project marker was detected.'
    })
    score -= 20
  } else {
    signals.push({
      level: 'INFO',
      code: 'WORKSPACE_TYPED',
      message: `Workspace type is ${snapshot.workspace.kind}.`
    })
  }

  if (snapshot.git.changed_count > 0) {
    signals.push({
      level: 'INFO',
      code: 'WORKTREE_ACTIVE',
      message: `${snapshot.git.changed_count} changed/untracked Git rows are present.`
    })
    score -= 5
  } else {
    signals.push({
      level: 'INFO',
      code: 'WORKTREE_CLEAN',
      message: 'No changed/untracked Git rows were observed.'
    })
  }

  if (snapshot.jobs.failures.length > 0) {
    signals.push({
      level: 'WARN',
      code: 'RECENT_FAILURES',
      message: `${snapshot.jobs.failures.length} recent failed/rejected Jobs were observed.`
    })
    score -= 25
  } else {
    signals.push({
      level: 'INFO',
      code: 'NO_RECENT_FAILURES',
      message: 'No recent failed/rejected Jobs were observed.'
    })
  }

  if (snapshot.runtime.workstation_47832 === 'LISTENING') {
    signals.push({
      level: 'INFO',
      code: 'WORKSTATION_LISTENING',
      message: 'Workstation loopback listener 127.0.0.1:47832 is present.'
    })
  } else if (snapshot.runtime.workstation_47832 === 'NOT_OBSERVED') {
    signals.push({
      level: 'WARN',
      code: 'WORKSTATION_NOT_OBSERVED',
      message: 'Workstation loopback listener 127.0.0.1:47832 was not observed.'
    })
    score -= 15
  } else {
    signals.push({
      level: 'WARN',
      code: 'WORKSTATION_PROBE_UNAVAILABLE',
      message: 'Workstation listener state could not be determined.'
    })
    score -= 10
  }

  const unavailableTools = snapshot.tools
    .filter(tool => tool.version === null)
    .map(tool => tool.name)

  if (unavailableTools.length) {
    signals.push({
      level: 'WARN',
      code: 'TOOLS_UNAVAILABLE',
      message: `Unavailable tools: ${unavailableTools.join(', ')}`
    })
    score -= Math.min(20, unavailableTools.length * 4)
  }

  const boundedScore = clampScore(score)

  let state: ReadinessState = 'READY'
  if (signals.some(signal => signal.level === 'WARN')) {
    state = 'ATTENTION'
  } else if (snapshot.git.changed_count > 0) {
    state = 'ACTIVE'
  }

  return {
    schema: 'vxs-agent-readiness/1',
    generated_at: snapshot.generated_at,
    state,
    score: boundedScore,
    signals
  }
}

export function recommendVxsNextCommands(
  snapshot: AgentContextSnapshot,
  readiness: ReadinessAssessment
): RecommendationSet {
  const recommendations: Recommendation[] = []

  const latestFailure = snapshot.jobs.failures[0]
  if (latestFailure) {
    recommendations.push({
      priority: 10,
      code: 'TRIAGE_LATEST_FAILURE',
      command: `vxs triage ${latestFailure.job_id}`,
      reason: 'A recent failed/rejected Workstation Job is present.'
    })
  }

  if (snapshot.runtime.workstation_47832 !== 'LISTENING') {
    recommendations.push({
      priority: 20,
      code: 'CHECK_RUNTIME',
      command: 'vxs runtime',
      reason: 'Workstation loopback listener is not currently confirmed.'
    })
    recommendations.push({
      priority: 30,
      code: 'CHECK_WORKSTATION',
      command: 'vxs workstation status',
      reason: 'Confirm the Workstation health endpoint before dispatch-oriented work.'
    })
  }

  if (snapshot.git.changed_count > 0) {
    recommendations.push({
      priority: 40,
      code: 'PLAN_CHANGED_VERIFY',
      command: 'vxs verify-plan changed',
      reason: 'The working tree has changes; preview the scoped verification pipeline.'
    })
    recommendations.push({
      priority: 50,
      code: 'RUN_CHANGED_VERIFY',
      command: 'vxs verify changed',
      reason: 'Run only the ecosystem checks selected from the current Git changes.'
    })
  } else {
    recommendations.push({
      priority: 60,
      code: 'PREFLIGHT',
      command: 'vxs preflight',
      reason: 'The working tree is clean; refresh readiness before the next development action.'
    })
  }

  if (snapshot.workspace.kind === 'directory') {
    recommendations.push({
      priority: 70,
      code: 'RAY_WORKSPACE',
      command: 'vxs ray',
      reason: 'No typed project marker was detected; inspect the workspace before choosing a build path.'
    })
  }

  return {
    schema: 'vxs-agent-recommendations/1',
    generated_at: snapshot.generated_at,
    readiness: readiness.state,
    recommendations: recommendations.sort(
      (a, b) => a.priority - b.priority
    )
  }
}

function renderReadiness(value: ReadinessAssessment): string {
  const rows = [
    'VXS READINESS',
    `Schema: ${value.schema}`,
    `Generated: ${value.generated_at}`,
    `State: ${value.state}`,
    `Score: ${value.score}/100`,
    '',
    'Signals:'
  ]

  for (const signal of value.signals) {
    rows.push(`  [${signal.level}] ${signal.code} - ${signal.message}`)
  }

  rows.push('')
  rows.push('READINESS_EXECUTION=NONE')
  rows.push('')

  return rows.map(line).join('')
}

function renderRecommendations(value: RecommendationSet): string {
  const rows = [
    'VXS RECOMMEND',
    `Schema: ${value.schema}`,
    `Generated: ${value.generated_at}`,
    `Readiness: ${value.readiness}`,
    '',
    'Recommended Next Commands:'
  ]

  if (!value.recommendations.length) {
    rows.push('  (none)')
  } else {
    for (const item of value.recommendations) {
      rows.push(`  P${item.priority} ${item.code}`)
      rows.push(`    ${item.command}`)
      rows.push(`    ${item.reason}`)
    }
  }

  rows.push('')
  rows.push('RECOMMENDATION_EXECUTION=NONE')
  rows.push('')

  return rows.map(line).join('')
}

function parseJsonOption(
  args: string[],
  usage: string
): boolean | VxsCommandDispatchResult {
  const option = (args[0] ?? '').trim()

  if (!option) return false
  if (option === '--json') return true

  return immediateError(
    `Unknown option '${option}'.`,
    [`Usage: ${usage}`]
  )
}

function readinessCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const json = parseJsonOption(args, 'vxs readiness [--json]')
  if (typeof json !== 'boolean') return json

  const snapshot = buildVxsAgentContextSnapshot(context)
  const value = assessVxsReadiness(snapshot)

  return {
    kind: 'immediate',
    output: json
      ? `${JSON.stringify(value, null, 2)}\n`
      : renderReadiness(value),
    exitCode: 0,
    stream: 'system'
  }
}

function recommendCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const json = parseJsonOption(args, 'vxs recommend [--json]')
  if (typeof json !== 'boolean') return json

  const snapshot = buildVxsAgentContextSnapshot(context)
  const readiness = assessVxsReadiness(snapshot)
  const value = recommendVxsNextCommands(snapshot, readiness)

  return {
    kind: 'immediate',
    output: json
      ? `${JSON.stringify(value, null, 2)}\n`
      : renderRecommendations(value),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsAgentDecisionCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'readiness',
      aliases: ['ready'],
      usage: 'vxs readiness [--json]',
      summary: 'Assess bounded development readiness from current context',
      execute: readinessCommand
    },
    {
      name: 'recommend',
      aliases: ['next'],
      usage: 'vxs recommend [--json]',
      summary: 'Recommend existing VXS commands without executing them',
      execute: recommendCommand
    }
  ]
}
