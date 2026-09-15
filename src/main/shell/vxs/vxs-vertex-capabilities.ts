import * as path from 'node:path'
import {
  detectVxsWorkspace
} from './vxs-workspace-detector'
import type {
  VxsCommandContext,
  VxsCommandDefinition,
  VxsCommandDispatchResult
} from './vxs-command-registry'
import {
  vxsWorkstationReadAdapter
} from './vxs-workstation-read-adapter'

const PORTAL_ROOT = 'G:\\Vertex_Project\\Development\\vertex_session_portal'

function line(value = ''): string {
  return `${value}\n`
}

function immediate(
  output: string[],
  exitCode = 0,
  stream: 'system' | 'stderr' = 'system'
): VxsCommandDispatchResult {
  return {
    kind: 'immediate',
    output: output.map(line).join(''),
    exitCode,
    stream
  }
}

function error(message: string, hints: string[] = []): VxsCommandDispatchResult {
  return immediate(
    [`ERROR: ${message}`, ...hints, ''],
    2,
    'stderr'
  )
}

function psSingleQuote(value: string): string {
  return `'${value.replaceAll("'", "''")}'`
}

function rayCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)
  const pattern = args.join(' ').trim()
  const script = path.join(PORTAL_ROOT, 'scripts', 'vxs', 'vxs_ray.py')

  const pieces = [
    'python',
    psSingleQuote(script),
    '--root',
    psSingleQuote(workspace.root)
  ]

  if (pattern) {
    pieces.push('--pattern', psSingleQuote(pattern))
  }

  return {
    kind: 'execute',
    executionCommand: pieces.join(' '),
    executionCwd: workspace.root,
    capability: 'RAY',
    routeSummary: pattern
      ? `Read-only workspace Ray · pattern=${pattern}`
      : 'Read-only workspace Ray · structural summary'
  }
}

function vraCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const body = args.join(' ').trim()

  if (!body || /^help$/i.test(body)) {
    return immediate([
      'VXS VRA',
      '',
      '  vxs vra list',
      '  vxs vra dispatch <artifact-id|card-id|filename>',
      '',
      'These commands alias the existing Portal Native VRA path.',
      'Dispatch remains an explicit Human command through the existing Human Gate.',
      ''
    ])
  }

  // Renderer runtime rewrites `vxs vra ...` to the already-existing native
  // `vra ...` command before Host execution reaches this registry.
  // Reaching main means the alias bridge did not fire; fail closed.
  return error(
    'Native VRA alias bridge did not intercept this command.',
    [
      'Expected renderer route: vxs vra ... -> existing vra ...',
      'No fallback dispatch is attempted.'
    ]
  )
}

function workstationCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const sub = (args[0] ?? 'status').toLowerCase()

  if (sub === 'help' || sub === '--help') {
    return immediate([
      'VXS WORKSTATION · READ-ONLY CONTROL PLANE',
      '',
      '  vxs workstation status',
      '  vxs workstation safety',
      '  vxs workstation job <job-id>',
      '',
      `Endpoint: ${vxsWorkstationReadAdapter.baseUrl}`,
      'Mutation endpoints are not exposed by this VXS pack.',
      ''
    ])
  }

  if (sub === 'status' || sub === 'health') {
    return vxsWorkstationReadAdapter.health()
  }

  if (sub === 'safety') {
    return vxsWorkstationReadAdapter.safety()
  }

  if (sub === 'job') {
    return vxsWorkstationReadAdapter.job(args[1] ?? '')
  }

  return error(
    `Unknown workstation command '${sub}'.`,
    ['Run: vxs workstation help']
  )
}

function evidenceCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  return vxsWorkstationReadAdapter.evidence(args[0] ?? '')
}

export function createVxsVertexCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'ray',
      aliases: [],
      usage: 'vxs ray [pattern]',
      summary: 'Read-only workspace observation',
      execute: rayCommand
    },
    {
      name: 'vra',
      aliases: [],
      usage: 'vxs vra <list|dispatch ...>',
      summary: 'Alias to existing Native VRA commands',
      execute: vraCommand
    },
    {
      name: 'workstation',
      aliases: ['ws'],
      usage: 'vxs workstation <status|safety|job>',
      summary: 'Read Workstation control-plane state',
      execute: workstationCommand
    },
    {
      name: 'evidence',
      aliases: [],
      usage: 'vxs evidence <job-id>',
      summary: 'Read Workstation Evidence for a job',
      execute: evidenceCommand
    }
  ]
}
