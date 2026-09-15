import { app } from 'electron'
import { execFile, spawn, type ChildProcess } from 'node:child_process'
import {
  copyFileSync,
  existsSync,
  readdirSync,
  renameSync,
  statSync,
  unlinkSync
} from 'node:fs'
import { basename, dirname, join, resolve, sep } from 'node:path'
import { promisify } from 'node:util'
import type {
  WorkstationServerProcessState,
  WorkstationServerRuntimeKind
} from '../../shared/contracts'
import { WorkstationClient } from './workstation-client'

const WORKSTATION_BIND = '127.0.0.1:47832' as const
const REQUIRED_RUNTIME_CONTRACT = 'vertex-workstation/headless-server-1'
const REQUIRED_RECOVERY_CONTRACT = 'estop-failed-write-recovery-1'
const START_TIMEOUT_MS = 15_000
const START_POLL_MS = 300
const ROOT_SCAN_DEPTH = 10
const LEGACY_REPLACE_TIMEOUT_MS = 8_000
const ROOT_RELEASE_EXE = join('release', 'vertex-workstation.exe')
const ROOT_RELEASE_TARGET_DIR = 'portal-managed-release-target'
const RELEASE_BUILD_TIMEOUT_MS = 10 * 60_000
const execFileAsync = promisify(execFile)

type LaunchPlan = {
  command: string
  args: string[]
  cwd: string
  root: string
  runtime: WorkstationServerRuntimeKind
  env?: Record<string, string>
}

type RuntimeHealthObservation = {
  reachable: boolean
  compatible: boolean
  runtimeContract: string | null
  runtimeGeneration: string | null
  recoveryContract: string | null
}

function nowUtc(): string {
  return new Date().toISOString()
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolveSleep => setTimeout(resolveSleep, ms))
}

function workstationRootValid(root: string): boolean {
  return existsSync(join(root, 'headless', 'Cargo.toml'))
}

