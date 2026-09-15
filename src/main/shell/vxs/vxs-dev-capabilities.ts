// VXS_GIT_BOOTSTRAP_000068V3
// VXS_AUTO_GIT_PUBLISH_000065V3
// VXS_CODE_QUALITY_CAPABILITY_PACK_000010
import * as path from 'node:path'
import {
  detectVxsWorkspace,
  type VxsWorkspaceInfo
} from './vxs-workspace-detector'
import { planVxsAutoGitMutation } from './vxs-git-auto-publish'
import { planVxsGitBootstrap } from './vxs-git-bootstrap'
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
    output: [
      `ERROR: ${message}`,
      ...hints,
      ''
    ].map(line).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

function packageExecutable(packageManager: string): string {
  if (process.platform !== 'win32') return packageManager
  return `${packageManager}.cmd`
}

function nodeScriptPlan(
  workspace: VxsWorkspaceInfo,
  script: string,
  capability: string
): VxsExecutionCommandResult | null {
  if (!workspace.packageManager) return null
  if (!workspace.scripts.includes(script)) return null

  const executable = packageExecutable(workspace.packageManager)

  return {
    kind: 'execute',
    executionCommand: `${executable} run ${script}`,
    executionCwd: workspace.root,
    capability,
    routeSummary: `${workspace.packageManager} script '${script}'`
  }
}

function workspaceHas(
  workspace: VxsWorkspaceInfo,
  marker: string
): boolean {
  return workspace.markers.includes(marker)
}

function buildPlan(
  workspace: VxsWorkspaceInfo
): VxsCommandDispatchResult {
  const node = nodeScriptPlan(workspace, 'build', 'BUILD')
  if (node) return node

  if (workspaceHas(workspace, 'Cargo.toml')) {
    return {
      kind: 'execute',
      executionCommand: 'cargo build',
      executionCwd: workspace.root,
      capability: 'BUILD',
      routeSummary: 'Cargo build'
    }
  }

  if (workspaceHas(workspace, 'pyproject.toml')) {
    return {
      kind: 'execute',
      executionCommand: 'python -m build',
      executionCwd: workspace.root,
      capability: 'BUILD',
      routeSummary: 'Python package build'
    }
  }

  return immediateError(
    'No supported build capability detected for this workspace.',
    [
      `Workspace Root: ${workspace.root}`,
      'Expected: package.json build script, Cargo.toml, or pyproject.toml'
    ]
  )
}

function testPlan(
  workspace: VxsWorkspaceInfo
): VxsCommandDispatchResult {
  const node = nodeScriptPlan(workspace, 'test', 'TEST')
  if (node) return node

  if (workspaceHas(workspace, 'Cargo.toml')) {
    return {
      kind: 'execute',
      executionCommand: 'cargo test',
      executionCwd: workspace.root,
      capability: 'TEST',
      routeSummary: 'Cargo test'
    }
  }

  if (
    workspaceHas(workspace, 'pyproject.toml') ||
    workspaceHas(workspace, 'requirements.txt') ||
    workspaceHas(workspace, 'setup.py')
  ) {
    return {
      kind: 'execute',
      executionCommand: 'python -m pytest',
      executionCwd: workspace.root,
      capability: 'TEST',
      routeSummary: 'Python pytest'
    }
  }

  return immediateError(
    'No supported test capability detected for this workspace.',
    [`Workspace Root: ${workspace.root}`]
  )
}

function lintPlan(
  workspace: VxsWorkspaceInfo
): VxsCommandDispatchResult {
  const node = nodeScriptPlan(workspace, 'lint', 'LINT')
  if (node) return node

  if (workspaceHas(workspace, 'Cargo.toml')) {
    return {
      kind: 'execute',
      executionCommand: 'cargo clippy --all-targets',
      executionCwd: workspace.root,
      capability: 'LINT',
      routeSummary: 'Cargo clippy'
    }
  }

  if (
    workspaceHas(workspace, 'pyproject.toml') ||
    workspaceHas(workspace, 'requirements.txt') ||
    workspaceHas(workspace, 'setup.py')
  ) {
    return {
      kind: 'execute',
      executionCommand: 'python -m ruff check .',
      executionCwd: workspace.root,
      capability: 'LINT',
      routeSummary: 'Python Ruff'
    }
  }

  return immediateError(
    'No supported lint capability detected for this workspace.',
    [`Workspace Root: ${workspace.root}`]
  )
}

