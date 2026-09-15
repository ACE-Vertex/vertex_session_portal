// VXS_JOB_INTELLIGENCE_CAPABILITY_PACK_000020
import * as fs from 'node:fs'
import * as path from 'node:path'
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

type JsonRecord = Record<string, unknown>

interface IndexedJob {
  jobId: string
  state: string
  result: string
  artifactId: string
  lane: string
  updatedMs: number
  sourcePath: string
  record: JsonRecord
}

const JOB_ID_PATTERN = /^[A-Za-z0-9._:-]{1,256}$/
const JOB_REGISTRY_ROOT =
  'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry'

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

function collectRecordsWithJobId(
  value: unknown,
  out: JsonRecord[],
  depth = 0
): void {
  if (depth > 8 || out.length >= 2000) return

  const record = asRecord(value)
  if (record) {
    if (typeof record.job_id === 'string' && record.job_id.trim()) {
      out.push(record)
    }

    for (const child of Object.values(record)) {
      collectRecordsWithJobId(child, out, depth + 1)
      if (out.length >= 2000) return
    }
    return
  }

  if (Array.isArray(value)) {
    for (const child of value) {
      collectRecordsWithJobId(child, out, depth + 1)
      if (out.length >= 2000) return
    }
  }
}

function recordTimestamp(record: JsonRecord, fallbackMs: number): number {
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
      'started_at',
      'returned_at'
    ]) {
      const value = timestamps[key]
      if (typeof value === 'string') {
        const unixMatch = /^unix-ms:(\d+)$/.exec(value)
        if (unixMatch) return Number(unixMatch[1])

        const parsed = Date.parse(value)
        if (Number.isFinite(parsed)) return parsed
      }
      if (typeof value === 'number' && Number.isFinite(value)) return value
    }
  }

  for (const key of [
    'updated_at',
    'completed_at',
    'created_at',
    'started_at',
    'registered_utc'
  ]) {
    const value = record[key]
    if (typeof value !== 'string') continue

    const unixMatch = /^unix-ms:(\d+)$/.exec(value)
    if (unixMatch) return Number(unixMatch[1])

    const parsed = Date.parse(value)
    if (Number.isFinite(parsed)) return parsed
  }

  return fallbackMs
}

function normalizeJob(
  record: JsonRecord,
  sourcePath: string,
  fallbackMs: number
): IndexedJob {
  const nestedRecord = asRecord(record.record)
  const nestedEvidence = asRecord(record.evidence)

  return {
    jobId: stringField(record, 'job_id'),
    state: stringField(record, 'state', 'job_state', 'status') ||
      (nestedRecord ? stringField(nestedRecord, 'state', 'status') : ''),
    result: stringField(record, 'result') ||
      (nestedEvidence ? stringField(nestedEvidence, 'result') : ''),
    artifactId: stringField(record, 'artifact_id') ||
      (nestedRecord ? stringField(nestedRecord, 'artifact_id') : ''),
    lane: stringField(record, 'allocated_lane', 'execution_lane') ||
      (nestedRecord
        ? stringField(nestedRecord, 'allocated_lane', 'execution_lane')
        : ''),
    updatedMs: recordTimestamp(record, fallbackMs),
    sourcePath,
    record
  }
}

function loadJobs(): IndexedJob[] {
  if (!fs.existsSync(JOB_REGISTRY_ROOT)) return []

  let names: string[]
  try {
    names = fs.readdirSync(JOB_REGISTRY_ROOT)
      .filter(name => name.endsWith('.json'))
      .slice(-1500)
  } catch {
    return []
  }

  const dedupe = new Map<string, IndexedJob>()

  for (const name of names) {
    const filePath = path.join(JOB_REGISTRY_ROOT, name)

    let stat: fs.Stats
    let data: unknown

    try {
      stat = fs.statSync(filePath)
      if (!stat.isFile() || stat.size > 4 * 1024 * 1024) continue
      data = JSON.parse(fs.readFileSync(filePath, 'utf-8')) as unknown
    } catch {
      continue
    }

    const records: JsonRecord[] = []
    collectRecordsWithJobId(data, records)

    for (const record of records) {
      const jobId = stringField(record, 'job_id')
      if (!jobId || !JOB_ID_PATTERN.test(jobId)) continue

      const candidate = normalizeJob(record, filePath, stat.mtimeMs)
      const existing = dedupe.get(jobId)

      if (!existing || candidate.updatedMs >= existing.updatedMs) {
        dedupe.set(jobId, candidate)
      }
    }
  }

  return [...dedupe.values()]
    .sort((a, b) => b.updatedMs - a.updatedMs)
}

function parseLimit(
  raw: string | undefined,
  usage: string
): number | VxsCommandDispatchResult {
  const value = (raw ?? '20').trim()
  const limit = Number.parseInt(value, 10)

  if (
    !Number.isFinite(limit) ||
    limit < 1 ||
    limit > 100 ||
    String(limit) !== value
  ) {
    return immediateError(
      `Invalid limit '${value}'.`,
      [`Usage: ${usage}`, 'Allowed range: 1-100']
    )
  }

  return limit
}