function uniqueExistingRoots(values: string[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  for (const value of values) {
    const root = resolve(value)
    const key = root.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    if (workstationRootValid(root)) result.push(root)
  }

  return result
}

export class WorkstationProcessController {
  private readonly client = new WorkstationClient()
  private managedChild: ChildProcess | null = null
  private managedRuntime: WorkstationServerRuntimeKind = 'UNAVAILABLE'
  private managedRoot: string | null = null
  private startedUtc: string | null = null
  private lastError: string | null = null
  private lastHealth: RuntimeHealthObservation = {
    reachable: false,
    compatible: false,
    runtimeContract: null,
    runtimeGeneration: null,
    recoveryContract: null
  }
  private startInFlight: Promise<WorkstationServerProcessState> | null = null

  async state(): Promise<WorkstationServerProcessState> {
    const health = await this.observeHealth()

    if (health.compatible) {
      this.lastError = null
      return this.snapshot(
        'ONLINE',
        true,
        this.managedChild?.pid ?? null,
        this.managedChild ? this.managedRuntime : 'EXTERNAL'
      )
    }

    if (health.reachable) {
      this.lastError = `WORKSTATION_RUNTIME_INCOMPATIBLE expected=${REQUIRED_RUNTIME_CONTRACT}/${REQUIRED_RECOVERY_CONTRACT} actual=${health.runtimeContract ?? 'LEGACY'}/${health.recoveryContract ?? 'LEGACY'}`
      return this.snapshot(
        'INCOMPATIBLE',
        false,
        this.managedChild?.pid ?? null,
        this.managedChild ? this.managedRuntime : 'EXTERNAL'
      )
    }

    if (this.startInFlight) {
      return this.snapshot(
        'STARTING',
        false,
        this.managedChild?.pid ?? null,
        this.managedRuntime
      )
    }

    return this.snapshot(
      this.lastError ? 'ERROR' : 'OFFLINE',
      false,
      this.managedChild?.pid ?? null,
      this.managedChild ? this.managedRuntime : 'UNAVAILABLE'
    )
  }

  start(): Promise<WorkstationServerProcessState> {
    if (this.startInFlight) return this.startInFlight

    this.startInFlight = this.startInternal()
      .finally(() => {
        this.startInFlight = null
      })

    return this.startInFlight
  }

  private async startInternal(): Promise<WorkstationServerProcessState> {
    const existing = await this.observeHealth()
    let forceCurrentSource = false
    let rootReleasePrepared = false

    // 000083V5H1:
    // A compatible external Workstation used to short-circuit here, which meant the
    // root release build branch was never reached.  If Human explicitly presses the
    // migration/start control while the current server is already compatible, first
    // build/publish the root EXE.  If that currently-listening process is not already
    // the root EXE, validate it using the same fail-closed identity gate, retire it,
    // then continue and launch the new root EXE hidden.
    if (existing.compatible) {
      try {
        const rootRelease = await this.ensureRootReleaseBinary(false)
        rootReleasePrepared = true

        if (await this.listenerUsesExecutable(rootRelease)) {
          this.lastError = null
          return this.snapshot(
            'ONLINE',
            true,
            this.managedChild?.pid ?? null,
            this.managedChild ? this.managedRuntime : 'EXTERNAL'
          )
        }

        await this.replaceValidatedLegacyListener()
      } catch (error) {
        this.lastError = `WORKSTATION_ROOT_MIGRATION_BLOCKED:${error instanceof Error ? error.message : String(error)}`
        return this.snapshot(
          'ERROR',
          false,
          this.managedChild?.pid ?? null,
          this.managedChild ? this.managedRuntime : 'EXTERNAL'
        )
      }
    }

    // Explicit START/REPLACE click may retire exactly one validated legacy Workstation listener.
    // This is not a blind kill: PID, executable path and command line must all match
    // the local Workstation server contract before termination is allowed.
    if (existing.reachable && !existing.compatible) {
      try {
        await this.replaceValidatedLegacyListener()
        forceCurrentSource = true
      } catch (error) {
        this.lastError = `WORKSTATION_LEGACY_REPLACE_BLOCKED:${error instanceof Error ? error.message : String(error)}`
        return this.snapshot(
          'INCOMPATIBLE',
          false,
          this.managedChild?.pid ?? null,
          this.managedChild ? this.managedRuntime : 'EXTERNAL'
        )
      }
    }

    if (!rootReleasePrepared) {
      try {
        await this.ensureRootReleaseBinary(forceCurrentSource)
      } catch (error) {
        this.lastError = `WORKSTATION_RELEASE_PREPARE_FAILED:${error instanceof Error ? error.message : String(error)}`
        return this.snapshot('ERROR', false, null, 'UNAVAILABLE')
      }
    }

    const plan = this.resolveLaunchPlan(false)
    if (!plan) {
      this.lastError = 'WORKSTATION_SERVER_RUNTIME_NOT_FOUND'
      return this.snapshot('ERROR', false, null, 'UNAVAILABLE')
    }

    this.lastError = null
    this.managedRoot = plan.root
    this.managedRuntime = plan.runtime
    this.startedUtc = nowUtc()

    const child = spawn(plan.command, plan.args, {
      cwd: plan.cwd,
      detached: true,
      windowsHide: true,
      shell: false,
      stdio: 'ignore',
      env: {
        ...process.env,
        ...plan.env,
        VERTEX_WORKSTATION_ROOT: plan.root
      }
    })

    this.managedChild = child

    child.once('error', error => {
      if (this.managedChild === child) {
        this.lastError = `WORKSTATION_SERVER_SPAWN_ERROR:${error.message}`
        this.managedChild = null
      }
    })

    child.once('exit', (code, signal) => {
      if (this.managedChild !== child) return
      this.managedChild = null

      if (code !== 0 && code !== null) {
        this.lastError = `WORKSTATION_SERVER_EXIT:${code}`
      } else if (signal) {
        this.lastError = `WORKSTATION_SERVER_SIGNAL:${signal}`
      }
    })

    // Workstation is deliberately NOT a child-lifecycle dependency of Session Portal.
    // Portal may start it, but Portal exit must not terminate the factory server.
    child.unref()

    const deadline = Date.now() + START_TIMEOUT_MS
    while (Date.now() < deadline) {
      if (await this.healthOnline()) {
        this.lastError = null
        return this.snapshot(
          'ONLINE',
          true,
          child.pid ?? null,
          plan.runtime
        )
      }

      if (this.lastError) {
        return this.snapshot(
          'ERROR',
          false,
          child.pid ?? null,
          plan.runtime
        )
      }

      await sleep(START_POLL_MS)
    }

    // A slow first Cargo build may legitimately exceed the synchronous button wait.
    // The process remains detached and the existing Portal health poll will mark ONLINE later.
    return this.snapshot(
      'STARTING',
      false,
      child.pid ?? null,
      plan.runtime
    )
  }

  private async observeHealth(): Promise<RuntimeHealthObservation> {
    try {
      const response = await this.client.health()
      const body = response.body
      const runtimeContract = typeof body.runtime_contract === 'string'
        ? body.runtime_contract
        : null
      const runtimeGeneration = typeof body.runtime_generation === 'string'
        ? body.runtime_generation
        : null
      const recoveryContract = typeof body.recovery_contract === 'string'
        ? body.recovery_contract
        : null
      const compatible =
        runtimeContract === REQUIRED_RUNTIME_CONTRACT &&
        recoveryContract === REQUIRED_RECOVERY_CONTRACT

      this.lastHealth = {
        reachable: true,
        compatible,
        runtimeContract,
        runtimeGeneration,
        recoveryContract
      }
      return this.lastHealth
    } catch {
      this.lastHealth = {
        reachable: false,
        compatible: false,
        runtimeContract: null,
        runtimeGeneration: null,
        recoveryContract: null
      }
      return this.lastHealth
    }
  }

  private async healthOnline(): Promise<boolean> {
    return (await this.observeHealth()).compatible
  }

  private snapshot(
    phase: WorkstationServerProcessState['phase'],
    online: boolean,
    pid: number | null,
    runtime: WorkstationServerRuntimeKind
  ): WorkstationServerProcessState {
    const workstationRoot = this.managedRoot ?? this.resolveWorkstationRoot()
    const rootReleasePath = workstationRoot ? join(workstationRoot, ROOT_RELEASE_EXE) : null

    return {
      phase,
      online,
      serverReachable: this.lastHealth.reachable,
      compatible: this.lastHealth.compatible,
      managedByPortal: this.managedChild !== null,
      pid,
      runtime,
      bind: WORKSTATION_BIND,
      workstationRoot,
      runtimeContract: this.lastHealth.runtimeContract,
      runtimeGeneration: this.lastHealth.runtimeGeneration,
      recoveryContract: this.lastHealth.recoveryContract,
      rootReleasePath,
      rootReleaseReady: Boolean(rootReleasePath && existsSync(rootReleasePath)),
      startedUtc: this.startedUtc,
      observedUtc: nowUtc(),
      lastError: this.lastError
    }
  }

  private resolveLaunchPlan(forceCurrentSource = false): LaunchPlan | null {
    const root = this.resolveWorkstationRoot()
    if (!root) return null

    const rootRelease = join(root, ROOT_RELEASE_EXE)
    const embedded = existsSync(rootRelease)
      ? rootRelease
      : forceCurrentSource
        ? undefined
        : this.embeddedRuntimeCandidates().find(candidate => existsSync(candidate))

    if (embedded) {
      return {
        command: embedded,
        args: [
          'workstation',
          'serve',
          '--bind',
          WORKSTATION_BIND,
          '--root',
          root
        ],
        cwd: root,
        root,
        runtime: 'EMBEDDED'
      }
    }

    // Development fallback always compiles the current Workstation source.
    // It intentionally does NOT launch target/release or target/debug binaries,
    // because those may predate the current recovery contract.
    return {
      command: process.env.CARGO?.trim() || 'cargo',
      args: [
        'run',
        '--quiet',
        '--manifest-path',
        join(root, 'headless', 'Cargo.toml'),
        '--bin',
        'vertex',
        '--',
        'workstation',
        'serve',
        '--bind',
        WORKSTATION_BIND,
        '--root',
        root
      ],
      cwd: root,
      root,
      runtime: 'SIBLING_CARGO',
      env: {
        CARGO_TARGET_DIR: join(root, 'runtime', 'portal-managed-cargo-target')
      }
    }
  }

  /**
   * 000083V5:
   * Build the current headless Workstation as a release binary and publish it to
   * the project root.  This happens only after the Human explicitly presses
   * START/REPLACE.  Cargo and the final server process are both spawned with
   * windowsHide=true and no inherited stdio, so no persistent console window is
   * required for Portal-managed operation.
   */
  private async ensureRootReleaseBinary(forceRebuild: boolean): Promise<string> {
    const root = this.resolveWorkstationRoot()
    if (!root) throw new Error('WORKSTATION_ROOT_NOT_FOUND')

    const destination = join(root, ROOT_RELEASE_EXE)
    const shouldBuild =
      forceRebuild ||
      !existsSync(destination) ||
      this.workstationSourcesNewerThan(destination, root)

    if (!shouldBuild) return destination

    const cargo = process.env.CARGO?.trim() || 'cargo'
    const targetDir = join(root, 'runtime', ROOT_RELEASE_TARGET_DIR)

    await new Promise<void>((resolveBuild, rejectBuild) => {
      const build = spawn(
        cargo,
        [
          'build',
          '--release',
          '--manifest-path',
          join(root, 'headless', 'Cargo.toml'),
          '--bin',
          'vertex',
          '--target-dir',
          targetDir
        ],
        {
          cwd: root,
          windowsHide: true,
          shell: false,
          stdio: 'ignore',
          env: {
            ...process.env,
            CARGO_TARGET_DIR: targetDir,
            VERTEX_WORKSTATION_ROOT: root
          }
        }
      )

      let settled = false
      const timer = setTimeout(() => {
        if (settled) return
        settled = true
        try { build.kill() } catch { /* fail closed below */ }
        rejectBuild(new Error('WORKSTATION_RELEASE_BUILD_TIMEOUT'))
      }, RELEASE_BUILD_TIMEOUT_MS)

      build.once('error', error => {
        if (settled) return
        settled = true
        clearTimeout(timer)
        rejectBuild(new Error(`WORKSTATION_RELEASE_BUILD_SPAWN:${error.message}`))
      })

      build.once('exit', code => {
        if (settled) return
        settled = true
        clearTimeout(timer)
        if (code === 0) resolveBuild()
        else rejectBuild(new Error(`WORKSTATION_RELEASE_BUILD_EXIT:${code ?? 'NULL'}`))
      })
    })

    const built = join(targetDir, 'release', 'vertex.exe')
    if (!existsSync(built)) {
      throw new Error(`WORKSTATION_RELEASE_BINARY_MISSING:${built}`)
    }

    this.publishRootReleaseBinary(built, destination)
    return destination
  }

  private workstationSourcesNewerThan(binary: string, root: string): boolean {
    const binaryMtime = statSync(binary).mtimeMs
    const roots = [
      join(root, 'headless', 'Cargo.toml'),
      join(root, 'Cargo.lock'),
      join(root, 'headless', 'src'),
      join(root, 'headless', 'tests'),
      join(root, 'src-tauri', 'src')
    ]

    const visit = (candidate: string): boolean => {
      if (!existsSync(candidate)) return false
      const stat = statSync(candidate)
      if (stat.isFile()) return stat.mtimeMs > binaryMtime
      if (!stat.isDirectory()) return false

      for (const entry of readdirSync(candidate, { withFileTypes: true })) {
        if (entry.name === 'target' || entry.name === 'runtime' || entry.name === '.git') continue
        if (visit(join(candidate, entry.name))) return true
      }
      return false
    }

    return roots.some(visit)
  }

  private publishRootReleaseBinary(source: string, destination: string): void {
    const next = `${destination}.next`
    const previous = `${destination}.previous`

    try { if (existsSync(next)) unlinkSync(next) } catch { /* retry below */ }
    try { if (existsSync(previous)) unlinkSync(previous) } catch { /* retry below */ }

    copyFileSync(source, next)

    let movedPrevious = false
    try {
      if (existsSync(destination)) {
        renameSync(destination, previous)
        movedPrevious = true
      }

      renameSync(next, destination)

      if (movedPrevious && existsSync(previous)) {
        unlinkSync(previous)
      }
    } catch (error) {
      try {
        if (!existsSync(destination) && existsSync(previous)) {
          renameSync(previous, destination)
        }
      } catch {
        // Preserve the original publication error; recovery is fail-closed.
      }
      throw error
    } finally {
      try { if (existsSync(next)) unlinkSync(next) } catch { /* no-op */ }
    }
  }

  private async listenerUsesExecutable(expectedExecutable: string): Promise<boolean> {
    const pid = await this.findLoopbackListenerPid()
    if (!pid || pid === process.pid) return false

    const identity = await this.inspectWindowsProcess(pid)
    if (!identity.executablePath) return false

    return resolve(identity.executablePath).toLowerCase() ===
      resolve(expectedExecutable).toLowerCase()
  }

  private async replaceValidatedLegacyListener(): Promise<void> {
    const root = this.resolveWorkstationRoot()
    if (!root) {
      throw new Error('WORKSTATION_ROOT_NOT_FOUND')
    }

    const pid = await this.findLoopbackListenerPid()
    if (!pid || pid === process.pid) {
      throw new Error('WORKSTATION_LISTENER_PID_INVALID')
    }

    const identity = await this.inspectWindowsProcess(pid)
    if (!this.legacyProcessAllowed(identity.executablePath, identity.commandLine, root)) {
      throw new Error(
        `WORKSTATION_LISTENER_IDENTITY_REJECTED pid=${pid} exe=${identity.executablePath || 'UNKNOWN'}`
      )
    }

    // Human clicked REPLACE LEGACY. Only after exact identity validation is the process terminated.
    try {
      process.kill(pid)
    } catch (error) {
      throw new Error(`WORKSTATION_LISTENER_TERMINATE_FAILED pid=${pid}:${error instanceof Error ? error.message : String(error)}`)
    }

    if (this.managedChild?.pid === pid) {
      this.managedChild = null
    }

    const deadline = Date.now() + LEGACY_REPLACE_TIMEOUT_MS
    while (Date.now() < deadline) {
      const health = await this.observeHealth()
      if (!health.reachable) {
        this.lastError = null
        return
      }
      await sleep(START_POLL_MS)
    }

    throw new Error(`WORKSTATION_LISTENER_DID_NOT_EXIT pid=${pid}`)
  }

  private async findLoopbackListenerPid(): Promise<number | null> {
    if (process.platform !== 'win32') {
      throw new Error('WORKSTATION_LEGACY_REPLACE_WINDOWS_ONLY')
    }

    const { stdout } = await execFileAsync(
      'netstat.exe',
      ['-ano', '-p', 'tcp'],
      {
        windowsHide: true,
        timeout: 4_000,
        encoding: 'utf8'
      }
    )

    for (const line of stdout.split(/\r?\n/)) {
      const parts = line.trim().split(/\s+/)
      if (parts.length < 5) continue
      if (parts[0].toUpperCase() !== 'TCP') continue
      if (parts[1] !== WORKSTATION_BIND) continue
      if (parts[3].toUpperCase() !== 'LISTENING') continue

      const pid = Number.parseInt(parts[4], 10)
      return Number.isSafeInteger(pid) && pid > 0 ? pid : null
    }

    return null
  }

  private async inspectWindowsProcess(
    pid: number
  ): Promise<{ executablePath: string; commandLine: string }> {
    const script = [
      `$p = Get-CimInstance Win32_Process -Filter 'ProcessId = ${pid}'`,
      `if ($null -eq $p) { exit 3 }`,
      `[Console]::Out.WriteLine($p.ExecutablePath)`,
      `[Console]::Out.WriteLine($p.CommandLine)`
    ].join('; ')

    const { stdout } = await execFileAsync(
      'powershell.exe',
      ['-NoProfile', '-NonInteractive', '-Command', script],
      {
        windowsHide: true,
        timeout: 4_000,
        encoding: 'utf8'
      }
    )

    const lines = stdout.split(/\r?\n/)
    return {
      executablePath: (lines.shift() ?? '').trim(),
      commandLine: lines.join(' ').trim()
    }
  }

  private legacyProcessAllowed(
    executablePath: string,
    commandLine: string,
    workstationRoot: string
  ): boolean {
    if (!executablePath || !commandLine) return false

    const executable = resolve(executablePath)
    const name = basename(executable).toLowerCase()
    if (name !== 'vertex.exe' && name !== 'vertex-workstation.exe') return false

    const allowedRoots = [
      resolve(workstationRoot),
      resolve(join(process.resourcesPath, 'workstation-server')),
      resolve(join(app.getAppPath(), 'resources', 'workstation-server'))
    ]

    const pathAllowed = allowedRoots.some(root => this.pathInside(executable, root))
    if (!pathAllowed) return false

    const normalizedCommand = commandLine.toLowerCase()
    return (
      normalizedCommand.includes('workstation') &&
      normalizedCommand.includes('serve') &&
      normalizedCommand.includes('127.0.0.1:47832')
    )
  }

  private pathInside(candidate: string, root: string): boolean {
    const normalizedCandidate = resolve(candidate).toLowerCase()
    const normalizedRoot = resolve(root).toLowerCase()
    return normalizedCandidate === normalizedRoot ||
      normalizedCandidate.startsWith(normalizedRoot + sep.toLowerCase())
  }

  private embeddedRuntimeCandidates(): string[] {
    const names = ['vertex.exe', 'vertex-workstation.exe']
    const roots = [
      join(process.resourcesPath, 'workstation-server'),
      join(app.getAppPath(), 'resources', 'workstation-server')
    ]

    return roots.flatMap(root => names.map(name => join(root, name)))
  }

  private resolveWorkstationRoot(): string | null {
    const explicit = process.env.VERTEX_WORKSTATION_ROOT?.trim()
    if (explicit && workstationRootValid(explicit)) {
      return resolve(explicit)
    }

    const seeds = [
      app.getAppPath(),
      process.cwd(),
      dirname(process.execPath),
      process.resourcesPath
    ]

    const candidates: string[] = []

    for (const seed of seeds) {
      let cursor = resolve(seed)

      for (let depth = 0; depth < ROOT_SCAN_DEPTH; depth += 1) {
        candidates.push(cursor)
        candidates.push(join(cursor, 'vertex_workstation'))

        const parent = dirname(cursor)
        if (parent === cursor) break
        cursor = parent
      }
    }

    return uniqueExistingRoots(candidates)[0] ?? null
  }
}

export const workstationProcessController = new WorkstationProcessController()
