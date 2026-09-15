// VXS_AUTONOMOUS_PREPARATION_LOOP_000026
// VXS_CHANGED_SCOPE_VERIFICATION_PACK_000018
// Preserves VXS_ORCHESTRATION_CAPABILITY_PACK_000017
import { spawnSync } from 'node:child_process'
import {
  detectVxsWorkspace,
  type VxsWorkspaceInfo
} from './vxs-workspace-detector'
import type {
  VxsCommandContext,
  VxsCommandDefinition,
  VxsCommandDispatchResult,
  VxsExecutionCommandResult
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

function runReadOnly(
  program: string,
  args: string[],
  cwd?: string,
  timeout = 5_000
): { ok: boolean; stdout: string; stderr: string } {
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

function commandAvailable(name: string): boolean {
  const resolver = process.platform === 'win32' ? 'where.exe' : 'which'
  return runReadOnly(resolver, [name], undefined, 2_000).ok
}

function packageExecutable(packageManager: string): string {
  if (process.platform !== 'win32') return packageManager
  return `${packageManager}.cmd`
}

function hasMarker(
  workspace: VxsWorkspaceInfo,
  marker: string
): boolean {
  return workspace.markers.includes(marker)
}

function unique(values: string[]): string[] {
  return [...new Set(values)]
}

function preflightCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  const gitStatus = workspace.git
    ? runReadOnly(
        'git',
        ['status', '--short', '--branch', '--untracked-files=normal'],
        workspace.root,
        5_000
      )
    : null

  let changed = 0
  let branch = '(git not detected)'

  if (gitStatus?.ok) {
    const rows = gitStatus.stdout.split(/\r?\n/).filter(Boolean)
    branch = rows[0] ?? '(branch unknown)'
    changed = Math.max(0, rows.length - 1)
  }

  let workstation = 'not observed'
  if (process.platform === 'win32') {
    const netstat = runReadOnly(
      'netstat.exe',
      ['-ano', '-p', 'tcp'],
      undefined,
      5_000
    )

    if (
      netstat.ok &&
      netstat.stdout
        .split(/\r?\n/)
        .some(value => /127\.0\.0\.1:47832\s+.*LISTENING/i.test(value))
    ) {
      workstation = 'LISTENING'
    }
  }

  const tools: Array<[string, boolean]> = [
    ['git', commandAvailable(process.platform === 'win32' ? 'git.exe' : 'git')],
    ['pwsh', commandAvailable(process.platform === 'win32' ? 'pwsh.exe' : 'pwsh')],
    ['python', commandAvailable(process.platform === 'win32' ? 'python.exe' : 'python')],
    ['cargo', commandAvailable(process.platform === 'win32' ? 'cargo.exe' : 'cargo')]
  ]

  if (workspace.packageManager) {
    tools.push([
      workspace.packageManager,
      commandAvailable(packageExecutable(workspace.packageManager))
    ])
  }

  const rows = [
    'VXS PREFLIGHT',
    `Workspace Root: ${workspace.root}`,
    `Workspace Type: ${workspace.kind}`,
    `Markers: ${workspace.markers.length ? workspace.markers.join(', ') : 'none'}`,
    `Package Manager: ${workspace.packageManager ?? 'not detected'}`,
    `Branch: ${branch}`,
    `Changed/Untracked Rows: ${changed}`,
    `Workstation 127.0.0.1:47832: ${workstation}`,
    '',
    'Tool Availability:',
    ...tools.map(([name, available]) =>
      `  [${available ? 'PASS' : 'WARN'}] ${name}`
    ),
    '',
    `Scripts: ${workspace.scripts.length ? workspace.scripts.join(', ') : 'none detected'}`,
    '',
    'PREFLIGHT is observation-only. No build/test/check has been executed.',
    ''
  ]

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function addNodeVerifySteps(
  workspace: VxsWorkspaceInfo,
  mode: 'quick' | 'full',
  steps: string[],
  labels: string[]
): void {
  if (!workspace.packageManager) return

  const executable = packageExecutable(workspace.packageManager)
  const scripts = new Set(workspace.scripts)

  for (const candidate of ['typecheck', 'check']) {
    if (scripts.has(candidate)) {
      steps.push(`${executable} run ${candidate}`)
      labels.push(`node:${candidate}`)
      break
    }
  }

  if (scripts.has('lint')) {
    steps.push(`${executable} run lint`)
    labels.push('node:lint')
  }

  for (const candidate of ['format:check', 'format-check', 'prettier:check']) {
    if (scripts.has(candidate)) {
      steps.push(`${executable} run ${candidate}`)
      labels.push(`node:${candidate}`)
      break
    }
  }

  if (scripts.has('test')) {
    steps.push(`${executable} run test`)
    labels.push('node:test')
  }

  if (mode === 'full' && scripts.has('build')) {
    steps.push(`${executable} run build`)
    labels.push('node:build')
  }
}

function addRustVerifySteps(
  workspace: VxsWorkspaceInfo,
  mode: 'quick' | 'full',
  steps: string[],
  labels: string[]
): void {
  if (!hasMarker(workspace, 'Cargo.toml')) return

  steps.push('cargo check')
  labels.push('rust:check')

  steps.push('cargo fmt --all -- --check')
  labels.push('rust:fmt-check')

  steps.push('cargo test')
  labels.push('rust:test')

  if (mode === 'full') {
    steps.push('cargo clippy --all-targets')
    labels.push('rust:clippy')

    steps.push('cargo build')
    labels.push('rust:build')
  }
}

function addPythonVerifySteps(
  workspace: VxsWorkspaceInfo,
  mode: 'quick' | 'full',
  steps: string[],
  labels: string[]
): void {
  const pythonWorkspace =
    hasMarker(workspace, 'pyproject.toml') ||
    hasMarker(workspace, 'requirements.txt') ||
    hasMarker(workspace, 'setup.py')

  if (!pythonWorkspace) return

  steps.push('python -m ruff check .')
  labels.push('python:ruff-check')

  steps.push('python -m ruff format --check .')
  labels.push('python:format-check')

  steps.push('python -m pytest')
  labels.push('python:test')

  if (mode === 'full' && hasMarker(workspace, 'pyproject.toml')) {
    steps.push('python -m build')
    labels.push('python:build')
  }
}


export type VerifyMode = 'quick' | 'full' | 'changed'

export interface VerificationPlan {
  mode: VerifyMode
  commands: string[]
  labels: string[]
  changedFiles: string[]
  ecosystems: string[]
  clean: boolean
}

function changedFilesForWorkspace(
  workspace: VxsWorkspaceInfo
): { ok: boolean; files: string[]; error: string } {
  if (!workspace.git) {
    return {
      ok: false,
      files: [],
      error: 'Git repository was not detected.'
    }
  }

  const status = runReadOnly(
    'git',
    ['status', '--short', '--untracked-files=normal'],
    workspace.root,
    5_000
  )

  if (!status.ok) {
    return {
      ok: false,
      files: [],
      error: status.stderr || 'git status failed'
    }
  }

  const files = status.stdout
    .split(/\r?\n/)
    .filter(Boolean)
    .map(row => row.length >= 4 ? row.slice(3).trim() : row.trim())
    .map(value => {
      const arrow = value.lastIndexOf(' -> ')
      return arrow >= 0 ? value.slice(arrow + 4).trim() : value
    })
    .map(value => value.replace(/^"(.*)"$/, '$1'))
    .filter(Boolean)

  return {
    ok: true,
    files: unique(files),
    error: ''
  }
}

function classifyChangedEcosystems(
  workspace: VxsWorkspaceInfo,
  files: string[]
): string[] {
  const ecosystems = new Set<string>()

  const nodeExtensions = new Set([
    '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
    '.vue', '.svelte', '.css', '.scss', '.sass', '.less', '.html'
  ])

  const nodeNames = new Set([
    'package.json',
    'package-lock.json',
    'pnpm-lock.yaml',
    'yarn.lock',
    'npm-shrinkwrap.json',
    'vite.config.ts',
    'vite.config.js',
    'tsconfig.json'
  ])

  const rustNames = new Set([
    'cargo.toml',
    'cargo.lock'
  ])

  const pythonNames = new Set([
    'pyproject.toml',
    'setup.py',
    'setup.cfg',
    'tox.ini',
    'pytest.ini'
  ])

  for (const raw of files) {
    const normalized = raw.replace(/\\/g, '/')
    const lower = normalized.toLowerCase()
    const base = lower.split('/').pop() ?? lower
    const extension = (
      base.includes('.') ? `.${base.split('.').pop()}` : ''
    )

    if (
      nodeExtensions.has(extension) ||
      nodeNames.has(base) ||
      base.endsWith('.json')
    ) {
      ecosystems.add('node')
    }

    if (extension === '.rs' || rustNames.has(base)) {
      ecosystems.add('rust')
    }

    if (
      extension === '.py' ||
      pythonNames.has(base) ||
      /^requirements.*\.txt$/.test(base)
    ) {
      ecosystems.add('python')
    }
  }

  // Conservative fallback: changed files exist but no ecosystem-specific
  // classification matched. Verify every ecosystem detected in this workspace.
  if (!ecosystems.size && files.length) {
    if (workspace.packageManager) ecosystems.add('node')
    if (hasMarker(workspace, 'Cargo.toml')) ecosystems.add('rust')
    if (
      hasMarker(workspace, 'pyproject.toml') ||
      hasMarker(workspace, 'requirements.txt') ||
      hasMarker(workspace, 'setup.py')
    ) {
      ecosystems.add('python')
    }
  }

  return [...ecosystems]
}

export function createVxsVerificationPlan(
  workspace: VxsWorkspaceInfo,
  mode: VerifyMode
): VerificationPlan | { error: string } {
  const steps: string[] = []
  const labels: string[] = []
  let changedFiles: string[] = []
  let ecosystems: string[] = []

  if (mode === 'changed') {
    const changed = changedFilesForWorkspace(workspace)
    if (!changed.ok) return { error: changed.error }

    changedFiles = changed.files
    if (!changedFiles.length) {
      return {
        mode,
        commands: [],
        labels: [],
        changedFiles: [],
        ecosystems: [],
        clean: true
      }
    }

    ecosystems = classifyChangedEcosystems(workspace, changedFiles)

    if (ecosystems.includes('node')) {
      addNodeVerifySteps(workspace, 'quick', steps, labels)
    }
    if (ecosystems.includes('rust')) {
      addRustVerifySteps(workspace, 'quick', steps, labels)
    }
    if (ecosystems.includes('python')) {
      addPythonVerifySteps(workspace, 'quick', steps, labels)
    }
  } else {
    addNodeVerifySteps(workspace, mode, steps, labels)
    addRustVerifySteps(workspace, mode, steps, labels)
    addPythonVerifySteps(workspace, mode, steps, labels)

    if (workspace.packageManager) ecosystems.push('node')
    if (hasMarker(workspace, 'Cargo.toml')) ecosystems.push('rust')
    if (
      hasMarker(workspace, 'pyproject.toml') ||
      hasMarker(workspace, 'requirements.txt') ||
      hasMarker(workspace, 'setup.py')
    ) {
      ecosystems.push('python')
    }
  }

  return {
    mode,
    commands: unique(steps),
    labels: unique(labels),
    changedFiles,
    ecosystems: unique(ecosystems),
    clean: false
  }
}

function renderVerificationPlan(
  plan: VerificationPlan,
  workspace: VxsWorkspaceInfo
): string {
  const rows = [
    'VXS VERIFY PLAN',
    `Mode: ${plan.mode}`,
    `Workspace Root: ${workspace.root}`,
    `Ecosystems: ${plan.ecosystems.length ? plan.ecosystems.join(', ') : 'none'}`,
    `Changed Files: ${plan.changedFiles.length}`,
    ''
  ]

  if (plan.changedFiles.length) {
    rows.push('Changed Scope:')
    rows.push(...plan.changedFiles.slice(0, 80).map(value => `  ${value}`))
    if (plan.changedFiles.length > 80) {
      rows.push(`  ... ${plan.changedFiles.length - 80} more`)
    }
    rows.push('')
  }

  rows.push('Pipeline:')
  if (plan.clean) {
    rows.push('  (clean working tree; nothing to verify)')
  } else if (!plan.commands.length) {
    rows.push('  (no supported verification commands detected)')
  } else {
    plan.commands.forEach((command, index) => {
      rows.push(`  ${index + 1}. ${command}`)
    })
  }

  rows.push('')
  rows.push('PLAN_ONLY=YES')
  rows.push('')

  return rows.map(line).join('')
}

function verifyPlanCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const rawMode = (args[0] ?? 'changed').toLowerCase()

  if (
    rawMode !== 'quick' &&
    rawMode !== 'full' &&
    rawMode !== 'changed'
  ) {
    return immediateError(
      `Unknown verify-plan mode '${rawMode}'.`,
      ['Usage: vxs verify-plan [quick|full|changed]']
    )
  }

  const workspace = detectVxsWorkspace(context.cwd)
  const plan = createVxsVerificationPlan(workspace, rawMode as VerifyMode)

  if ('error' in plan) {
    return immediateError(plan.error)
  }

  return {
    kind: 'immediate',
    output: renderVerificationPlan(plan, workspace),
    exitCode: 0,
    stream: 'system'
  }
}


export function chainVxsVerificationCommands(commands: string[]): string {
  if (process.platform === 'win32') {
    return commands
      .map(
        command =>
          `${command}; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`
      )
      .join('; ')
  }

  return commands.join(' && ')
}

function verifyCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const rawMode = (args[0] ?? 'quick').toLowerCase()

  if (
    rawMode !== 'quick' &&
    rawMode !== 'full' &&
    rawMode !== 'changed'
  ) {
    return immediateError(
      `Unknown verify mode '${rawMode}'.`,
      ['Usage: vxs verify [quick|full|changed]']
    )
  }

  const mode = rawMode as VerifyMode
  const workspace = detectVxsWorkspace(context.cwd)
  const plan = createVxsVerificationPlan(workspace, mode)

  if ('error' in plan) {
    return immediateError(plan.error)
  }

  if (plan.clean) {
    return {
      kind: 'immediate',
      output: [
        'VXS VERIFY CHANGED',
        `Workspace Root: ${workspace.root}`,
        'Changed Files: 0',
        '',
        'Clean working tree; no changed-scope verification required.',
        ''
      ].map(line).join(''),
      exitCode: 0,
      stream: 'system'
    }
  }

  if (!plan.commands.length) {
    return immediateError(
      'No supported verification pipeline was detected.',
      [
        `Workspace Root: ${workspace.root}`,
        `Mode: ${mode}`,
        'Expected Node scripts, Cargo.toml, or a Python project marker.'
      ]
    )
  }

  const result: VxsExecutionCommandResult = {
    kind: 'execute',
    executionCommand: chainVxsVerificationCommands(plan.commands),
    executionCwd: workspace.root,
    capability:
      mode === 'full'
        ? 'VERIFY_FULL'
        : mode === 'changed'
          ? 'VERIFY_CHANGED'
          : 'VERIFY_QUICK',
    routeSummary:
      `VXS verify ${mode}: ${plan.labels.join(' -> ')}`
  }

  return result
}

export function createVxsOrchestrationCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'preflight',
      aliases: [],
      usage: 'vxs preflight',
      summary: 'Summarize workspace/runtime readiness without execution',
      execute: preflightCommand
    },
    {
      name: 'verify',
      aliases: [],
      usage: 'vxs verify [quick|full|changed]',
      summary: 'Run a fail-fast workspace verification pipeline',
      execute: verifyCommand
    },
    {
      name: 'verify-plan',
      aliases: ['vplan'],
      usage: 'vxs verify-plan [quick|full|changed]',
      summary: 'Preview a verification pipeline without executing it',
      execute: verifyPlanCommand
    }
  ]
}