function runScriptPlan(
  workspace: VxsWorkspaceInfo,
  args: string[]
): VxsCommandDispatchResult {
  if (!workspace.packageManager) {
    return immediateError(
      'vxs run currently requires a Node workspace with a package manager.'
    )
  }

  const script = args[0]?.trim() ?? ''
  if (!script) {
    return {
      kind: 'immediate',
      output: [
        'VXS RUN',
        `Workspace Root: ${workspace.root}`,
        `Package Manager: ${workspace.packageManager}`,
        `Scripts: ${workspace.scripts.length ? workspace.scripts.join(', ') : 'none'}`,
        '',
        'Usage: vxs run <script>',
        ''
      ].map(line).join(''),
      exitCode: 0,
      stream: 'system'
    }
  }

  if (!/^[A-Za-z0-9:_-]+$/.test(script)) {
    return immediateError(
      `Invalid package script name '${script}'.`
    )
  }

  if (!workspace.scripts.includes(script)) {
    return immediateError(
      `Package script '${script}' was not found.`,
      [
        `Available: ${workspace.scripts.length ? workspace.scripts.join(', ') : 'none'}`
      ]
    )
  }

  const plan = nodeScriptPlan(workspace, script, 'RUN')
  return plan ?? immediateError(`Unable to route package script '${script}'.`)
}

function gitPlan(
  context: VxsCommandContext,
  args: string[]
): VxsCommandDispatchResult {
  const subcommand = (args[0] ?? 'status').toLowerCase()
  const workspace = detectVxsWorkspace(context.cwd)

  const gitRoot = workspace.git
    ? workspace.root
    : context.cwd

  if (subcommand === 'bootstrap') {
    return planVxsGitBootstrap(
      context,
      path.resolve(gitRoot),
      args.slice(1)
    )
  }

  if (
    subcommand === 'commit' ||
    subcommand === 'push' ||
    subcommand === 'publish'
  ) {
    return planVxsAutoGitMutation(
      context,
      path.resolve(gitRoot),
      subcommand,
      args.slice(1),
      workspace
    )
  }

  const fixed: Record<string, {
    command: string
    summary: string
  }> = {
    status: {
      command: 'git status --short --branch',
      summary: 'Git status'
    },
    diff: {
      command: 'git diff',
      summary: 'Git working-tree diff'
    },
    staged: {
      command: 'git diff --staged',
      summary: 'Git staged diff'
    },
    branch: {
      command: 'git branch --show-current',
      summary: 'Git current branch'
    },
    log: {
      command: 'git log --oneline -10',
      summary: 'Git recent log'
    }
  }

  if (subcommand === 'help' || subcommand === '--help') {
    return {
      kind: 'immediate',
      output: [
        'VXS GIT · OBSERVE + AUTO-GATED MUTATION',
        '',
        '  vxs git status                         Short status + branch',
        '  vxs git diff                           Working-tree diff',
        '  vxs git staged                         Staged diff',
        '  vxs git branch                         Current branch',
        '  vxs git log                            Last 10 commits',
        '',
        'AUTO Human Gate mutation:',
        '  vxs git bootstrap <vera-01..vera-05> <github-origin-url>',
        '  vxs git commit <vera-01..vera-05> <message>',
        '  vxs git push <vera-01..vera-05>',
        '  vxs git publish <vera-01..vera-05> <message>',
        '',
        'bootstrap = AUTO-authorized git init(main) + GitHub origin registration only',
        'publish = verify -> stage -> commit -> dry-run push -> push -> remote HEAD verify',
        'AUTO OFF / expired / out-of-scope = fail closed.',
        'Force push and remote mutation are not supported.',
        ''
      ].map(line).join(''),
      exitCode: 0,
      stream: 'system'
    }
  }

  const selected = fixed[subcommand]
  if (!selected) {
    return immediateError(
      `Unsupported vxs git command '${subcommand}'.`,
      ['Run: vxs git help']
    )
  }

  return {
    kind: 'execute',
    executionCommand: selected.command,
    executionCwd: path.resolve(gitRoot),
    capability: 'GIT',
    routeSummary: selected.summary
  }
}


function buildCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  return buildPlan(detectVxsWorkspace(context.cwd))
}

function testCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  return testPlan(detectVxsWorkspace(context.cwd))
}

function lintCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  return lintPlan(detectVxsWorkspace(context.cwd))
}

function runCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  return runScriptPlan(detectVxsWorkspace(context.cwd), args)
}

function gitCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  return gitPlan(context, args)
}


function workspaceCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  return {
    kind: 'immediate',
    output: [
      'VXS WORKSPACE',
      `CWD: ${workspace.cwd}`,
      `Root: ${workspace.root}`,
      `Type: ${workspace.kind}`,
      `Markers: ${workspace.markers.length ? workspace.markers.join(', ') : 'none'}`,
      `Package Manager: ${workspace.packageManager ?? 'not detected'}`,
      `Package: ${workspace.packageName ?? 'not detected'}`,
      `Version: ${workspace.packageVersion ?? 'not detected'}`,
      `Frameworks: ${workspace.frameworks.length ? workspace.frameworks.join(', ') : 'none detected'}`,
      `Git: ${workspace.git ? 'detected' : 'not detected'}`,
      `Scripts: ${workspace.scripts.length ? workspace.scripts.join(', ') : 'none detected'}`,
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function scriptsCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  if (!workspace.packageManager) {
    return immediateError(
      'No Node package manager was detected for this workspace.',
      [`Workspace Root: ${workspace.root}`]
    )
  }

  return {
    kind: 'immediate',
    output: [
      'VXS SCRIPTS',
      `Workspace Root: ${workspace.root}`,
      `Package Manager: ${workspace.packageManager}`,
      '',
      ...(workspace.scripts.length
        ? workspace.scripts.map(script => `  ${script}`)
        : ['  (no package scripts detected)']),
      ''
    ].map(line).join(''),
    exitCode: 0,
    stream: 'system'
  }
}

function checkCommand(
  _args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const workspace = detectVxsWorkspace(context.cwd)

  for (const script of ['typecheck', 'check']) {
    const plan = nodeScriptPlan(workspace, script, 'CHECK')
    if (plan) return plan
  }

  if (workspaceHas(workspace, 'Cargo.toml')) {
    return {
      kind: 'execute',
      executionCommand: 'cargo check',
      executionCwd: workspace.root,
      capability: 'CHECK',
      routeSummary: 'Cargo check'
    }
  }

  if (
    workspaceHas(workspace, 'pyproject.toml') ||
    workspaceHas(workspace, 'requirements.txt') ||
    workspaceHas(workspace, 'setup.py')
  ) {
    return {
      kind: 'execute',
      executionCommand: 'python -m ruff check .',
      executionCwd: workspace.root,
      capability: 'CHECK',
      routeSummary: 'Python Ruff check'
    }
  }

  return immediateError(
    'No supported non-mutating code check was detected.',
    [
      `Workspace Root: ${workspace.root}`,
      'Expected: Node typecheck/check script, Cargo.toml, or Python workspace'
    ]
  )
}

function formatCheckCommand(
  args: string[],
  context: VxsCommandContext
): VxsCommandDispatchResult {
  const requested = (args[0] ?? '').toLowerCase()
  if (requested !== '--check') {
    return immediateError(
      'Formatting mutation is not enabled in this pack.',
      ['Usage: vxs format --check']
    )
  }

  const workspace = detectVxsWorkspace(context.cwd)

  for (const script of ['format:check', 'format-check', 'prettier:check']) {
    const plan = nodeScriptPlan(workspace, script, 'FORMAT_CHECK')
    if (plan) return plan
  }

  if (workspaceHas(workspace, 'Cargo.toml')) {
    return {
      kind: 'execute',
      executionCommand: 'cargo fmt --all -- --check',
      executionCwd: workspace.root,
      capability: 'FORMAT_CHECK',
      routeSummary: 'Cargo fmt check'
    }
  }

  if (
    workspaceHas(workspace, 'pyproject.toml') ||
    workspaceHas(workspace, 'requirements.txt') ||
    workspaceHas(workspace, 'setup.py')
  ) {
    return {
      kind: 'execute',
      executionCommand: 'python -m ruff format --check .',
      executionCwd: workspace.root,
      capability: 'FORMAT_CHECK',
      routeSummary: 'Python Ruff format check'
    }
  }

  return immediateError(
    'No supported formatting check was detected.',
    [
      `Workspace Root: ${workspace.root}`,
      'Expected: Node format-check script, Cargo.toml, or Python workspace'
    ]
  )
}

export function createVxsDevelopmentCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'workspace',
      aliases: ['ws-info'],
      usage: 'vxs workspace',
      summary: 'Show detected workspace details',
      execute: workspaceCommand
    },
    {
      name: 'scripts',
      aliases: [],
      usage: 'vxs scripts',
      summary: 'List detected Node package scripts',
      execute: scriptsCommand
    },
    {
      name: 'check',
      aliases: [],
      usage: 'vxs check',
      summary: 'Auto-route non-mutating code checks',
      execute: checkCommand
    },
    {
      name: 'format',
      aliases: [],
      usage: 'vxs format --check',
      summary: 'Verify formatting without rewriting files',
      execute: formatCheckCommand
    },
    {
      name: 'build',
      aliases: [],
      usage: 'vxs build',
      summary: 'Auto-route the workspace build',
      execute: buildCommand
    },
    {
      name: 'test',
      aliases: [],
      usage: 'vxs test',
      summary: 'Auto-route the workspace test suite',
      execute: testCommand
    },
    {
      name: 'lint',
      aliases: [],
      usage: 'vxs lint',
      summary: 'Auto-route the workspace linter',
      execute: lintCommand
    },
    {
      name: 'run',
      aliases: [],
      usage: 'vxs run <script>',
      summary: 'Run a detected Node package script',
      execute: runCommand
    },
    {
      name: 'git',
      aliases: [],
      usage: 'vxs git <status|diff|staged|branch|log|bootstrap|commit|push|publish>',
      summary: 'Git observation plus AUTO Human Gate bootstrap/commit/push/publish',
      execute: gitCommand
    }
  ]
}
