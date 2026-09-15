// VXS_CHANGE_INTELLIGENCE_CAPABILITY_PACK_000014
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

function runGit(
  cwd: string,
  args: string[]
): { ok: boolean; stdout: string; stderr: string } {
  try {
    const result = spawnSync(
      'git',
      args,
      {
        cwd,
        windowsHide: true,
        shell: false,
        encoding: 'utf-8',
        timeout: 8_000
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

function changedCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  if (!workspace.git) {
    return immediateError(
      'Git repository was not detected.',
      [`Workspace Root: ${workspace.root}`]
    )
  }

  const result = runGit(
    workspace.root,
    ['status', '--short', '--untracked-files=normal']
  )

  if (!result.ok) {
    return immediateError('git status failed.', result.stderr ? [result.stderr] : [])
  }

  const rows = [
    'VXS CHANGED',
    `Workspace Root: ${workspace.root}`,
    ''
  ]

  if (!result.stdout) {
    rows.push('(clean working tree)')
  } else {
    rows.push(...result.stdout.split(/\r?\n/).slice(0, 300))
  }

  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function diffstatCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  if (!workspace.git) {
    return immediateError(
      'Git repository was not detected.',
      [`Workspace Root: ${workspace.root}`]
    )
  }

  const worktree = runGit(workspace.root, ['diff', '--stat'])
  const staged = runGit(workspace.root, ['diff', '--cached', '--stat'])

  if (!worktree.ok || !staged.ok) {
    return immediateError(
      'git diff --stat failed.',
      [
        ...(worktree.stderr ? [worktree.stderr] : []),
        ...(staged.stderr ? [staged.stderr] : [])
      ]
    )
  }

  const rows = [
    'VXS DIFFSTAT',
    `Workspace Root: ${workspace.root}`,
    '',
    'WORKTREE:',
    ...(worktree.stdout ? worktree.stdout.split(/\r?\n/) : ['(none)']),
    '',
    'STAGED:',
    ...(staged.stdout ? staged.stdout.split(/\r?\n/) : ['(none)']),
    ''
  ]

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
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

const SOURCE_EXTENSIONS = new Set([
  '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
  '.rs', '.py', '.go', '.java', '.kt', '.kts',
  '.cs', '.cpp', '.cc', '.c', '.h', '.hpp',
  '.vue', '.svelte', '.json', '.toml', '.yaml',
  '.yml', '.md', '.ps1', '.sh'
])

function walkSourceFiles(
  root: string,
  callback: (filePath: string) => boolean | void
): void {
  let scanned = 0
  const maxFiles = 5000

  function walk(current: string): boolean {
    if (scanned >= maxFiles) return false

    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(current, { withFileTypes: true })
    } catch {
      return true
    }

    for (const entry of entries) {
      if (scanned >= maxFiles) return false

      const full = path.join(current, entry.name)

      if (entry.isDirectory()) {
        if (SEARCH_SKIP.has(entry.name)) continue
        if (!walk(full)) return false
        continue
      }

      if (!entry.isFile()) continue
      if (!SOURCE_EXTENSIONS.has(path.extname(entry.name).toLowerCase())) continue

      scanned += 1
      const keepGoing = callback(full)
      if (keepGoing === false) return false
    }

    return true
  }

  walk(root)
}

function refsCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const symbol = (args[0] ?? '').trim()

  if (!symbol) {
    return immediateError(
      'Symbol is required.',
      ['Usage: vxs refs <symbol>']
    )
  }

  if (!/^[A-Za-z_$][A-Za-z0-9_$.:/-]{0,127}$/.test(symbol)) {
    return immediateError('Symbol contains unsupported characters.')
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const needle = symbol.toLowerCase()
  const hits: string[] = []
  const maxHits = 120
  const maxFileBytes = 2 * 1024 * 1024

  walkSourceFiles(workspace.root, filePath => {
    if (hits.length >= maxHits) return false

    let stat: fs.Stats
    try {
      stat = fs.statSync(filePath)
    } catch {
      return
    }

    if (stat.size > maxFileBytes) return

    let text: string
    try {
      text = fs.readFileSync(filePath, 'utf-8')
    } catch {
      return
    }

    const rows = text.split(/\r?\n/)
    for (let index = 0; index < rows.length; index += 1) {
      if (!rows[index].toLowerCase().includes(needle)) continue

      hits.push(
        `${path.relative(workspace.root, filePath)}:${index + 1}: ${rows[index].slice(0, 500)}`
      )

      if (hits.length >= maxHits) return false
    }
  })

  const rows = [
    'VXS REFS',
    `Symbol: ${symbol}`,
    `Matches: ${hits.length}`,
    '',
    ...hits
  ]

  if (hits.length >= maxHits) {
    rows.push('')
    rows.push(`TRUNCATED at ${maxHits} matches.`)
  }

  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function resolveInsideWorkspace(
  workspaceRoot: string,
  requested: string
): string | null {
  const value = requested.trim()
  const resolved = path.resolve(workspaceRoot, value || '.')
  const relative = path.relative(workspaceRoot, resolved)

  if (
    relative === '' ||
    (!relative.startsWith('..') && !path.isAbsolute(relative))
  ) {
    return resolved
  }

  return null
}

function todoCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '.').trim()
  const workspace = detectVxsWorkspace(context.cwd)
  const root = resolveInsideWorkspace(workspace.root, requested)

  if (!root) {
    return immediateError('Requested path escapes the detected workspace.')
  }

  if (!fs.existsSync(root)) {
    return immediateError(`Path not found: ${requested}`)
  }

  const tokens = ['TODO', 'FIXME', 'HACK', 'XXX']
  const hits: string[] = []
  const maxHits = 120

  const inspectFile = (filePath: string): boolean | void => {
    if (hits.length >= maxHits) return false

    let stat: fs.Stats
    try {
      stat = fs.statSync(filePath)
    } catch {
      return
    }

    if (!stat.isFile() || stat.size > 2 * 1024 * 1024) return

    let text: string
    try {
      text = fs.readFileSync(filePath, 'utf-8')
    } catch {
      return
    }

    const rows = text.split(/\r?\n/)
    for (let index = 0; index < rows.length; index += 1) {
      if (!tokens.some(token => rows[index].includes(token))) continue

      hits.push(
        `${path.relative(workspace.root, filePath)}:${index + 1}: ${rows[index].slice(0, 500)}`
      )

      if (hits.length >= maxHits) return false
    }
  }

  try {
    const stat = fs.statSync(root)
    if (stat.isFile()) {
      inspectFile(root)
    } else if (stat.isDirectory()) {
      walkSourceFiles(root, inspectFile)
    }
  } catch {
    return immediateError(`Unable to inspect: ${requested}`)
  }

  const rows = [
    'VXS TODO',
    `Root: ${path.relative(workspace.root, root) || '.'}`,
    `Matches: ${hits.length}`,
    '',
    ...hits
  ]

  if (hits.length >= maxHits) {
    rows.push('')
    rows.push(`TRUNCATED at ${maxHits} matches.`)
  }

  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsChangeIntelligenceCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'changed',
      aliases: [],
      usage: 'vxs changed',
      summary: 'Show changed and untracked files',
      execute: changedCommand
    },
    {
      name: 'diffstat',
      aliases: [],
      usage: 'vxs diffstat',
      summary: 'Show staged and worktree diff statistics',
      execute: diffstatCommand
    },
    {
      name: 'refs',
      aliases: [],
      usage: 'vxs refs <symbol>',
      summary: 'Find bounded source references to a symbol',
      execute: refsCommand
    },
    {
      name: 'todo',
      aliases: [],
      usage: 'vxs todo [path]',
      summary: 'Find TODO/FIXME/HACK/XXX markers',
      execute: todoCommand
    }
  ]
}
