// VXS_AUTONOMOUS_PREPARATION_LOOP_000026
import { detectVxsWorkspace } from './vxs-workspace-detector'
import {
  buildVxsCapabilityCatalog
} from './vxs-capability-discovery'
import {
  runVxsSelfTest,
  buildVxsAutonomyPolicy
} from './vxs-autonomy-foundation-capabilities'
import {
  buildVxsAgentContextSnapshot
} from './vxs-agent-context-capabilities'
import {
  assessVxsReadiness,
  recommendVxsNextCommands
} from './vxs-agent-decision-capabilities'
import {
  createVxsVerificationPlan,
  chainVxsVerificationCommands,
  type VerifyMode,
  type VerificationPlan
} from './vxs-orchestration-capabilities'
import type {
  VxsCommandContext,
  VxsCommandDefinition,
  VxsCommandDispatchResult,
  VxsExecutionCommandResult
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

interface PreparationPlan {
  schema: 'vxs-preparation-plan/1'
  generated_at: string
  mode: 'AUTONOMOUS_PREPARATION'
  workspace: {
    root: string
    branch: string | null
    changed_count: number
  }
  selftest: 'PASS'
  readiness: {
    state: string
    score: number
  }
  verification: {
    mode: VerifyMode
    ecosystems: string[]
    changed_files: number
    steps: string[]
    clean: boolean
  }
  authority: {
    automatic_safe_verification: true
    arbitrary_run_auto_execution: false
    vra_auto_dispatch: false
    human_gate_bypass: false
    workstation_lane_allocation_authority: 'WORKSTATION'
  }
}

interface ApprovalPointPacket {
  schema: 'vxs-approval-point/1'
  generated_at: string
  status:
    | 'READY_FOR_HUMAN_REVIEW'
    | 'NO_CHANGES'
    | 'PREPARATION_BLOCKED'
  workspace: {
    root: string
    branch: string | null
    changed_count: number
  }
  readiness: {
    state: string
    score: number
  }
  safe_verification: {
    mode: VerifyMode
    result: 'PASS_IF_PACKET_EMITTED' | 'SKIPPED_CLEAN' | 'NOT_RUN'
    steps: string[]
  }
  recommended_next_commands: string[]
  approval: {
    required: boolean
    type: 'HUMAN_GATE' | 'NONE'
    instruction: string
  }
  authority: {
    human_gate_bypass: false
    automatic_vra_dispatch: false
    arbitrary_run_auto_execution: false
    workstation_lane_allocation_authority: 'WORKSTATION'
    observation_authoritative: false
  }
}

function powerShellLiteral(value: string): string {
  return `'${value.replace(/'/g, "''")}'`
}

function posixLiteral(value: string): string {
  return `'${value.replace(/'/g, `'\"'\"'`)}'`
}

function appendApprovalEmitter(
  verificationCommand: string,
  packet: ApprovalPointPacket
): string {
  const json = JSON.stringify(packet)

  if (process.platform === 'win32') {
    return [
      verificationCommand,
      `Write-Output 'VXS_APPROVAL_POINT/1'`,
      `Write-Output ${powerShellLiteral(json)}`,
      `Write-Output '[/VXS_APPROVAL_POINT/1]'`
    ].join('; ')
  }

  return [
    verificationCommand,
    `printf '%s\\n' 'VXS_APPROVAL_POINT/1' ${posixLiteral(json)} '[/VXS_APPROVAL_POINT/1]'`
  ].join(' && ')
}

function buildPlan(
  context: VxsCommandContext,
  commands: readonly VxsCommandDefinition[]
):
  | {
      plan: PreparationPlan
      verifyPlan: VerificationPlan
      approval: ApprovalPointPacket
    }
  | { error: string } {
  const selftest = runVxsSelfTest(commands)
  if (selftest.status !== 'PASS') {
    const failed = selftest.checks
      .filter(check => check.status === 'FAIL')
      .map(check => check.code)
      .join(', ')

    return {
      error: `VXS self-test failed: ${failed || 'unknown contract failure'}`
    }
  }

  const catalog = buildVxsCapabilityCatalog(commands)
  const policy = buildVxsAutonomyPolicy(catalog.capabilities)

  if (
    !policy.automatic_local_verification ||
    !policy.automatic_execution_allowlist.includes('verify') ||
    !policy.automatic_execution_allowlist.includes('prepare')
  ) {
    return {
      error: 'Autonomy policy does not permit autonomous safe preparation.'
    }
  }

  const snapshot = buildVxsAgentContextSnapshot(context)
  const readiness = assessVxsReadiness(snapshot)
  const recommendations = recommendVxsNextCommands(
    snapshot,
    readiness
  )

  const workspace = detectVxsWorkspace(context.cwd)
  const verifyMode: VerifyMode = snapshot.workspace.git
    ? 'changed'
    : 'quick'

  const verifyPlan = createVxsVerificationPlan(
    workspace,
    verifyMode
  )

  if ('error' in verifyPlan) {
    return {
      error: `Verification planning failed: ${verifyPlan.error}`
    }
  }

  const plan: PreparationPlan = {
    schema: 'vxs-preparation-plan/1',
    generated_at: snapshot.generated_at,
    mode: 'AUTONOMOUS_PREPARATION',
    workspace: {
      root: snapshot.workspace.root,
      branch: snapshot.git.branch,
      changed_count: snapshot.git.changed_count
    },
    selftest: 'PASS',
    readiness: {
      state: readiness.state,
      score: readiness.score
    },
    verification: {
      mode: verifyPlan.mode,
      ecosystems: verifyPlan.ecosystems,
      changed_files: verifyPlan.changedFiles.length,
      steps: verifyPlan.labels,
      clean: verifyPlan.clean
    },
    authority: {
      automatic_safe_verification: true,
      arbitrary_run_auto_execution: false,
      vra_auto_dispatch: false,
      human_gate_bypass: false,
      workstation_lane_allocation_authority: 'WORKSTATION'
    }
  }

  const recommendedNextCommands = recommendations.recommendations
    .map(item => item.command)
    .filter(command => !/^vxs\s+prepare(?:\s|$)/i.test(command))
    .slice(0, 8)

  const noChanges =
    verifyPlan.mode === 'changed' &&
    verifyPlan.clean

  const approval: ApprovalPointPacket = {
    schema: 'vxs-approval-point/1',
    generated_at: snapshot.generated_at,
    status: noChanges
      ? 'NO_CHANGES'
      : 'READY_FOR_HUMAN_REVIEW',
    workspace: {
      root: snapshot.workspace.root,
      branch: snapshot.git.branch,
      changed_count: snapshot.git.changed_count
    },
    readiness: {
      state: readiness.state,
      score: readiness.score
    },
    safe_verification: {
      mode: verifyPlan.mode,
      result: noChanges
        ? 'SKIPPED_CLEAN'
        : 'PASS_IF_PACKET_EMITTED',
      steps: verifyPlan.labels
    },
    recommended_next_commands: recommendedNextCommands,
    approval: {
      required: !noChanges,
      type: noChanges ? 'NONE' : 'HUMAN_GATE',
      instruction: noChanges
        ? 'No changed-scope approval is required.'
        : 'Review the proposed mutation/VRA at the existing Human Gate. VXS has not dispatched or applied it.'
    },
    authority: {
      human_gate_bypass: false,
      automatic_vra_dispatch: false,
      arbitrary_run_auto_execution: false,
      workstation_lane_allocation_authority: 'WORKSTATION',
      observation_authoritative: false
    }
  }

  return {
    plan,
    verifyPlan,
    approval
  }
}

function renderPlan(
  plan: PreparationPlan,
  approval: ApprovalPointPacket
): string {
  const rows = [
    'VXS AUTONOMOUS PREPARATION PLAN',
    `Schema: ${plan.schema}`,
    `Generated: ${plan.generated_at}`,
    `Workspace: ${plan.workspace.root}`,
    `Branch: ${plan.workspace.branch ?? '(none)'}`,
    `Changed Rows: ${plan.workspace.changed_count}`,
    `Readiness: ${plan.readiness.state} (${plan.readiness.score}/100)`,
    `Verification Mode: ${plan.verification.mode}`,
    `Verification Steps: ${plan.verification.steps.length}`,
    ''
  ]

  if (plan.verification.steps.length) {
    for (const step of plan.verification.steps) {
      rows.push(`  ${step}`)
    }
  } else if (plan.verification.clean) {
    rows.push('  (clean working tree; no changed-scope verification required)')
  } else {
    rows.push('  (no supported verification steps detected)')
  }

  rows.push('')
  rows.push(`Approval Status: ${approval.status}`)
  rows.push(`Human Gate Required: ${approval.approval.required ? 'YES' : 'NO'}`)
  rows.push('Automatic VRA Dispatch: NO')
  rows.push('Arbitrary run Auto Execution: NO')
  rows.push('Lane Allocation Authority: WORKSTATION')
  rows.push('')
  rows.push('PLAN_ONLY=YES')
  rows.push('')

  return rows.map(line).join('')
}

function renderApproval(
  packet: ApprovalPointPacket
): string {
  return [
    'VXS_APPROVAL_POINT/1',
    JSON.stringify(packet),
    '[/VXS_APPROVAL_POINT/1]',
    ''
  ].map(line).join('')
}

export function createVxsAutonomousPreparationCommands(
  getCommands: () => readonly VxsCommandDefinition[]
): VxsCommandDefinition[] {
  function prepareCommand(
    args: string[],
    context: VxsCommandContext
  ): VxsCommandDispatchResult {
    const option = (args[0] ?? '').trim()

    if (
      option &&
      option !== '--plan' &&
      option !== '--json'
    ) {
      return immediateError(
        `Unknown option '${option}'.`,
        [
          'Usage: vxs prepare [--plan|--json]',
          'Default: execute policy-approved safe verification and emit an approval point only after success.'
        ]
      )
    }

    const built = buildPlan(context, getCommands())

    if ('error' in built) {
      return immediateError(
        built.error,
        [
          'Autonomous preparation stopped fail-closed.',
          'No VRA was dispatched and no Human Gate was bypassed.'
        ]
      )
    }

    const { plan, verifyPlan, approval } = built

    if (option === '--json') {
      return {
        kind: 'immediate',
        output: `${JSON.stringify({
          schema: 'vxs-autonomous-preparation/1',
          plan,
          approval_preview: approval
        }, null, 2)}\n`,
        exitCode: 0,
        stream: 'system'
      }
    }

    if (option === '--plan') {
      return {
        kind: 'immediate',
        output: renderPlan(plan, approval),
        exitCode: 0,
        stream: 'system'
      }
    }

    if (verifyPlan.clean) {
      return {
        kind: 'immediate',
        output: renderApproval(approval),
        exitCode: 0,
        stream: 'system'
      }
    }

    if (!verifyPlan.commands.length) {
      return immediateError(
        'Autonomous preparation has changes but no supported safe verification pipeline.',
        [
          'Run: vxs prepare --plan',
          'Run: vxs ray',
          'No approval point was emitted.'
        ]
      )
    }

    const verificationCommand =
      chainVxsVerificationCommands(verifyPlan.commands)

    const result: VxsExecutionCommandResult = {
      kind: 'execute',
      executionCommand: appendApprovalEmitter(
        verificationCommand,
        approval
      ),
      executionCwd: plan.workspace.root,
      capability: 'AUTONOMOUS_PREPARATION_SAFE_VERIFY',
      routeSummary:
        `VXS prepare: selftest PASS -> ${verifyPlan.mode} safe verify -> Human Gate approval point`
    }

    return result
  }

  return [
    {
      name: 'prepare',
      aliases: ['prep'],
      usage: 'vxs prepare [--plan|--json]',
      summary: 'Autonomously prepare safe verification up to the Human Gate',
      execute: prepareCommand
    }
  ]
}
