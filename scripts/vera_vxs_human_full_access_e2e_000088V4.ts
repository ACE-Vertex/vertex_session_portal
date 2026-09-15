import { app, BrowserWindow } from 'electron'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { VertexShellService } from '../src/main/shell/vertex-shell-service'
import { registerVeraVxsProductionIpc } from '../src/main/ipc/register-vertex-shell-ipc'
import {
  grantVeraVxsHumanFullAccess,
  revokeVeraVxsHumanFullAccess
} from '../src/main/shell/vxs/vera-vxs-human-authority'

const receiptPath = process.env.VERA_VXS_GATE_E2E_RECEIPT
const preloadPath = process.env.VERA_VXS_PRELOAD_PATH

function request(command: string, id: string) {
  return {
    schema: 'vertex-vxs/vera-request-1' as const,
    requestId: id,
    correlationId: `corr-${id}`,
    origin: {
      vera: 'VERA04',
      session: 'vera-04',
      window: 'vera-04'
    },
    authority: 'AUTO_SAFE' as const,
    command,
    cwd: process.cwd()
  }
}

async function rendererInvoke(win: BrowserWindow, value: unknown): Promise<any> {
  return await win.webContents.executeJavaScript(
    `window.veraVxs.execute(${JSON.stringify(value)})`,
    true
  )
}

async function rendererReject(win: BrowserWindow, value: unknown): Promise<string> {
  return await win.webContents.executeJavaScript(
    `(async () => {
      try {
        await window.veraVxs.execute(${JSON.stringify(value)})
        return 'UNEXPECTED_ACCEPT'
      } catch (error) {
        return String(error && error.message ? error.message : error)
      }
    })()`,
    true
  )
}

async function main(): Promise<void> {
  if (!receiptPath) throw new Error('VERA_VXS_GATE_E2E_RECEIPT_REQUIRED')
  if (!preloadPath) throw new Error('VERA_VXS_PRELOAD_PATH_REQUIRED')

  await app.whenReady()

  revokeVeraVxsHumanFullAccess()

  const service = new VertexShellService()
  registerVeraVxsProductionIpc(service)

  const win = new BrowserWindow({
    show: false,
    webPreferences: {
      preload: path.resolve(preloadPath),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })

  await win.loadURL('data:text/html,<html><body>VERA VXS HUMAN GATE E2E</body></html>')

  const preloadReady = await win.webContents.executeJavaScript(
    `Boolean(window.veraVxs && typeof window.veraVxs.execute === 'function')`,
    true
  )
  if (!preloadReady) throw new Error('VERA_VXS_PRELOAD_API_NOT_EXPOSED')

  const lockedRequest = request('vxs --version', 'gate-locked-before')
  const lockedBefore = await rendererReject(win, lockedRequest)
  if (!lockedBefore.includes('VERA_VXS_HUMAN_GATE_REQUIRED')) {
    throw new Error('LOCKED_GATE_DID_NOT_REJECT:' + lockedBefore)
  }

  grantVeraVxsHumanFullAccess()

  const versionResult = await rendererInvoke(
    win,
    request('vxs --version', 'gate-full-vxs-version')
  )
  if (versionResult?.shellResult?.exitCode !== 0) {
    throw new Error('FULL_VXS_VERSION_FAILED')
  }

  const powershellResult = await rendererInvoke(
    win,
    request('Get-Process | Select-Object -First 1', 'gate-full-powershell-read')
  )
  if (powershellResult?.shellResult?.exitCode !== 0) {
    throw new Error('FULL_POWERSHELL_READ_FAILED')
  }

  revokeVeraVxsHumanFullAccess()

  const lockedAfter = await rendererReject(
    win,
    request('vxs --version', 'gate-locked-after')
  )
  if (!lockedAfter.includes('VERA_VXS_HUMAN_GATE_REQUIRED')) {
    throw new Error('REVOKED_GATE_DID_NOT_REJECT:' + lockedAfter)
  }

  const receipt = {
    schema: 'vertex-vxs/human-full-access-e2e-receipt-1',
    origin: 'VERA04/vera-04/vera-04',
    preload_api: 'window.veraVxs.execute',
    ipc_channel: 'vera-vxs:execute',
    locked_before: true,
    full_vxs_exit_code: versionResult.shellResult.exitCode,
    full_vxs_backend: String(versionResult.shellResult.backend ?? ''),
    full_powershell_exit_code: powershellResult.shellResult.exitCode,
    full_powershell_backend: String(powershellResult.shellResult.backend ?? ''),
    locked_after_revoke: true,
    process_scoped_authority: true,
    human_grant_simulated_in_test: true
  }

  fs.mkdirSync(path.dirname(receiptPath), { recursive: true })
  fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2), 'utf8')

  if (!win.isDestroyed()) win.destroy()
  app.quit()
}

main().catch(error => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error))
  app.exit(91)
})
