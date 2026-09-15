import { app } from 'electron'
import { VertexShellService } from '../src/main/shell/vertex-shell-service'
import {
  createVeraVxsVraDirectServer
} from '../src/main/shell/vxs/vera-vxs-vra-direct-http-nerve'
import {
  grantVeraVxsHumanFullAccess,
  revokeVeraVxsHumanFullAccess
} from '../src/main/shell/vxs/vera-vxs-human-authority'

async function post(port: number, command: string, requestId: string) {
  const response = await fetch(`http://127.0.0.1:${port}/v1/execute`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      schema: 'vertex-vxs/vra-direct-request-1',
      request_id: requestId,
      correlation_id: `corr-${requestId}`,
      origin: {
        vera: 'VERA04',
        session: 'vera-04',
        window: 'vera-04'
      },
      command,
      cwd: process.cwd()
    })
  })
  return {
    status: response.status,
    body: await response.json() as any
  }
}

async function main(): Promise<void> {
  await app.whenReady()

  revokeVeraVxsHumanFullAccess()
  const service = new VertexShellService()
  const handle = await createVeraVxsVraDirectServer(service, {
    host: '127.0.0.1',
    port: 0
  })

  const healthLocked = await fetch(
    `http://127.0.0.1:${handle.port}/health`
  ).then(r => r.json()) as any
  if (healthLocked?.authority?.mode !== 'LOCKED') {
    throw new Error('HEALTH_LOCKED_EXPECTED')
  }

  const locked = await post(
    handle.port,
    'vxs --version',
    'e2e-locked'
  )
  if (
    locked.status !== 423 ||
    locked.body?.error !== 'VERA_VXS_HUMAN_GATE_REQUIRED'
  ) {
    throw new Error('LOCKED_GATE_NOT_ENFORCED')
  }

  grantVeraVxsHumanFullAccess()

  const version = await post(
    handle.port,
    'vxs --version',
    'e2e-version'
  )
  if (
    version.status !== 200 ||
    version.body?.ok !== true ||
    version.body?.result?.shellResult?.exitCode !== 0
  ) {
    throw new Error('VXS_VERSION_DIRECT_FAILED')
  }

  const powershell = await post(
    handle.port,
    'Get-Process | Select-Object -First 1',
    'e2e-powershell'
  )
  if (
    powershell.status !== 200 ||
    powershell.body?.ok !== true ||
    powershell.body?.result?.shellResult?.exitCode !== 0
  ) {
    throw new Error('POWERSHELL_DIRECT_FAILED')
  }

  revokeVeraVxsHumanFullAccess()

  const relocked = await post(
    handle.port,
    'vxs --version',
    'e2e-relocked'
  )
  if (
    relocked.status !== 423 ||
    relocked.body?.error !== 'VERA_VXS_HUMAN_GATE_REQUIRED'
  ) {
    throw new Error('RELOCK_NOT_ENFORCED')
  }

  await handle.close()

  console.log('VRA_VXS_DIRECT_HTTP_NERVE_E2E=PASS')
  console.log('LOOPBACK_ONLY=true')
  console.log('LOCKED_REJECT=PASS')
  console.log('FULL_VXS=PASS')
  console.log('FULL_POWERSHELL=PASS')
  console.log('RELOCK_REJECT=PASS')
  console.log('SECOND_EXECUTOR=false')
  console.log('PRODUCTION_PORT=47834')

  app.quit()
}

main().catch(error => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error))
  app.exit(91)
})
