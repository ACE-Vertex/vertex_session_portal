// VXS_RUNTIME_DIAGNOSTICS_CAPABILITY_PACK_000016
import { spawnSync } from 'node:child_process'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { detectVxsWorkspace } from './vxs-workspace-detector'
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

interface SpawnResult {
  ok: boolean
  stdout: string
  stderr: string
  status: number | null
}

function runReadOnly(
  program: string,
  args: string[],
  timeout = 5_000
): SpawnResult {
  try {
    const result = spawnSync(
      program,
      args,
      {
        windowsHide: true,
        shell: false,
        encoding: 'utf-8',
        timeout
      }
    )

    return {
      ok: result.status === 0,
      stdout: (result.stdout ?? '').trim(),
      stderr: (result.stderr ?? '').trim(),
      status: result.status
    }
  } catch (error) {
    return {
      ok: false,
      stdout: '',
      stderr: error instanceof Error ? error.message : String(error),
      status: null
    }
  }
}

function commandVersion(
  label: string,
  program: string,
  args: string[]
): string {
  const result = runReadOnly(program, args, 3_000)
  const text = result.stdout || result.stderr

  if (!result.ok || !text) {
    return `${label}: unavailable`
  }

  return `${label}: ${text.split(/\r?\n/)[0].slice(0, 300)}`
}

function versionsCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  const rows = [
    'VXS VERSIONS',
    `Platform: ${process.platform} ${process.arch}`,
    `Node: ${process.versions.node}`,
    `Electron: ${process.versions.electron ?? 'not available'}`,
    `Chrome: ${process.versions.chrome ?? 'not available'}`,
    commandVersion('Git', 'git', ['--version']),
    commandVersion(
      'PowerShell',
      process.platform === 'win32' ? 'pwsh.exe' : 'pwsh',
      ['--version']
    ),
    commandVersion('Python', 'python', ['--version']),
    commandVersion('Cargo', 'cargo', ['--version']),
    commandVersion('Rustc', 'rustc', ['--version']),
    commandVersion(
      'NPM',
      process.platform === 'win32' ? 'npm.cmd' : 'npm',
      ['--version']
    ),
    `Workspace Root: ${workspace.root}`,
    ''
  ]

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function runtimeCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  const workRoot =
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime'

  const portalRuntimeCandidates = [
    path.join(
      process.env.APPDATA ?? '',
      'vertex-session-portal',
      'vra-dispatch'
    ),
    path.join(
      process.env.APPDATA ?? '',
      'Vertex Session Portal',
      'vra-dispatch'
    )
  ].filter(Boolean)

  const rows = [
    'VXS RUNTIME',
    `PID: ${process.pid}`,
    `Uptime Seconds: ${Math.floor(process.uptime())}`,
    `Memory RSS MiB: ${(process.memoryUsage().rss / 1024 / 1024).toFixed(1)}`,
    `Heap Used MiB: ${(process.memoryUsage().heapUsed / 1024 / 1024).toFixed(1)}`,
    `Workspace Root: ${workspace.root}`,
    `Workstation Runtime: ${fs.existsSync(workRoot) ? 'present' : 'missing'}`,
  ]

  for (const candidate of portalRuntimeCandidates) {
    rows.push(
      `Portal Dispatch State: ${candidate} = ${fs.existsSync(candidate) ? 'present' : 'missing'}`
    )
  }

  if (process.platform === 'win32') {
    const ws = runReadOnly(
      'netstat.exe',
      ['-ano', '-p', 'tcp'],
      5_000
    )

    if (ws.ok) {
      const listeners = ws.stdout
        .split(/\r?\n/)
        .filter(value => /\sLISTENING\s/i.test(value))
      rows.push(`TCP Listening Rows: ${listeners.length}`)

      const workstationPort = listeners.filter(value =>
        /:47832\s/.test(value)
      )
      rows.push(
        `Workstation 127.0.0.1:47832: ${workstationPort.length ? 'LISTENING' : 'not observed'}`
      )
    } else {
      rows.push('TCP Listener Probe: unavailable')
    }
  } else {
    rows.push('TCP Listener Probe: Windows netstat adapter not active')
  }

  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function portCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const rawPort = (args[0] ?? '').trim()
  const port = Number.parseInt(rawPort, 10)

  if (
    !Number.isFinite(port) ||
    port < 1 ||
    port > 65535 ||
    String(port) !== rawPort
  ) {
    return immediateError(
      `Invalid port '${rawPort}'.`,
      ['Usage: vxs port <1-65535>']
    )
  }

  if (process.platform !== 'win32') {
    return immediateError(
      'The current runtime diagnostic adapter supports Windows netstat only.'
    )
  }

  const result = runReadOnly(
    'netstat.exe',
    ['-ano', '-p', 'tcp'],
    5_000
  )

  if (!result.ok) {
    return immediateError(
      'netstat query failed.',
      result.stderr ? [result.stderr] : []
    )
  }

  const portPattern = new RegExp(`:${port}\\s`)
  const hits = result.stdout
    .split(/\r?\n/)
    .filter(value => portPattern.test(value))
    .slice(0, 80)

  const pids = new Set<string>()
  for (const hit of hits) {
    const parts = hit.trim().split(/\s+/)
    const pid = parts[parts.length - 1]
    if (/^\d+$/.test(pid)) pids.add(pid)
  }

  const rows = [
    'VXS PORT',
    `Port: ${port}`,
    `Matches: ${hits.length}`,
    '',
    ...(hits.length ? hits : ['(no TCP rows found)']),
    ''
  ]

  if (pids.size) {
    rows.push(`PIDs: ${[...pids].join(', ')}`)
    rows.push('')
  }

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

