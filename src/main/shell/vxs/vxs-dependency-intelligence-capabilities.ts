// VXS_DEPENDENCY_INTELLIGENCE_CAPABILITY_PACK_000015
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

function resolveInsideWorkspace(
  workspaceRoot: string,
  requested: string
): string | null {
  const resolved = path.resolve(workspaceRoot, requested)
  const relative = path.relative(workspaceRoot, resolved)

  if (
    relative === '' ||
    (!relative.startsWith('..') && !path.isAbsolute(relative))
  ) {
    return resolved
  }

  return null
}

const SOURCE_EXTENSIONS = new Set([
  '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
  '.vue', '.svelte', '.rs', '.py', '.go', '.java',
  '.kt', '.kts', '.cs'
])

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

function readTextFile(filePath: string, maxBytes = 2 * 1024 * 1024): string | null {
  try {
    const stat = fs.statSync(filePath)
    if (!stat.isFile() || stat.size > maxBytes) return null
    return fs.readFileSync(filePath, 'utf-8')
  } catch {
    return null
  }
}

function extractImports(text: string): string[] {
  const imports = new Set<string>()

  const patterns = [
    /\bimport\s+(?:type\s+)?(?:[^'"]+?\s+from\s+)?['"]([^'"]+)['"]/g,
    /\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\bexport\s+(?:type\s+)?(?:[^'"]+?\s+from\s+)?['"]([^'"]+)['"]/g
  ]

  for (const pattern of patterns) {
    let match: RegExpExecArray | null
    while ((match = pattern.exec(text)) !== null) {
      if (match[1]) imports.add(match[1])
      if (imports.size >= 200) break
    }
  }

  return [...imports].sort()
}

function importsCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '').trim()

  if (!requested) {
    return immediateError(
      'File path is required.',
      ['Usage: vxs imports <path>']
    )
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const filePath = resolveInsideWorkspace(workspace.root, requested)

  if (!filePath) {
    return immediateError('Requested file escapes the detected workspace.')
  }

  const text = readTextFile(filePath)

  if (text === null) {
    return immediateError(
      'File is missing, unreadable, or larger than 2 MiB.',
      [`Path: ${requested}`]
    )
  }

  const imports = extractImports(text)

  return {
    kind: 'immediate',
    output: [
      'VXS IMPORTS',
      `File: ${path.relative(workspace.root, filePath)}`,
      `Imports: ${imports.length}`,
      '',
      ...(imports.length ? imports : ['(none detected)']),
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function moduleCandidates(
  workspaceRoot: string,
  filePath: string
): string[] {
  const relative = path
    .relative(workspaceRoot, filePath)
    .replace(/\\/g, '/')

  const noExt = relative.replace(/\.[^.\/]+$/, '')
  const base = path.basename(noExt)
  const withDot = noExt.startsWith('.') ? noExt : `./${noExt}`

  const values = new Set<string>([
    relative,
    noExt,
    withDot,
    base,
    `./${base}`
  ])

  if (base === 'index') {
    const parent = path.dirname(noExt).replace(/\\/g, '/')
    const parentBase = path.basename(parent)
    values.add(parent)
    values.add(`./${parent}`)
    values.add(parentBase)
    values.add(`./${parentBase}`)
  }

  return [...values].filter(Boolean)
}

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
      if (callback(full) === false) return false
    }

    return true
  }

  walk(root)
}

function findDependents(
  workspaceRoot: string,
  targetPath: string
): string[] {
  const targetNormalized = path.resolve(targetPath)
  const candidates = moduleCandidates(workspaceRoot, targetPath)
    .map(value => value.toLowerCase())

  const hits: string[] = []
  const maxHits = 120

  walkSourceFiles(workspaceRoot, filePath => {
    if (hits.length >= maxHits) return false
    if (path.resolve(filePath) === targetNormalized) return

    const text = readTextFile(filePath)
    if (text === null) return

    const imports = extractImports(text)
    const lowerImports = imports.map(value => value.toLowerCase())

    const matched = lowerImports.some(specifier =>
      candidates.some(candidate =>
        specifier === candidate ||
        specifier.endsWith('/' + candidate.replace(/^\.\//, '')) ||
        candidate.endsWith('/' + specifier.replace(/^\.\//, ''))
      )
    )

    if (matched) {
      hits.push(path.relative(workspaceRoot, filePath))
    }
  })

  return hits.sort()
}

function dependentsCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '').trim()

  if (!requested) {
    return immediateError(
      'File path is required.',
      ['Usage: vxs dependents <path>']
    )
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const filePath = resolveInsideWorkspace(workspace.root, requested)

  if (!filePath) {
    return immediateError('Requested file escapes the detected workspace.')
  }

  if (!fs.existsSync(filePath)) {
    return immediateError(`File not found: ${requested}`)
  }

  const hits = findDependents(workspace.root, filePath)

  const rows = [
    'VXS DEPENDENTS',
    `File: ${path.relative(workspace.root, filePath)}`,
    `Direct Dependents: ${hits.length}`,
    '',
    ...(hits.length ? hits : ['(none detected)']),
    ''
  ]

  if (hits.length >= 120) {
    rows.splice(rows.length - 1, 0, 'TRUNCATED at 120 matches.')
  }

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function impactCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '').trim()

  if (!requested) {
    return immediateError(
      'File path is required.',
      ['Usage: vxs impact <path>']
    )
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const filePath = resolveInsideWorkspace(workspace.root, requested)

  if (!filePath) {
    return immediateError('Requested file escapes the detected workspace.')
  }

  const text = readTextFile(filePath)
  if (text === null) {
    return immediateError(
      'File is missing, unreadable, or larger than 2 MiB.',
      [`Path: ${requested}`]
    )
  }

  const imports = extractImports(text)
  const dependents = findDependents(workspace.root, filePath)

  let size = 0
  let modified = 'unknown'
  try {
    const stat = fs.statSync(filePath)
    size = stat.size
    modified = stat.mtime.toISOString()
  } catch {
    // Already proven readable above.
  }

  let impact = 'LOW'
  if (dependents.length >= 20) impact = 'HIGH'
  else if (dependents.length >= 5) impact = 'MEDIUM'

  return {
    kind: 'immediate',
    output: [
      'VXS IMPACT',
      `File: ${path.relative(workspace.root, filePath)}`,
      `Size: ${size}`,
      `Modified: ${modified}`,
      `Direct Imports: ${imports.length}`,
      `Direct Dependents: ${dependents.length}`,
      `Impact Hint: ${impact}`,
      '',
      'Top Dependents:',
      ...(dependents.slice(0, 20).length
        ? dependents.slice(0, 20).map(value => `  ${value}`)
        : ['  (none detected)']),
      '',
      'Impact Hint is a bounded static heuristic, not an execution guarantee.',
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

export function createVxsDependencyIntelligenceCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'imports',
      aliases: [],
      usage: 'vxs imports <path>',
      summary: 'List detected imports for a workspace source file',
      execute: importsCommand
    },
    {
      name: 'dependents',
      aliases: [],
      usage: 'vxs dependents <path>',
      summary: 'Find bounded direct source dependents',
      execute: dependentsCommand
    },
    {
      name: 'impact',
      aliases: [],
      usage: 'vxs impact <path>',
      summary: 'Summarize bounded static change impact',
      execute: impactCommand
    }
  ]
}
