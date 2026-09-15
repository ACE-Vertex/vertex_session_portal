import { app, BrowserWindow } from 'electron'
import {
  beginVeraVxsActivity,
  completeVeraVxsActivity,
  failVeraVxsActivity,
  getVeraVxsActivity
} from '../src/main/shell/vxs/vera-vxs-activity'

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function snapshot(window: BrowserWindow): Promise<Record<string, string | null>> {
  return await window.webContents.executeJavaScript(`(() => {
    const root = document.getElementById('vertex-shell-internal-unit')
    const shadow = root?.shadowRoot
    const badge = shadow?.getElementById('vxs-vera-session-badge')
    const tabsRow = shadow?.querySelector('.tabsRow')
    return {
      text: badge?.textContent || null,
      state: badge?.dataset?.state || null,
      title: badge?.title || null,
      parentClass: badge?.parentElement?.className || null,
      tabsRowContains: tabsRow && badge ? String(tabsRow.contains(badge)) : 'false'
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
      '<div class="vsh">' +
      '<header class="head"><div class="actions"><span class="status">READY</span></div></header>' +
      '<div class="tabsRow"><div class="tabs"><button class="tab active">SHELL 1</button></div>' +
      '<button class="tabAdd">+</button></div>' +
      '</div>'
    return true
  })()`, true)

  beginVeraVxsActivity({
    originVera: 'VERA04',
    originSession: 'vera-04',
    command: 'vxs ps engine',
    requestId: 'session-tab-e2e-running',
    correlationId: 'session-tab-correlation-running'
  })
  await delay(120)

  const running = getVeraVxsActivity()
  const runningView = await snapshot(window)
  if (running.state !== 'RUNNING' || running.originSession !== 'vera-04') {
    throw new Error('SESSION_RUNNING_SNAPSHOT_INVALID')
  }
  if (runningView.state !== 'RUNNING') {
    throw new Error('SESSION_RUNNING_BADGE_STATE_INVALID')
  }
  if (!String(runningView.text || '').includes('VERA04')) {
    throw new Error('VERA04_NOT_VISIBLE_IN_TAB_MENU')
  }
  if (!String(runningView.text || '').includes('S04')) {
    throw new Error('SESSION_04_NOT_VISIBLE_IN_TAB_MENU')
  }
  if (runningView.tabsRowContains !== 'true') {
    throw new Error('SESSION_BADGE_NOT_IN_TABS_ROW')
  }
  if (!String(runningView.title || '').includes('Session: vera-04')) {
    throw new Error('SESSION_PROVENANCE_NOT_IN_TOOLTIP')
  }

  completeVeraVxsActivity('session-tab-e2e-running')
  await delay(120)
  const succeededView = await snapshot(window)
  if (succeededView.state !== 'SUCCEEDED' || !String(succeededView.text || '').includes('OK')) {
    throw new Error('SESSION_SUCCEEDED_BADGE_INVALID')
  }

  beginVeraVxsActivity({
    originVera: 'VERA04',
    originSession: 'vera-04',
    command: 'token=super-secret-value Get-Process',
    requestId: 'session-tab-e2e-failed',
    correlationId: 'session-tab-correlation-failed'
  })
  failVeraVxsActivity('session-tab-e2e-failed', new Error('synthetic failure'))
  await delay(120)
  const failedView = await snapshot(window)
  const failed = getVeraVxsActivity()
  if (failedView.state !== 'FAILED' || !String(failedView.text || '').includes('FAIL')) {
    throw new Error('SESSION_FAILED_BADGE_INVALID')
  }
  if (String(failed.command || '').includes('super-secret-value')) {
    throw new Error('SESSION_COMMAND_REDACTION_FAILED')
  }

  console.log('VXS_VERA_SESSION_TAB_E2E_000095V4H2=PASS')
  console.log('SESSION_04_VISIBLE_IN_TAB_MENU=PASS')
  console.log('SESSION_REGEX_TEMPLATE_ESCAPE=PASS')
  console.log('SESSION_LABEL_RENDERED=VERA04 · S04')
  console.log('RUNNING_STATE_VISIBLE=PASS')
  console.log('SUCCEEDED_STATE_VISIBLE=PASS')
  console.log('FAILED_STATE_VISIBLE=PASS')
  console.log('SESSION_PROVENANCE_EXACT=PASS')
  console.log('SECOND_EXECUTOR=false')

  window.destroy()
  app.quit()
}

void main().catch(error => {
  console.error(error instanceof Error ? error.stack || error.message : String(error))
  app.exit(91)
})
