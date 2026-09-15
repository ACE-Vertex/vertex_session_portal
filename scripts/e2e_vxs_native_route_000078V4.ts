import { app } from 'electron'
import { VertexShellService } from '../src/main/shell/vertex-shell-service'

interface SinkEvent {
  commandId: string
  kind: string
  chunk: string
  at: string
}

interface CaseResult {
  command: string
  backend: string
  exitCode: number
  providerNative: boolean
  nativeSchema: boolean
  organ: string | null
  routeEvidence: boolean
  stdout: string
  stderr: string
}

function parseNativePayload(text: string): any | null {
  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
  for (const line of lines) {
    if (!line.startsWith('{')) continue
    try {
      const value = JSON.parse(line)
      if (value?.schema === 'vertex-vxs/native-organ-output-1') return value
    } catch {
      // ignore non-JSON lines
    }
  }
  return null
}

async function runCase(
  service: VertexShellService,
  command: string,
  cwd: string
): Promise<CaseResult> {
  const events: SinkEvent[] = []
  const result = await service.execute(
    { command, cwd },
    (event: any) => {
      events.push({
        commandId: String(event.commandId ?? ''),
        kind: String(event.kind ?? ''),
        chunk: String(event.chunk ?? ''),
        at: String(event.at ?? '')
      })
    }
  )

  const stdout = events
    .filter(event => event.kind === 'stdout')
    .map(event => event.chunk)
    .join('')
  const stderr = events
    .filter(event => event.kind === 'stderr')
    .map(event => event.chunk)
    .join('')
  const system = events
    .filter(event => event.kind === 'system')
    .map(event => event.chunk)
    .join('\n')

  const payload = parseNativePayload(stdout)

  return {
    command,
    backend: result.backend,
    exitCode: result.exitCode,
    providerNative:
      result.backend.startsWith('VXS_NATIVE_') &&
      system.includes('Provider: NATIVE') &&
      system.includes('NATIVE_PROVIDER_AVAILABLE'),
    nativeSchema: payload?.schema === 'vertex-vxs/native-organ-output-1',
    organ: typeof payload?.organ === 'string' ? payload.organ : null,
    routeEvidence: system.includes('VXS ROUTE'),
    stdout,
    stderr
  }
}

async function main(): Promise<void> {
  await app.whenReady()

  const root = process.env.VXS_E2E_ROOT
  if (!root) {
    throw new Error('VXS_E2E_ROOT_REQUIRED')
  }

  // Deliberately poison PATH after Electron has started.
  // Native route uses an absolute Rust binary path. Any fallback attempt to
  // "pwsh.exe" should fail, making this a stronger Native-only E2E proof.
  process.env.PATH = ''

  const service = new VertexShellService()
  const targetFile = `${root}\\package.json`
  const targetDir = `${root}\\src\\main\\shell\\vxs`

  const commands = [
    'vxs system observe',
    `vxs fs exists "${targetFile}"`,
    `vxs fs meta "${targetFile}"`,
    `vxs fs list "${targetDir}"`
  ]

  const cases: CaseResult[] = []
  for (const command of commands) {
    cases.push(await runCase(service, command, root))
  }

  const expectations = [
    { organ: 'system' },
    { organ: 'filesystem' },
    { organ: 'filesystem' },
    { organ: 'filesystem' }
  ]

  const allPass = cases.every((item, index) =>
    item.exitCode === 0 &&
    item.providerNative &&
    item.nativeSchema &&
    item.organ === expectations[index].organ &&
    item.routeEvidence &&
    !item.stderr
  )

  const report = {
    schema: 'vertex-vxs/e2e-native-route-smoke-1',
    state: allPass ? 'PASS' : 'FAIL',
    path_poisoned: process.env.PATH === '',
    powerShell_available_via_path: false,
    command_count: cases.length,
    cases: cases.map(item => ({
      command: item.command,
      backend: item.backend,
      exitCode: item.exitCode,
      providerNative: item.providerNative,
      nativeSchema: item.nativeSchema,
      organ: item.organ,
      routeEvidence: item.routeEvidence,
      stdout: item.stdout.slice(0, 4096),
      stderr: item.stderr.slice(0, 4096)
    }))
  }

  console.log('VXS_E2E_RESULT=' + JSON.stringify(report))
  app.exit(allPass ? 0 : 7)
}

main().catch(error => {
  console.error(
    'VXS_E2E_FATAL=' +
      (error instanceof Error ? `${error.name}:${error.message}` : String(error))
  )
  app.exit(9)
})
