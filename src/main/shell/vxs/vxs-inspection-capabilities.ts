// VXS_INSPECTION_CAPABILITY_PACK_000011
import { spawnSync } from 'node:child_process'
import * as fs from 'node:fs'
import * as path from 'node:path'
import {
  detectVxsWorkspace,
  type VxsWorkspaceInfo
} from './vxs-workspace-detector'
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

function envCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)
  const pathEntries = (process.env.PATH ?? '')
    .split(path.delimiter)
    .filter(Boolean)

  const rows = [
    'VXS ENV · SAFE SUMMARY',
    `Platform: ${process.platform}`,
    `Architecture: ${process.arch}`,
    `Node: ${process.versions.node}`,
    `PID: ${process.pid}`,
    `CWD: ${workspace.cwd}`,
    `Workspace Root: ${workspace.root}`,
    `Workspace Type: ${workspace.kind}`,
    `Package Manager: ${workspace.packageManager ?? 'not detected'}`,
    `Compatibility Backend: ${context.compatibilityBackend}`,
    `PATH Entries: ${pathEntries.length}`,
    '',
    'Sensitive environment variable values are intentionally not displayed.',
    ''
  ]

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function whichCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const tool = (args[0] ?? '').trim()

  if (!tool) {
    return immediateError(
      'Tool name is required.',
      ['Usage: vxs which <tool>']
    )
  }

  if (!/^[A-Za-z0-9._+-]+$/.test(tool)) {
    return immediateError(
      `Invalid tool name '${tool}'.`
    )
  }

  const resolver = process.platform === 'win32' ? 'where.exe' : 'which'

  try {
    const result = spawnSync(
      resolver,
      [tool],
      {
        windowsHide: true,
        shell: false,
        encoding: 'utf-8',
        timeout: 3_000
      }
    )

    const stdout = (result.stdout ?? '').trim()
    const stderr = (result.stderr ?? '').trim()

    if (result.status !== 0 || !stdout) {
      return immediateError(
        `Tool '${tool}' was not found.`,
        stderr ? [stderr] : []
      )
    }

    return {
      kind: 'immediate',
      output: [
        'VXS WHICH',
        `Tool: ${tool}`,
        ...stdout.split(/\r?\n/).map(value => `Path: ${value}`),
        ''
      ].map(line).join(''),
      exitCode: 0,
      stream: 'system'
    }
  } catch (error) {
    return immediateError(
      `Unable to resolve '${tool}'.`,
      [error instanceof Error ? error.message : String(error)]
    )
  }
}

const TREE_SKIP = new Set([
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

function treeCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)
  const rawDepth = (args[0] ?? '2').trim()
  const depth = Number.parseInt(rawDepth, 10)

  if (!Number.isFinite(depth) || depth < 1 || depth > 4) {
    return immediateError(
      `Invalid tree depth '${rawDepth}'.`,
      ['Usage: vxs tree [1-4]']
    )
  }

  const rows: string[] = [
    'VXS TREE',
    `Root: ${workspace.root}`,
    `Depth: ${depth}`,
    ''
  ]

  let emitted = 0
  const maxEntries = 300

  function walk(dir: string, level: number): void {
    if (level > depth || emitted >= maxEntries) return

    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true })
        .filter(entry => !TREE_SKIP.has(entry.name))
        .sort((a, b) => {
          if (a.isDirectory() !== b.isDirectory()) {
            return a.isDirectory() ? -1 : 1
          }
          return a.name.localeCompare(b.name)
        })
    } catch {
      return
    }

    for (const entry of entries) {
      if (emitted >= maxEntries) return

      const prefix = '  '.repeat(level - 1)
      rows.push(
        `${prefix}${entry.isDirectory() ? '[D]' : '[F]'} ${entry.name}`
      )
      emitted += 1

      if (entry.isDirectory() && level < depth) {
        walk(path.join(dir, entry.name), level + 1)
      }
    }
  }

  walk(workspace.root, 1)

  if (emitted >= maxEntries) {
    rows.push('')
    rows.push(`TRUNCATED at ${maxEntries} entries.`)
  }

  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

interface PackageJsonShape {
  name?: unknown
  version?: unknown
  dependencies?: unknown
  devDependencies?: unknown
  optionalDependencies?: unknown
  peerDependencies?: unknown
}

function keysOfRecord(value: unknown): string[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return []
  }

  return Object.keys(value as Record<string, unknown>).sort()
}

function depsCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace: VxsWorkspaceInfo = detectVxsWorkspace(context.cwd)
  const packageJson = path.join(workspace.root, 'package.json')

  if (!fs.existsSync(packageJson)) {
    return immediateError(
      'package.json was not found in the detected workspace.',
      [`Workspace Root: ${workspace.root}`]
    )
  }

  let data: PackageJsonShape
  try {
    data = JSON.parse(fs.readFileSync(packageJson, 'utf-8')) as PackageJsonShape
  } catch (error) {
    return immediateError(
      'package.json could not be parsed.',
      [error instanceof Error ? error.message : String(error)]
    )
  }

  const groups = [
    ['dependencies', keysOfRecord(data.dependencies)],
    ['devDependencies', keysOfRecord(data.devDependencies)],
    ['optionalDependencies', keysOfRecord(data.optionalDependencies)],
    ['peerDependencies', keysOfRecord(data.peerDependencies)]
  ] as const

  const rows: string[] = [
    'VXS DEPS',
    `Package: ${typeof data.name === 'string' ? data.name : '(unnamed)'}`,
    `Version: ${typeof data.version === 'string' ? data.version : '(unknown)'}`,
    `Workspace Root: ${workspace.root}`,
    ''
  ]

  for (const [name, values] of groups) {
    rows.push(`${name}: ${values.length}`)

    for (const value of values.slice(0, 80)) {
      rows.push(`  ${value}`)
    }

    if (values.length > 80) {
      rows.push(`  ... ${values.length - 80} more`)
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

export function createVxsInspectionCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'env',
      aliases: [],
      usage: 'vxs env',
      summary: 'Show a safe development environment summary',
      execute: envCommand
    },
    {
      name: 'which',
      aliases: [],
      usage: 'vxs which <tool>',
      summary: 'Resolve a development tool path',
      execute: whichCommand
    },
    {
      name: 'tree',
      aliases: [],
      usage: 'vxs tree [1-4]',
      summary: 'Show a bounded workspace tree',
      execute: treeCommand
    },
    {
      name: 'deps',
      aliases: [],
      usage: 'vxs deps',
      summary: 'Inspect local package dependencies',
      execute: depsCommand
    }
  ]
}
