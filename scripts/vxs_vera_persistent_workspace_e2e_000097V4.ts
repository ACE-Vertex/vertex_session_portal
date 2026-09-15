import { app, BrowserWindow } from 'electron'
import {
  beginVeraVxsActivity,
  completeVeraVxsActivity,
  getVeraVxsActivity
} from '../src/main/shell/vxs/vera-vxs-activity'

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

async function snapshot(window: BrowserWindow): Promise<Record<string, unknown>> {
  return await window.webContents.executeJavaScript(`(() => {
    const root = document.getElementById('vertex-shell-internal-unit')
    const shadow = root?.shadowRoot
    const sessionTabs = shadow?.getElementById('vxs-vera-session-tabs')
    const veraTabs = Array.from(sessionTabs?.querySelectorAll('.vxsVeraPersistentTab') || [])
    const workspaces = Array.from(shadow?.querySelectorAll('.vxsVeraWorkspace') || [])
    const workspace = workspaces.find(pane => pane.dataset.session === 'vera-04')
    const nativeCwd = shadow?.querySelector('.cwdRow')
    const nativeOutput = shadow?.querySelector('.output')
    const composer = shadow?.querySelector('.composer')
    const runs = Array.from(workspace?.querySelectorAll('.vxsVeraRun') || [])
    return {
      hostVisible: root?.style.display !== 'none',
      tabCount: veraTabs.length,
      tabText: veraTabs.map(tab => tab.textContent || ''),
      tabActive: veraTabs.map(tab => tab.classList.contains('active')),
      workspaceCount: workspaces.length,
      workspaceHidden: workspace?.hidden ?? null,
      runCount: runs.length,
      runInputs: runs.map(run => run.querySelector('.vxsVeraRunInput')?.textContent || ''),
      runOutputs: runs.map(run => run.querySelector('.vxsVeraRunOutput')?.textContent || ''),
      runStates: runs.map(run => run.querySelector('.vxsVeraRunState')?.textContent || ''),
      nativeCwdDisplay: nativeCwd?.style.display ?? null,
      nativeOutputDisplay: nativeOutput?.style.display ?? null,
      composerDisplay: composer?.style.display ?? null
    }
  })()`, true)
}

async function clickNative(window: BrowserWindow): Promise<void> {
  await window.webContents.executeJavaScript(`(() => {
    const root = document.getElementById('vertex-shell-internal-unit')
    const shadow = root?.shadowRoot
    const button = shadow?.querySelector('.tabs .tab')
    if (!button) throw new Error('NATIVE_TAB_NOT_FOUND')
    button.click()
    return true
  })()`, true)
}

async function clickVera(window: BrowserWindow): Promise<void> {
  await window.webContents.executeJavaScript(`(() => {
    const root = document.getElementById('vertex-shell-internal-unit')
    const shadow = root?.shadowRoot
    const button = shadow?.querySelector('#vxs-vera-session-tabs .vxsVeraPersistentTab[data-session="vera-04"]')
    if (!button) throw new Error('VERA_TAB_NOT_FOUND')
    button.click()
    return true
  })()`, true)
}

