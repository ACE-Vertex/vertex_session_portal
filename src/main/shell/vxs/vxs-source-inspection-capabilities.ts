// VXS_SOURCE_INSPECTION_CAPABILITY_PACK_000013
import { createHash } from 'node:crypto'
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
    output: [
      `ERROR: ${message}`,
      ...hints,
      ''
    ].map(line).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

function resolveInsideWorkspace(
  workspaceRoot: string,
  requested: string
): string | null {
  const value = requested.trim()
  if (!value) return workspaceRoot

  const resolved = path.resolve(workspaceRoot, value)
  const relative = path.relative(workspaceRoot, resolved)

  if (
    relative === '' ||
    (!relative.startsWith('..') && !path.isAbsolute(relative))
  ) {
    return resolved
  }

  return null
}

const SEARCH_SKIP = new Set([
  '.git',
  'node_modules',
  'target',
  'dist',
  'out',
  'coverage',
  '.vite',
  '__pycache__',
  '.venv',
  'venv',
  'runtime'
])

function findCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const pattern = (args[0] ?? '').trim()
  const relativeRoot = (args[1] ?? '.').trim()

  if (!pattern) {
    return immediateError(
      'Search pattern is required.',
      ['Usage: vxs find <text> [path]']
    )
  }

  if (pattern.length > 200) {
    return immediateError('Search pattern is too long.')
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const searchRoot = resolveInsideWorkspace(workspace.root, relativeRoot)

  if (!searchRoot) {
    return immediateError('Search path escapes the detected workspace.')
  }

  if (!fs.existsSync(searchRoot)) {
    return immediateError(`Search path does not exist: ${relativeRoot}`)
  }

  const hits: string[] = []
  let scannedFiles = 0
  const maxFiles = 4000
  const maxHits = 120
  const maxFileBytes = 2 * 1024 * 1024
  const needle = pattern.toLowerCase()

  function scanFile(filePath: string): void {
    if (scannedFiles >= maxFiles || hits.length >= maxHits) return

    let stat: fs.Stats
    try {
      stat = fs.statSync(filePath)
    } catch {
      return
    }

    if (!stat.isFile() || stat.size > maxFileBytes) return
    scannedFiles += 1

    let text: string
    try {
      text = fs.readFileSync(filePath, 'utf-8')
    } catch {
      return
    }

    const rows = text.split(/\r?\n/)
    for (let index = 0; index < rows.length; index += 1) {
      if (!rows[index].toLowerCase().includes(needle)) continue

      const rel = path.relative(workspace.root, filePath)
      hits.push(`${rel}:${index + 1}: ${rows[index].slice(0, 500)}`)
      if (hits.length >= maxHits) return
    }
  }

  function walk(current: string): void {
    if (scannedFiles >= maxFiles || hits.length >= maxHits) return

    let stat: fs.Stats
    try {
      stat = fs.statSync(current)
    } catch {
      return
    }

    if (stat.isFile()) {
      scanFile(current)
      return
    }

    if (!stat.isDirectory()) return

    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(current, { withFileTypes: true })
    } catch {
      return
    }

    for (const entry of entries) {
      if (hits.length >= maxHits || scannedFiles >= maxFiles) return
      if (entry.isDirectory() && SEARCH_SKIP.has(entry.name)) continue
      walk(path.join(current, entry.name))
    }
  }

  walk(searchRoot)

  const rows = [
    'VXS FIND',
    `Pattern: ${pattern}`,
    `Root: ${searchRoot}`,
    `Files Scanned: ${scannedFiles}`,
    `Matches: ${hits.length}`,
    '',
    ...hits
  ]

  if (hits.length >= maxHits) {
    rows.push('')
    rows.push(`TRUNCATED at ${maxHits} matches.`)
  }

  if (scannedFiles >= maxFiles) {
    rows.push('')
    rows.push(`FILE SCAN LIMIT reached at ${maxFiles}.`)
  }

  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function inspectCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '').trim()
  const rawStart = args[1] ?? '1'
  const rawCount = args[2] ?? '120'

  if (!requested) {
    return immediateError(
      'File path is required.',
      ['Usage: vxs inspect <path> [start-line] [count]']
    )
  }

  const start = Number.parseInt(rawStart, 10)
  const count = Number.parseInt(rawCount, 10)

  if (!Number.isFinite(start) || start < 1) {
    return immediateError(`Invalid start line '${rawStart}'.`)
  }

  if (!Number.isFinite(count) || count < 1 || count > 400) {
    return immediateError(
      `Invalid line count '${rawCount}'.`,
      ['Allowed range: 1-400']
    )
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const filePath = resolveInsideWorkspace(workspace.root, requested)

  if (!filePath) {
    return immediateError('Requested file escapes the detected workspace.')
  }

  let stat: fs.Stats
  try {
    stat = fs.statSync(filePath)
  } catch {
    return immediateError(`File not found: ${requested}`)
  }

  if (!stat.isFile()) {
    return immediateError(`Path is not a file: ${requested}`)
  }

  if (stat.size > 4 * 1024 * 1024) {
    return immediateError(
      'File is larger than the 4 MiB inspection limit.',
      ['Use vxs find for bounded search instead.']
    )
  }

  let text: string
  try {
    text = fs.readFileSync(filePath, 'utf-8')
  } catch {
    return immediateError(`File could not be read as UTF-8 text: ${requested}`)
  }

  const fileLines = text.split(/\r?\n/)
  const from = Math.min(start - 1, fileLines.length)
  const to = Math.min(from + count, fileLines.length)

  const rows = [
    'VXS INSPECT',
    `File: ${path.relative(workspace.root, filePath)}`,
    `Lines: ${from + 1}-${to} / ${fileLines.length}`,
    ''
  ]

  for (let index = from; index < to; index += 1) {
    rows.push(`${String(index + 1).padStart(6, '0')}| ${fileLines[index]}`)
  }

  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function hashCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '').trim()

  if (!requested) {
    return immediateError(
      'File path is required.',
      ['Usage: vxs hash <path>']
    )
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const filePath = resolveInsideWorkspace(workspace.root, requested)

  if (!filePath) {
    return immediateError('Requested file escapes the detected workspace.')
  }

  let bytes: Buffer
  try {
    const stat = fs.statSync(filePath)
    if (!stat.isFile()) {
      return immediateError(`Path is not a file: ${requested}`)
    }
    if (stat.size > 128 * 1024 * 1024) {
      return immediateError('File exceeds the 128 MiB hash limit.')
    }
    bytes = fs.readFileSync(filePath)
  } catch {
    return immediateError(`File could not be read: ${requested}`)
  }

  const digest = createHash('sha256').update(bytes).digest('hex')

  return {
    kind: 'immediate',
    output: [
      'VXS HASH',
      `File: ${path.relative(workspace.root, filePath)}`,
      `SHA256: ${digest}`,
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function statCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '.').trim()
  const workspace = detectVxsWorkspace(context.cwd)
  const target = resolveInsideWorkspace(workspace.root, requested)

  if (!target) {
    return immediateError('Requested path escapes the detected workspace.')
  }

  let stat: fs.Stats
  try {
    stat = fs.statSync(target)
  } catch {
    return immediateError(`Path not found: ${requested}`)
  }

  return {
    kind: 'immediate',
    output: [
      'VXS STAT',
      `Path: ${path.relative(workspace.root, target) || '.'}`,
      `Type: ${stat.isDirectory() ? 'directory' : stat.isFile() ? 'file' : 'other'}`,
      `Size: ${stat.size}`,
      `Modified: ${stat.mtime.toISOString()}`,
      `Created: ${stat.birthtime.toISOString()}`,
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsSourceInspectionCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'find',
      aliases: ['grep'],
      usage: 'vxs find <text> [path]',
      summary: 'Search workspace text with bounded reads',
      execute: findCommand
    },
    {
      name: 'inspect',
      aliases: ['cat'],
      usage: 'vxs inspect <path> [start-line] [count]',
      summary: 'Read bounded line ranges from workspace files',
      execute: inspectCommand
    },
    {
      name: 'hash',
      aliases: ['sha256'],
      usage: 'vxs hash <path>',
      summary: 'Compute SHA256 for a workspace file',
      execute: hashCommand
    },
    {
      name: 'stat',
      aliases: [],
      usage: 'vxs stat <path>',
      summary: 'Show workspace file or directory metadata',
      execute: statCommand
    }
  ]
}
