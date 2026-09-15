// VXS_AGENT_DECISION_CAPABILITY_PACK_000022
// VXS_AGENT_CONTEXT_CAPABILITY_PACK_000021
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

interface CommandResult {
  ok: boolean
  stdout: string
  stderr: string
}

interface RecentJobSummary {
  job_id: string
  state: string
  result: string
  artifact_id: string
  lane: string
  updated_at: string
}

export interface AgentContextSnapshot {
  schema: 'vxs-agent-context/1'
  generated_at: string
  host: {
    platform: string
    arch: string
    node: string
    electron: string | null
    chrome: string | null
  }
  workspace: {
    cwd: string
    root: string
    kind: string
    markers: string[]
    package_manager: string | null
    frameworks: string[]
    scripts: string[]
    git: boolean
  }
  git: {
    branch: string | null
    changed_count: number
    changed: string[]
  }
  runtime: {
    pid: number
    uptime_seconds: number
    rss_mib: number
    heap_used_mib: number
    workstation_47832: 'LISTENING' | 'NOT_OBSERVED' | 'UNAVAILABLE'
  }
  tools: Array<{
    name: string
    version: string | null
  }>
  jobs: {
    recent: RecentJobSummary[]
    failures: RecentJobSummary[]
  }
  safety: {
    secret_env_values_included: false
    full_log_bodies_included: false
    filesystem_mutation: false
    network_mutation: false
  }
}

function runReadOnly(
  program: string,
  args: string[],
  cwd?: string,
  timeout = 5_000
): CommandResult {
  try {
    const result = spawnSync(
      program,
      args,
      {
        cwd,
        windowsHide: true,
        shell: false,
        encoding: 'utf-8',
        timeout
      }
    )

    return {
      ok: result.status === 0,
      stdout: (result.stdout ?? '').trim(),
      stderr: (result.stderr ?? '').trim()
    }
  } catch (error) {
    return {
      ok: false,
      stdout: '',
      stderr: error instanceof Error ? error.message : String(error)
    }
  }
}

function firstLine(text: string): string {
  return text.split(/\r?\n/)[0]?.trim() ?? ''
}

function toolVersion(
  name: string,
  program: string,
  args: string[]
): { name: string; version: string | null } {
  const result = runReadOnly(program, args, undefined, 3_000)
  const text = firstLine(result.stdout || result.stderr)

  return {
    name,
    version: result.ok && text ? text.slice(0, 300) : null
  }
}

function workstationListenerState():
  'LISTENING' | 'NOT_OBSERVED' | 'UNAVAILABLE' {
  if (process.platform !== 'win32') return 'UNAVAILABLE'

  const result = runReadOnly(
    'netstat.exe',
    ['-ano', '-p', 'tcp'],
    undefined,
    5_000
  )

  if (!result.ok) return 'UNAVAILABLE'

  const listening = result.stdout
    .split(/\r?\n/)
    .some(value =>
      /127\.0\.0\.1:47832\s+.*LISTENING/i.test(value)
    )

  return listening ? 'LISTENING' : 'NOT_OBSERVED'
}

function gitSnapshot(
  root: string,
  enabled: boolean
): {
  branch: string | null
  changed_count: number
  changed: string[]
} {
  if (!enabled) {
    return {
      branch: null,
      changed_count: 0,
      changed: []
    }
  }

  const branchResult = runReadOnly(
    'git',
    ['branch', '--show-current'],
    root,
    4_000
  )

  const statusResult = runReadOnly(
    'git',
    ['status', '--short', '--untracked-files=normal'],
    root,
    5_000
  )

  const changed = statusResult.ok
    ? statusResult.stdout
        .split(/\r?\n/)
        .filter(Boolean)
        .slice(0, 120)
    : []

  return {
    branch:
      branchResult.ok && branchResult.stdout
        ? firstLine(branchResult.stdout)
        : null,
    changed_count: changed.length,
    changed
  }
}

type JsonRecord = Record<string, unknown>

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as JsonRecord
}

function stringField(record: JsonRecord, ...keys: string[]): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function numberField(record: JsonRecord, ...keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value

    if (typeof value === 'string' && /^\d+$/.test(value)) {
      const parsed = Number(value)
      if (Number.isFinite(parsed)) return parsed
    }
  }

  return null
}