async function main(): Promise<void> {
  await app.whenReady()
  const window = new BrowserWindow({ show: false, webPreferences: { contextIsolation: false, sandbox: false } })
  await window.loadURL('data:text/html,<html><body></body></html>')
  await window.webContents.executeJavaScript(`(() => {
    const root = document.createElement('div')
    root.id = 'vertex-shell-internal-unit'
    root.style.display = 'none'
    document.body.appendChild(root)
    window.__VERTEX_SHELL_SET_VISIBILITY__ = visible => {
      root.style.display = visible ? '' : 'none'
      return Boolean(visible)
    }
    const shadow = root.attachShadow({ mode: 'open' })
    shadow.innerHTML =
      '<div class="vsh collapsed">' +
      '<header class="head"><div class="actions"><span class="status">READY</span></div></header>' +
      '<div class="tabsRow"><div class="tabs"><button class="tab active">SHELL 1</button></div><button class="tabAdd">+</button></div>' +
      '<div class="cwdRow">CWD</div>' +
      '<pre class="output">native-output</pre>' +
      '<div class="composer">composer</div>' +
      '</div>'
    return true
  })()`, true)

  beginVeraVxsActivity({
    originVera: 'VERA04', originSession: 'vera-04', command: 'vxs ps engine',
    requestId: 'persistent-run-1', correlationId: 'persistent-corr-1'
  })
  await delay(140)
  const firstRunning = await snapshot(window)
  if (firstRunning.hostVisible !== true) throw new Error('FIRST_REQUEST_DID_NOT_OPEN_VXS')
  if (firstRunning.tabCount !== 1 || firstRunning.workspaceCount !== 1) throw new Error('FIRST_REQUEST_DID_NOT_CREATE_ONE_WORKSPACE')
  if (!String((firstRunning.tabText as string[])[0]).includes('VERA04 · S04')) throw new Error('FIRST_TAB_LABEL_INVALID')
  if ((firstRunning.tabActive as boolean[])[0] !== true) throw new Error('FIRST_VERA_TAB_NOT_ACTIVE')
  if (firstRunning.workspaceHidden !== false) throw new Error('FIRST_WORKSPACE_NOT_VISIBLE')
  if (!(firstRunning.runInputs as string[])[0]?.includes('vxs ps engine')) throw new Error('FIRST_INPUT_NOT_VISIBLE')
  if (!(firstRunning.runStates as string[])[0]?.includes('RUNNING')) throw new Error('FIRST_RUN_STATE_NOT_RUNNING')

  completeVeraVxsActivity('persistent-run-1', {
    streamEvents: [{ kind: 'stdout', chunk: 'PowerShell Engine 7.6.6\n' }],
    shellResult: { exitCode: 0, output: 'PowerShell Engine 7.6.6\n' }
  })
  await delay(140)
  const firstComplete = await snapshot(window)
  if (!(firstComplete.runOutputs as string[])[0]?.includes('PowerShell Engine 7.6.6')) throw new Error('FIRST_RESULT_NOT_VISIBLE')
  if (!(firstComplete.runStates as string[])[0]?.includes('OK · EXIT 0')) throw new Error('FIRST_RESULT_STATE_INVALID')

  await clickNative(window)
  await delay(80)
  const switched = await snapshot(window)
  if (switched.workspaceHidden !== true) throw new Error('NATIVE_TAB_DID_NOT_HIDE_VERA_WORKSPACE')
  if (switched.nativeCwdDisplay === 'none' || switched.composerDisplay === 'none') throw new Error('NATIVE_WORKSPACE_NOT_RESTORED')
  if (switched.tabCount !== 1) throw new Error('VERA_TAB_DID_NOT_PERSIST_AFTER_SWITCH')

  beginVeraVxsActivity({
    originVera: 'VERA04', originSession: 'vera-04', command: 'Get-Process | Select-Object -First 1',
    requestId: 'persistent-run-2', correlationId: 'persistent-corr-2'
  })
  await delay(140)
  const secondRunning = await snapshot(window)
  if (secondRunning.tabCount !== 1 || secondRunning.workspaceCount !== 1) throw new Error('SECOND_REQUEST_CREATED_DUPLICATE_TAB')
  if (secondRunning.runCount !== 2) throw new Error('SECOND_REQUEST_DID_NOT_APPEND_HISTORY')
  if (!(secondRunning.runInputs as string[])[1]?.includes('Get-Process')) throw new Error('SECOND_INPUT_NOT_RECORDED')
  if (secondRunning.workspaceHidden !== true) throw new Error('SECOND_REQUEST_STOLE_HUMAN_FOCUS')

  completeVeraVxsActivity('persistent-run-2', {
    streamEvents: [{ kind: 'stdout', chunk: 'pwsh 53296\n' }],
    shellResult: { exitCode: 0 }
  })
  await delay(100)
  await clickVera(window)
  await delay(80)
  const reopened = await snapshot(window)
  if (reopened.workspaceHidden !== false) throw new Error('HUMAN_COULD_NOT_REOPEN_VERA_TAB')
  if ((reopened.tabActive as boolean[])[0] !== true) throw new Error('REOPENED_VERA_TAB_NOT_ACTIVE')
  if (reopened.runCount !== 2) throw new Error('WORKSPACE_HISTORY_NOT_PERSISTENT')
  if (!(reopened.runOutputs as string[])[1]?.includes('pwsh 53296')) throw new Error('SECOND_RESULT_NOT_VISIBLE')

  const snapshotState = getVeraVxsActivity()
  if (snapshotState.originVera !== 'VERA04' || snapshotState.originSession !== 'vera-04' || snapshotState.exitCode !== 0) {
    throw new Error('ACTIVITY_PROVENANCE_OR_RESULT_INVALID')
  }

  console.log('VXS_VERA_PERSISTENT_WORKSPACE_E2E_000097V4=PASS')
  console.log('FIRST_REQUEST_OPENS_VXS=PASS')
  console.log('FIRST_REQUEST_OPENS_DEDICATED_TAB=PASS')
  console.log('INPUT_VISIBLE_DURING_RUNNING=PASS')
  console.log('RESULT_VISIBLE_AFTER_COMPLETE=PASS')
  console.log('NATIVE_TAB_CAN_SWITCH_AWAY=PASS')
  console.log('VERA_TAB_PERSISTS_AFTER_SWITCH=PASS')
  console.log('SECOND_REQUEST_REUSES_SAME_TAB=PASS')
  console.log('SECOND_REQUEST_APPENDS_HISTORY=PASS')
  console.log('HUMAN_CAN_REOPEN_VERA_TAB=PASS')
  console.log('SECOND_EXECUTOR=false')
  window.destroy()
  app.quit()
}

void main().catch(error => {
  console.error(error instanceof Error ? error.stack || error.message : String(error))
  app.exit(91)
})
