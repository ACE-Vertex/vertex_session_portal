// VXS_OBSERVABILITY_CAPABILITY_PACK_000012
import * as fs from 'node:fs'
import * as os from 'node:os'
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
    output: [
      `ERROR: ${message}`,
      ...hints,
      ''
    ].map(line).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

function safeReadText(filePath: string, maxBytes = 512 * 1024): string | null {
  try {
    const stat = fs.statSync(filePath)
    if (!stat.isFile()) return null

    const fd = fs.openSync(filePath, 'r')
    try {
      const size = Math.min(stat.size, maxBytes)
      const start = Math.max(0, stat.size - size)
      const buffer = Buffer.alloc(size)
      fs.readSync(fd, buffer, 0, size, start)
      return buffer.toString('utf-8')
    } finally {
      fs.closeSync(fd)
    }
  } catch {
    return null
  }
}

function lastLines(text: string, count: number): string[] {
  return text
    .split(/\r?\n/)
    .filter((value, index, values) => value.length > 0 || index < values.length - 1)
    .slice(-count)
}

function portalLogRoots(): string[] {
  const appData = process.env.APPDATA
  const localAppData = process.env.LOCALAPPDATA
  const roots: string[] = []

  if (appData) {
    roots.push(
      path.join(appData, 'vertex-session-portal'),
      path.join(appData, 'Vertex Session Portal')
    )
  }

  if (localAppData) {
    roots.push(
      path.join(localAppData, 'vertex-session-portal'),
      path.join(localAppData, 'VertexSessionPortal')
    )
  }

  return roots
}

function collectRecentLogFiles(
  roots: string[],
  limit = 30
): Array<{ path: string; mtimeMs: number; size: number }> {
  const rows: Array<{ path: string; mtimeMs: number; size: number }> = []
  const allowed = new Set(['.log', '.txt', '.jsonl', '.ndjson'])

  function walk(dir: string, depth: number): void {
    if (depth > 3 || rows.length > 500) return

    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
    } catch {
      return
    }

    for (const entry of entries) {
      const full = path.join(dir, entry.name)

      if (entry.isDirectory()) {
        if (['node_modules', '.git', 'target'].includes(entry.name)) continue
        walk(full, depth + 1)
        continue
      }

      if (!entry.isFile()) continue
      if (!allowed.has(path.extname(entry.name).toLowerCase())) continue

      try {
        const stat = fs.statSync(full)
        rows.push({ path: full, mtimeMs: stat.mtimeMs, size: stat.size })
      } catch {
        // Observation only; unreadable files are skipped.
      }
    }
  }

  for (const root of roots) {
    if (fs.existsSync(root)) walk(root, 0)
  }

  return rows
    .sort((a, b) => b.mtimeMs - a.mtimeMs)
    .slice(0, limit)
}

function logsCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const scope = (args[0] ?? 'portal').toLowerCase()
  const rawCount = args[1] ?? '80'
  const count = Number.parseInt(rawCount, 10)

  if (!Number.isFinite(count) || count < 10 || count > 300) {
    return immediateError(
      `Invalid line count '${rawCount}'.`,
      ['Usage: vxs logs [portal|workstation] [10-300]']
    )
  }

  let roots: string[]

  if (scope === 'portal') {
    roots = portalLogRoots()
  } else if (scope === 'workstation') {
    roots = [
      'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime'
    ]
  } else {
    return immediateError(
      `Unknown log scope '${scope}'.`,
      ['Usage: vxs logs [portal|workstation] [10-300]']
    )
  }

  const files = collectRecentLogFiles(roots, 12)

  if (!files.length) {
    return immediateError(
      `No readable ${scope} log files were found.`
    )
  }

  const rows: string[] = [
    'VXS LOGS',
    `Scope: ${scope}`,
    `Tail Lines: ${count}`,
    ''
  ]

  for (const item of files.slice(0, 5)) {
    rows.push(`FILE: ${item.path}`)
    rows.push(`SIZE: ${item.size}`)

    const text = safeReadText(item.path)
    if (text === null) {
      rows.push('(unreadable)')
    } else {
      rows.push(...lastLines(text, count))
    }

    rows.push('')
  }

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

const JOB_ID_PATTERN = /^[A-Za-z0-9._:-]+$/

function traceCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const jobId = (args[0] ?? '').trim()

  if (!jobId) {
    return immediateError(
      'Job ID is required.',
      ['Usage: vxs trace <job-id>']
    )
  }

  if (!JOB_ID_PATTERN.test(jobId)) {
    return immediateError('Job ID contains unsupported characters.')
  }

  const portalRoots = portalLogRoots()
  const workstationRoot =
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime'

  const searchRoots = [
    ...portalRoots,
    workstationRoot
  ]

  const files = collectRecentLogFiles(searchRoots, 80)
  const hits: Array<{ path: string; lines: string[] }> = []

  for (const item of files) {
    const text = safeReadText(item.path, 2 * 1024 * 1024)
    if (!text || !text.includes(jobId)) continue

    const matched = text
      .split(/\r?\n/)
      .filter(value => value.includes(jobId))
      .slice(-20)

    hits.push({ path: item.path, lines: matched })
    if (hits.length >= 12) break
  }

  const registryRoot =
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry'

  if (fs.existsSync(registryRoot)) {
    let registryFiles: string[] = []
    try {
      registryFiles = fs.readdirSync(registryRoot)
        .filter(name => name.endsWith('.json'))
        .map(name => path.join(registryRoot, name))
        .slice(-200)
    } catch {
      registryFiles = []
    }

    for (const filePath of registryFiles) {
      const text = safeReadText(filePath, 2 * 1024 * 1024)
      if (!text || !text.includes(jobId)) continue

      const matched = text
        .split(/\r?\n/)
        .filter(value => value.includes(jobId))
        .slice(-20)

      hits.push({ path: filePath, lines: matched })
      if (hits.length >= 16) break
    }
  }

  const rows: string[] = [
    'VXS TRACE',
    `Job ID: ${jobId}`,
    `Matches: ${hits.length}`,
    ''
  ]

  if (!hits.length) {
    rows.push('No local trace matches were found.')
    rows.push('')
  } else {
    for (const hit of hits) {
      rows.push(`FILE: ${hit.path}`)
      rows.push(...hit.lines)
      rows.push('')
    }
  }

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsObservabilityCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'logs',
      aliases: [],
      usage: 'vxs logs [portal|workstation] [10-300]',
      summary: 'Tail bounded local Vertex logs',
      execute: logsCommand
    },
    {
      name: 'trace',
      aliases: ['job-trace'],
      usage: 'vxs trace <job-id>',
      summary: 'Find local Portal/Workstation traces for a Job',
      execute: traceCommand
    }
  ]
}
