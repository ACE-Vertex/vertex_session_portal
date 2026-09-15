import { app, BrowserWindow } from 'electron'
import {
  beginVeraVxsActivity,
  completeVeraVxsActivity,
  failVeraVxsActivity,
  getVeraVxsActivity
} from '../src/main/shell/vxs/vera-vxs-activity'

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function badge(window: BrowserWindow): Promise<Record<string, string | null>> {
  return await window.webContents.executeJavaScript(`(() => {
    const root = document.getElementById('vertex-shell-internal-unit')
    const shadow = root?.shadowRoot
    const chip = shadow?.getElementById('vxs-vera-activity')
    return {
      text: chip?.textContent || null,
      state: chip?.dataset?.state || null,
      command: chip?.querySelector('.vxsVeraCommand')?.textContent || null
    }
  })()`, true)
}

async function main(): Promise<void> {
  await app.whenReady()

  const window = new BrowserWindow({
    show: false,
    webPreferences: {
      contextIsolation: false,
      sandbox: false
    }
  })

  await window.loadURL('data:text/html,<html><body></body></html>')
  await window.webContents.executeJavaScript(`(() => {
    const root = document.createElement('div')
    root.id = 'vertex-shell-internal-unit'
    document.body.appendChild(root)
    const shadow = root.attachShadow({ mode: 'open' })
    shadow.innerHTML =
      '<div class="vsh"><header class="head"><div class="actions"><span class="status">READY</span></div></header></div>'
    return true
  })()`, true)

  beginVeraVxsActivity({
    originVera: 'VERA04',
    command: 'vxs --version',
    requestId: 'activity-e2e-request',
    correlationId: 'activity-e2e-correlation'
  })
  await delay(120)

  const running = getVeraVxsActivity()
  if (running.state !== 'RUNNING' || running.originVera !== 'VERA04') {
    throw new Error('ACTIVITY_RUNNING_STATE_INVALID')
  }
  const runningBadge = await badge(window)
  if (runningBadge.state !== 'RUNNING') {
    throw new Error('ACTIVITY_RUNNING_BADGE_MISSING')
  }
  if (!String(runningBadge.text || '').includes('VERA04')) {
    throw new Error('ACTIVITY_RUNNING_ORIGIN_NOT_VISIBLE')
  }
  if (runningBadge.command !== 'vxs --version') {
    throw new Error('ACTIVITY_RUNNING_COMMAND_NOT_VISIBLE')
  }

  completeVeraVxsActivity('activity-e2e-request')
  await delay(120)
  const succeeded = getVeraVxsActivity()
  const succeededBadge = await badge(window)
  if (succeeded.state !== 'SUCCEEDED' || succeededBadge.state !== 'SUCCEEDED') {
    throw new Error('ACTIVITY_SUCCEEDED_STATE_INVALID')
  }

  beginVeraVxsActivity({
    originVera: 'VERA04',
    command: 'token=super-secret-value Get-Process',
    requestId: 'activity-e2e-fail',
    correlationId: 'activity-e2e-correlation-fail'
  })
  failVeraVxsActivity('activity-e2e-fail', new Error('synthetic failure'))
  await delay(120)

  const failed = getVeraVxsActivity()
  const failedBadge = await badge(window)
  if (failed.state !== 'FAILED' || failedBadge.state !== 'FAILED') {
    throw new Error('ACTIVITY_FAILED_STATE_INVALID')
  }
  if (String(failed.command || '').includes('super-secret-value')) {
    throw new Error('ACTIVITY_COMMAND_REDACTION_FAILED')
  }

  console.log('VRA_VXS_ACTIVITY_VISUAL_E2E_000092V4H1=PASS')
  console.log('RUNNING_VISIBLE=PASS')
  console.log('SUCCEEDED_VISIBLE=PASS')
  console.log('FAILED_VISIBLE=PASS')
  console.log('COMMAND_REDACTION=PASS')
  console.log('SECOND_EXECUTOR=false')

  window.destroy()
  app.quit()
}

void main().catch(error => {
  console.error(error instanceof Error ? error.stack || error.message : String(error))
  app.exit(91)
})