const PROCESS_QUERY_PATTERN = /^[A-Za-z0-9._+\- ]{1,128}$/

function processCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const query = (args[0] ?? '').trim()

  if (!query) {
    return immediateError(
      'Process name or PID is required.',
      ['Usage: vxs process <name|pid>']
    )
  }

  if (!PROCESS_QUERY_PATTERN.test(query)) {
    return immediateError('Process query contains unsupported characters.')
  }

  if (process.platform !== 'win32') {
    return immediateError(
      'The current runtime diagnostic adapter supports Windows tasklist only.'
    )
  }

  const result = runReadOnly(
    'tasklist.exe',
    ['/FO', 'CSV', '/NH'],
    5_000
  )

  if (!result.ok) {
    return immediateError(
      'tasklist query failed.',
      result.stderr ? [result.stderr] : []
    )
  }

  const numeric = /^\d+$/.test(query)
  const needle = query.toLowerCase()

  const hits = result.stdout
    .split(/\r?\n/)
    .filter(value => {
      const lower = value.toLowerCase()
      if (numeric) {
        return new RegExp(`"${query}"`).test(value)
      }
      return lower.includes(needle)
    })
    .slice(0, 80)

  return {
    kind: 'immediate',
    output: [
      'VXS PROCESS',
      `Query: ${query}`,
      `Matches: ${hits.length}`,
      '',
      ...(hits.length ? hits : ['(no matching process rows found)']),
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsRuntimeDiagnosticsCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'runtime',
      aliases: [],
      usage: 'vxs runtime',
      summary: 'Inspect local VXS/Portal/Workstation runtime state',
      execute: runtimeCommand
    },
    {
      name: 'port',
      aliases: ['ports'],
      usage: 'vxs port <number>',
      summary: 'Inspect TCP ownership for a local port',
      execute: portCommand
    },
    {
      name: 'process',
      aliases: ['ps'],
      usage: 'vxs process <name|pid>',
      summary: 'Inspect Windows process rows',
      execute: processCommand
    },
    {
      name: 'versions',
      aliases: [],
      usage: 'vxs versions',
      summary: 'Show development runtime/tool versions',
      execute: versionsCommand
    }
  ]
}