function collectJobRecords(
  value: unknown,
  out: JsonRecord[],
  depth = 0
): void {
  if (depth > 8 || out.length >= 1200) return

  const record = asRecord(value)
  if (record) {
    if (typeof record.job_id === 'string' && record.job_id.trim()) {
      out.push(record)
    }

    for (const child of Object.values(record)) {
      collectJobRecords(child, out, depth + 1)
      if (out.length >= 1200) return
    }

    return
  }

  if (Array.isArray(value)) {
    for (const child of value) {
      collectJobRecords(child, out, depth + 1)
      if (out.length >= 1200) return
    }
  }
}

function jobTimestamp(
  record: JsonRecord,
  fallbackMs: number
): number {
  const direct = numberField(
    record,
    'updated_ms',
    'completed_ms',
    'created_ms',
    'started_ms'
  )

  if (direct !== null) return direct

  const timestamps = asRecord(record.timestamps)

  if (timestamps) {
    for (const key of [
      'updated_at',
      'completed_at',
      'created_at',
      'started_at'
    ]) {
      const value = timestamps[key]

      if (typeof value === 'string') {
        const unix = /^unix-ms:(\d+)$/.exec(value)
        if (unix) return Number(unix[1])

        const parsed = Date.parse(value)
        if (Number.isFinite(parsed)) return parsed
      }
    }
  }

  return fallbackMs
}

function isFailure(record: JsonRecord): boolean {
  const nested = asRecord(record.record)
  const values = [
    stringField(record, 'state', 'status', 'result', 'error', 'last_error'),
    nested ? stringField(nested, 'state', 'status', 'result', 'error') : ''
  ].join(' ').toLowerCase()

  return (
    values.includes('fail') ||
    values.includes('reject') ||
    values.includes('rollback') ||
    values.includes('error') ||
    values.includes('conflict')
  )
}

function recentJobs(): {
  recent: RecentJobSummary[]
  failures: RecentJobSummary[]
} {
  const root =
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry'

  if (!fs.existsSync(root)) {
    return {
      recent: [],
      failures: []
    }
  }

  let names: string[]
  try {
    names = fs.readdirSync(root)
      .filter(name => name.endsWith('.json'))
      .slice(-800)
  } catch {
    return {
      recent: [],
      failures: []
    }
  }

  const dedupe = new Map<
    string,
    { record: JsonRecord; updatedMs: number }
  >()

  for (const name of names) {
    const filePath = path.join(root, name)

    try {
      const stat = fs.statSync(filePath)
      if (!stat.isFile() || stat.size > 4 * 1024 * 1024) continue

      const data = JSON.parse(
        fs.readFileSync(filePath, 'utf-8')
      ) as unknown

      const records: JsonRecord[] = []
      collectJobRecords(data, records)

      for (const record of records) {
        const jobId = stringField(record, 'job_id')
        if (!jobId) continue

        const updatedMs = jobTimestamp(record, stat.mtimeMs)
        const existing = dedupe.get(jobId)

        if (!existing || updatedMs >= existing.updatedMs) {
          dedupe.set(jobId, { record, updatedMs })
        }
      }
    } catch {
      // Snapshot is best-effort and read-only.
    }
  }

  const ordered = [...dedupe.entries()]
    .sort((a, b) => b[1].updatedMs - a[1].updatedMs)

  function summarize(
    jobId: string,
    record: JsonRecord,
    updatedMs: number
  ): RecentJobSummary {
    const nested = asRecord(record.record)

    return {
      job_id: jobId,
      state:
        stringField(record, 'state', 'status', 'job_state') ||
        (nested ? stringField(nested, 'state', 'status') : ''),
      result:
        stringField(record, 'result') ||
        (nested ? stringField(nested, 'result') : ''),
      artifact_id:
        stringField(record, 'artifact_id') ||
        (nested ? stringField(nested, 'artifact_id') : ''),
      lane:
        stringField(record, 'allocated_lane', 'execution_lane') ||
        (nested
          ? stringField(nested, 'allocated_lane', 'execution_lane')
          : ''),
      updated_at: new Date(updatedMs).toISOString()
    }
  }

  const recent = ordered
    .slice(0, 12)
    .map(([jobId, value]) =>
      summarize(jobId, value.record, value.updatedMs)
    )

  const failures = ordered
    .filter(([, value]) => isFailure(value.record))
    .slice(0, 8)
    .map(([jobId, value]) =>
      summarize(jobId, value.record, value.updatedMs)
    )

  return {
    recent,
    failures
  }
}