function renderJobRow(job: IndexedJob): string {
  const stamp = new Date(job.updatedMs).toISOString()
  return [
    stamp,
    job.state || job.result || '(unknown)',
    job.lane || '-',
    job.jobId,
    job.artifactId || '-'
  ].join(' | ')
}

function jobsCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const parsed = parseLimit(args[0], 'vxs jobs [1-100]')
  if (typeof parsed !== 'number') return parsed

  const jobs = loadJobs().slice(0, parsed)

  return {
    kind: 'immediate',
    output: [
      'VXS JOBS',
      `Registry Root: ${JOB_REGISTRY_ROOT}`,
      `Showing: ${jobs.length}`,
      '',
      ...(jobs.length ? jobs.map(renderJobRow) : ['(no durable jobs found)']),
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function isFailedJob(job: IndexedJob): boolean {
  const haystack = [
    job.state,
    job.result,
    stringField(job.record, 'error', 'last_error', 'failure_reason')
  ].join(' ').toLowerCase()

  return (
    haystack.includes('fail') ||
    haystack.includes('reject') ||
    haystack.includes('rollback') ||
    haystack.includes('error') ||
    haystack.includes('conflict')
  )
}

function failuresCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const parsed = parseLimit(args[0], 'vxs failures [1-100]')
  if (typeof parsed !== 'number') return parsed

  const jobs = loadJobs()
    .filter(isFailedJob)
    .slice(0, parsed)

  return {
    kind: 'immediate',
    output: [
      'VXS FAILURES',
      `Showing: ${jobs.length}`,
      '',
      ...(jobs.length ? jobs.map(renderJobRow) : ['(no failed jobs found)']),
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function timelineEntries(
  record: JsonRecord
): Array<{ label: string; value: string }> {
  const entries: Array<{ label: string; value: string }> = []

  function add(label: string, value: unknown): void {
    if (typeof value === 'string' && value.trim()) {
      entries.push({ label, value: value.trim() })
      return
    }

    if (typeof value === 'number' && Number.isFinite(value)) {
      entries.push({ label, value: String(value) })
    }
  }

  const timestamps = asRecord(record.timestamps)
  if (timestamps) {
    for (const key of [
      'created_at',
      'registered_at',
      'started_at',
      'completed_at',
      'returned_at'
    ]) {
      add(`timestamps.${key}`, timestamps[key])
    }
  }

  for (const key of [
    'created_at',
    'registered_utc',
    'registration_attempt_utc',
    'registered_utc',
    'started_at',
    'completed_at',
    'returned_at',
    'updated_at',
    'created_ms',
    'started_ms',
    'finished_ms',
    'completed_ms',
    'updated_ms'
  ]) {
    add(key, record[key])
  }

  return entries
}

function timelineCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const jobId = (args[0] ?? '').trim()

  if (!jobId) {
    return immediateError(
      'Job ID is required.',
      ['Usage: vxs timeline <job-id>']
    )
  }

  if (!JOB_ID_PATTERN.test(jobId)) {
    return immediateError('Job ID contains unsupported characters.')
  }

  const job = loadJobs().find(value => value.jobId === jobId)

  if (!job) {
    return immediateError(
      `Job was not found in the durable registry: ${jobId}`,
      ['Try: vxs jobs 100']
    )
  }

  const entries = timelineEntries(job.record)

  const rows = [
    'VXS TIMELINE',
    `Job ID: ${job.jobId}`,
    `Artifact: ${job.artifactId || '(unknown)'}`,
    `State: ${job.state || '(unknown)'}`,
    `Result: ${job.result || '(unknown)'}`,
    `Lane: ${job.lane || '(none)'}`,
    `Registry Source: ${job.sourcePath}`,
    '',
    'Timeline:'
  ]

  if (entries.length) {
    for (const entry of entries) {
      rows.push(`  ${entry.label}: ${entry.value}`)
    }
  } else {
    rows.push('  (no explicit timestamp fields found)')
    rows.push(`  registry_file_mtime: ${new Date(job.updatedMs).toISOString()}`)
  }

  rows.push('')
  rows.push('TIMELINE_MUTATION=NONE')
  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsJobIntelligenceCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'jobs',
      aliases: ['job-list'],
      usage: 'vxs jobs [1-100]',
      summary: 'List recent durable Workstation jobs',
      execute: jobsCommand
    },
    {
      name: 'failures',
      aliases: ['failed-jobs'],
      usage: 'vxs failures [1-100]',
      summary: 'List recent failed/rejected Workstation jobs',
      execute: failuresCommand
    },
    {
      name: 'timeline',
      aliases: ['job-timeline'],
      usage: 'vxs timeline <job-id>',
      summary: 'Show durable lifecycle timestamps for a Job',
      execute: timelineCommand
    }
  ]
}
