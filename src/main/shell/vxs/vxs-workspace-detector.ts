import * as fs from 'node:fs'
import * as path from 'node:path'

export type VxsWorkspaceKind =
  | 'directory'
  | 'node'
  | 'rust'
  | 'python'
  | 'mixed'

export interface VxsWorkspaceInfo {
  cwd: string
  root: string
  kind: VxsWorkspaceKind
  markers: string[]
  packageManager: string | null
  packageName: string | null
  packageVersion: string | null
  frameworks: string[]
  scripts: string[]
  git: boolean
}

const WORKSPACE_MARKERS = [
  'package.json',
  'Cargo.toml',
  'pyproject.toml',
  'requirements.txt',
  'setup.py',
  '.git'
] as const

function exists(candidate: string): boolean {
  try {
    return fs.existsSync(candidate)
  } catch {
    return false
  }
}

function readJsonObject(candidate: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(fs.readFileSync(candidate, 'utf8'))
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : null
  } catch {
    return null
  }
}

function stringProperty(
  record: Record<string, unknown> | null,
  key: string
): string | null {
  const value = record?.[key]
  return typeof value === 'string' && value.trim()
    ? value.trim()
    : null
}

function objectProperty(
  record: Record<string, unknown> | null,
  key: string
): Record<string, unknown> {
  const value = record?.[key]
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function nearestWorkspaceRoot(start: string): string {
  let current = path.resolve(start)

  while (true) {
    if (WORKSPACE_MARKERS.some(marker => exists(path.join(current, marker)))) {
      return current
    }

    const parent = path.dirname(current)
    if (parent === current) return path.resolve(start)
    current = parent
  }
}

function detectPackageManager(root: string): string | null {
  if (exists(path.join(root, 'pnpm-lock.yaml'))) return 'pnpm'
  if (exists(path.join(root, 'yarn.lock'))) return 'yarn'
  if (exists(path.join(root, 'package-lock.json'))) return 'npm'
  if (exists(path.join(root, 'package.json'))) return 'npm'
  return null
}

function detectFrameworks(packageJson: Record<string, unknown> | null): string[] {
  if (!packageJson) return []

  const deps = {
    ...objectProperty(packageJson, 'dependencies'),
    ...objectProperty(packageJson, 'devDependencies')
  }

  const known: Array<[string, string]> = [
    ['electron', 'Electron'],
    ['vue', 'Vue'],
    ['react', 'React'],
    ['typescript', 'TypeScript'],
    ['vite', 'Vite'],
    ['@electron-vite/cli', 'electron-vite'],
    ['electron-vite', 'electron-vite'],
    ['quasar', 'Quasar'],
    ['@quasar/extras', 'Quasar']
  ]

  const found: string[] = []
  for (const [dependency, label] of known) {
    if (dependency in deps && !found.includes(label)) found.push(label)
  }
  return found
}

function detectScripts(packageJson: Record<string, unknown> | null): string[] {
  const scripts = objectProperty(packageJson, 'scripts')
  return Object.keys(scripts).sort()
}

export function detectVxsWorkspace(cwd: string): VxsWorkspaceInfo {
  const resolvedCwd = path.resolve(cwd)
  const root = nearestWorkspaceRoot(resolvedCwd)

  const markers = WORKSPACE_MARKERS.filter(
    marker => exists(path.join(root, marker))
  )

  const hasNode = markers.includes('package.json')
  const hasRust = markers.includes('Cargo.toml')
  const hasPython =
    markers.includes('pyproject.toml') ||
    markers.includes('requirements.txt') ||
    markers.includes('setup.py')

  const kinds = [hasNode, hasRust, hasPython].filter(Boolean).length
  const kind: VxsWorkspaceKind =
    kinds > 1
      ? 'mixed'
      : hasNode
        ? 'node'
        : hasRust
          ? 'rust'
          : hasPython
            ? 'python'
            : 'directory'

  const packageJson = hasNode
    ? readJsonObject(path.join(root, 'package.json'))
    : null

  return {
    cwd: resolvedCwd,
    root,
    kind,
    markers,
    packageManager: detectPackageManager(root),
    packageName: stringProperty(packageJson, 'name'),
    packageVersion: stringProperty(packageJson, 'version'),
    frameworks: detectFrameworks(packageJson),
    scripts: detectScripts(packageJson),
    git: exists(path.join(root, '.git'))
  }
}