export function buildVxsAgentContextSnapshot(
  context: VxsCommandContext
): AgentContextSnapshot {
  const workspace = detectVxsWorkspace(context.cwd)
  const git = gitSnapshot(workspace.root, workspace.git)
  const jobs = recentJobs()
  const memory = process.memoryUsage()

  const tools = [
    toolVersion('git', 'git', ['--version']),
    toolVersion(
      'pwsh',
      process.platform === 'win32' ? 'pwsh.exe' : 'pwsh',
      ['--version']
    ),
    toolVersion('python', 'python', ['--version']),
    toolVersion('cargo', 'cargo', ['--version']),
    toolVersion('rustc', 'rustc', ['--version'])
  ]

  if (workspace.packageManager) {
    tools.push(
      toolVersion(
        workspace.packageManager,
        process.platform === 'win32'
          ? `${workspace.packageManager}.cmd`
          : workspace.packageManager,
        ['--version']
      )
    )
  }

  return {
    schema: 'vxs-agent-context/1',
    generated_at: new Date().toISOString(),
    host: {
      platform: process.platform,
      arch: process.arch,
      node: process.versions.node,
      electron: process.versions.electron ?? null,
      chrome: process.versions.chrome ?? null
    },
    workspace: {
      cwd: workspace.cwd,
      root: workspace.root,
      kind: workspace.kind,
      markers: workspace.markers.slice(0, 40),
      package_manager: workspace.packageManager,
      frameworks: workspace.frameworks.slice(0, 40),
      scripts: workspace.scripts.slice(0, 80),
      git: workspace.git
    },
    git,
    runtime: {
      pid: process.pid,
      uptime_seconds: Math.floor(process.uptime()),
      rss_mib: Number((memory.rss / 1024 / 1024).toFixed(1)),
      heap_used_mib: Number((memory.heapUsed / 1024 / 1024).toFixed(1)),
      workstation_47832: workstationListenerState()
    },
    tools,
    jobs,
    safety: {
      secret_env_values_included: false,
      full_log_bodies_included: false,
      filesystem_mutation: false,
      network_mutation: false
    }
  }
}

function renderText(snapshot: AgentContextSnapshot): string {
  const rows = [
    'VXS AGENT CONTEXT',
    `Schema: ${snapshot.schema}`,
    `Generated: ${snapshot.generated_at}`,
    '',
    'Workspace:',
    `  Root: ${snapshot.workspace.root}`,
    `  Type: ${snapshot.workspace.kind}`,
    `  Package Manager: ${snapshot.workspace.package_manager ?? 'not detected'}`,
    `  Frameworks: ${
      snapshot.workspace.frameworks.length
        ? snapshot.workspace.frameworks.join(', ')
        : 'none detected'
    }`,
    '',
    'Git:',
    `  Branch: ${snapshot.git.branch ?? '(none)'}`,
    `  Changed Rows: ${snapshot.git.changed_count}`,
    '',
    'Runtime:',
    `  PID: ${snapshot.runtime.pid}`,
    `  Workstation 47832: ${snapshot.runtime.workstation_47832}`,
    `  RSS MiB: ${snapshot.runtime.rss_mib}`,
    '',
    'Tools:'
  ]

  for (const tool of snapshot.tools) {
    rows.push(`  ${tool.name}: ${tool.version ?? 'unavailable'}`)
  }

  rows.push('')
  rows.push(`Recent Jobs: ${snapshot.jobs.recent.length}`)

  for (const job of snapshot.jobs.recent.slice(0, 6)) {
    rows.push(
      `  ${job.updated_at} | ${job.state || job.result || 'unknown'} | ${job.lane || '-'} | ${job.job_id}`
    )
  }

  rows.push('')
  rows.push(`Recent Failures: ${snapshot.jobs.failures.length}`)

  for (const job of snapshot.jobs.failures.slice(0, 5)) {
    rows.push(
      `  ${job.updated_at} | ${job.state || job.result || 'unknown'} | ${job.job_id}`
    )
  }

  rows.push('')
  rows.push('Safety:')
  rows.push('  Secret environment values: NOT INCLUDED')
  rows.push('  Full log bodies: NOT INCLUDED')
  rows.push('  Mutation: NONE')
  rows.push('')

  return rows.map(line).join('')
}

function contextCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const option = (args[0] ?? '').trim()

  if (option && option !== '--json') {
    return immediateError(
      `Unknown option '${option}'.`,
      ['Usage: vxs context [--json]']
    )
  }

  const snapshot = buildVxsAgentContextSnapshot(context)

  return {
    kind: 'immediate',
    output:
      option === '--json'
        ? `${JSON.stringify(snapshot, null, 2)}\n`
        : renderText(snapshot),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsAgentContextCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'context',
      aliases: ['ctx'],
      usage: 'vxs context [--json]',
      summary: 'Create a bounded safe development context snapshot',
      execute: contextCommand
    }
  ]
}
