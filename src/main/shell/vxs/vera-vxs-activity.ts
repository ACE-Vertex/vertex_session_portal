import { BrowserWindow } from 'electron'

export const VERA_VXS_ACTIVITY_SCHEMA = 'vertex-vxs/activity-1' as const

export type VeraVxsActivityState =
  | 'IDLE'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'FAILED'

export interface VeraVxsActivitySnapshot {
  schema: typeof VERA_VXS_ACTIVITY_SCHEMA
  state: VeraVxsActivityState
  originVera: string | null
  originSession: string | null
  route: 'VRA→VXS'
  command: string | null
  requestId: string | null
  correlationId: string | null
  startedAt: number | null
  completedAt: number | null
  updatedAt: number
  visibleOutput: string | null
  exitCode: number | null
  error: string | null
}

const MAX_VISIBLE_COMMAND_CHARS = 180
const MAX_VISIBLE_ERROR_CHARS = 240
const MAX_VISIBLE_OUTPUT_CHARS = 32_000

let activity: VeraVxsActivitySnapshot = {
  schema: VERA_VXS_ACTIVITY_SCHEMA,
  state: 'IDLE',
  originVera: null,
  originSession: null,
  route: 'VRA→VXS',
  command: null,
  requestId: null,
  correlationId: null,
  startedAt: null,
  completedAt: null,
  updatedAt: Date.now(),
  visibleOutput: null,
  exitCode: null,
  error: null
}

function redactCommand(command: string): string {
  const redacted = String(command ?? '')
    .replace(
      /(api[_-]?key|token|password|passwd|secret)\s*=\s*("[^"]*"|'[^']*'|\S+)/gi,
      '$1=[REDACTED]'
    )
    .replace(
      /(authorization\s*:\s*bearer)\s+\S+/gi,
      '$1 [REDACTED]'
    )
    .replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, '[REDACTED]')

  return redacted.length <= MAX_VISIBLE_COMMAND_CHARS
    ? redacted
    : `${redacted.slice(0, MAX_VISIBLE_COMMAND_CHARS - 1)}…`
}

function boundedError(value: unknown): string {
  const text = value instanceof Error ? value.message : String(value ?? '')
  return text.length <= MAX_VISIBLE_ERROR_CHARS
    ? text
    : `${text.slice(0, MAX_VISIBLE_ERROR_CHARS - 1)}…`
}

function redactVisibleOutput(value: string): string {
  const redacted = String(value ?? '')
    .replace(
      /(api[_-]?key|token|password|passwd|secret)\s*=\s*("[^"]*"|'[^']*'|\S+)/gi,
      '$1=[REDACTED]'
    )
    .replace(
      /(authorization\s*:\s*bearer)\s+\S+/gi,
      '$1 [REDACTED]'
    )
    .replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, '[REDACTED]')

  return redacted.length <= MAX_VISIBLE_OUTPUT_CHARS
    ? redacted
    : `${redacted.slice(0, MAX_VISIBLE_OUTPUT_CHARS - 1)}…`
}

function visibleResult(result: unknown): {
  output: string | null
  exitCode: number | null
} {
  if (!result || typeof result !== 'object') {
    return { output: null, exitCode: null }
  }

  const record = result as Record<string, unknown>
  const streamEvents = Array.isArray(record.streamEvents)
    ? record.streamEvents
    : []

  const streamText = streamEvents
    .map(event => {
      if (!event || typeof event !== 'object') return ''
      const chunk = (event as Record<string, unknown>).chunk
      return typeof chunk === 'string' ? chunk : ''
    })
    .join('')

  const shellResult =
    record.shellResult && typeof record.shellResult === 'object'
      ? (record.shellResult as Record<string, unknown>)
      : null

  const exitCode =
    shellResult && typeof shellResult.exitCode === 'number'
      ? shellResult.exitCode
      : null

  let output = streamText
  if (!output && shellResult) {
    for (const key of ['output', 'stdout', 'stderr', 'message']) {
      const value = shellResult[key]
      if (typeof value === 'string' && value) {
        output += value
        if (!output.endsWith('\n')) output += '\n'
      }
    }
  }

  return {
    output: output ? redactVisibleOutput(output.trimEnd()) : null,
    exitCode
  }
}

function cloneActivity(): VeraVxsActivitySnapshot {
  return { ...activity }
}

function publishActivity(snapshot: VeraVxsActivitySnapshot): void {
  const payload = JSON.stringify(snapshot)
  const script = `(() => {
    const activity = ${payload}
    const root = document.getElementById('vertex-shell-internal-unit')
    if (!root || !root.shadowRoot) return 'vxs-host-not-ready'

    const shadow = root.shadowRoot
    const actions = shadow.querySelector('.actions')
    const tabsRow = shadow.querySelector('.tabsRow')
    const tabAdd = shadow.querySelector('.tabAdd')
    if (!actions) return 'vxs-actions-not-ready'
    if (!tabsRow) return 'vxs-tabs-row-not-ready'

    const STYLE_ID = 'vxs-vera-activity-style'
    const CHIP_ID = 'vxs-vera-activity'

    let style = shadow.getElementById(STYLE_ID)
    if (!style) {
      style = document.createElement('style')
      style.id = STYLE_ID
      style.textContent = [
        '.vxsVeraActivity{height:27px;max-width:320px;display:flex;align-items:center;gap:6px;',
        'padding:0 8px;border:1px solid #26394B;border-radius:5px;background:#111923;',
        'font:800 8px/1 system-ui,sans-serif;letter-spacing:.03em;overflow:hidden;white-space:nowrap}',
        '.vxsVeraActivity .vxsVeraState{flex:none;color:#718195}',
        '.vxsVeraActivity .vxsVeraCommand{min-width:0;overflow:hidden;text-overflow:ellipsis;color:#718195;',
        'font:700 8px/1 "Cascadia Mono",Consolas,monospace}',
        '.vxsVeraActivity[data-state="RUNNING"]{border-color:#F1B85B;background:rgba(241,184,91,.06)}',
        '.vxsVeraActivity[data-state="RUNNING"] .vxsVeraState{color:#F1B85B}',
        '.vxsVeraActivity[data-state="SUCCEEDED"]{border-color:#55D69E;background:rgba(85,214,158,.06)}',
        '.vxsVeraActivity[data-state="SUCCEEDED"] .vxsVeraState{color:#55D69E}',
        '.vxsVeraActivity[data-state="FAILED"]{border-color:#FF6F7C;background:rgba(255,111,124,.06)}',
        '.vxsVeraActivity[data-state="FAILED"] .vxsVeraState{color:#FF6F7C}',
        '.vxsVeraSessionBadge{height:24px;display:inline-flex;align-items:center;flex:none;padding:0 8px;',
        'border:1px solid #26394B;border-radius:4px;background:#111923;color:#718195;',
        'font:800 8px/1 "Cascadia Mono",Consolas,monospace;letter-spacing:.05em;white-space:nowrap}',
        '.vxsVeraSessionBadge[data-state="RUNNING"]{border-color:#F1B85B;color:#F1B85B;background:rgba(241,184,91,.06)}',
        '.vxsVeraSessionBadge[data-state="SUCCEEDED"]{border-color:#55D69E;color:#55D69E;background:rgba(85,214,158,.06)}',
        '.vxsVeraSessionBadge[data-state="FAILED"]{border-color:#FF6F7C;color:#FF6F7C;background:rgba(255,111,124,.06)}',
        '@media(max-width:760px){.vxsVeraActivity{max-width:150px}.vxsVeraActivity .vxsVeraCommand{display:none}.vxsVeraSessionBadge{padding:0 6px}}'
      ].join('')
      shadow.appendChild(style)
    }

    let chip = shadow.getElementById(CHIP_ID)
    if (!chip) {
      chip = document.createElement('div')
      chip.id = CHIP_ID
      chip.className = 'vxsVeraActivity'
      chip.setAttribute('aria-label', 'VERA to VXS activity')
      const state = document.createElement('span')
      state.className = 'vxsVeraState'
      const command = document.createElement('span')
      command.className = 'vxsVeraCommand'
      chip.append(state, command)
      actions.insertBefore(chip, actions.firstChild)
    }

    chip.dataset.state = activity.state
    const stateNode = chip.querySelector('.vxsVeraState')
    const commandNode = chip.querySelector('.vxsVeraCommand')

    const stateLabel =
      activity.state === 'RUNNING'
        ? 'RUNNING'
        : activity.state === 'SUCCEEDED'
          ? 'OK'
          : activity.state === 'FAILED'
            ? 'FAIL'
            : 'IDLE'

    stateNode.textContent =
      activity.state === 'IDLE'
        ? 'VERA → VXS · IDLE'
        : (activity.originVera || 'VERA') + ' → VXS · ' + stateLabel

    commandNode.textContent = activity.command || ''

    // VXS_VERA_SESSION_TAB_000095V4H2
    const SESSION_BADGE_ID = 'vxs-vera-session-badge'
    let sessionBadge = shadow.getElementById(SESSION_BADGE_ID)
    if (!sessionBadge) {
      sessionBadge = document.createElement('span')
      sessionBadge.id = SESSION_BADGE_ID
      sessionBadge.className = 'vxsVeraSessionBadge'
      sessionBadge.setAttribute('role', 'status')
      sessionBadge.setAttribute('aria-live', 'polite')
      sessionBadge.setAttribute('aria-label', 'VERA session using VXS')
      tabsRow.insertBefore(sessionBadge, tabAdd || null)
    }

    const sessionMatch = String(activity.originSession || '').match(/(\\d{2})$/)
    const veraMatch = String(activity.originVera || '').match(/(\\d{2})$/)
    const sessionNo = sessionMatch?.[1] || veraMatch?.[1] || ''
    sessionBadge.dataset.state = activity.state
    sessionBadge.hidden = activity.state === 'IDLE' || !sessionNo
    sessionBadge.textContent = sessionNo
      ? (activity.originVera || 'VERA') + ' · S' + sessionNo + ' · ' + stateLabel
      : ''

    // VXS_VERA_PERSISTENT_WORKSPACE_000097V4
    const shellPanel = shadow.querySelector('.vsh')
    const nativeTabs = shadow.querySelector('.tabs')
    const cwdRow = shadow.querySelector('.cwdRow')
    const nativeOutput = shadow.querySelector('.output')
    const composer = shadow.querySelector('.composer')

    if (
      shellPanel &&
      nativeTabs &&
      activity.originSession &&
      activity.originVera &&
      activity.requestId
    ) {
      const WORKSPACE_STYLE_ID = 'vxs-vera-workspace-style'
      const SESSION_TABS_ID = 'vxs-vera-session-tabs'

      let workspaceStyle = shadow.getElementById(WORKSPACE_STYLE_ID)
      if (!workspaceStyle) {
        workspaceStyle = document.createElement('style')
        workspaceStyle.id = WORKSPACE_STYLE_ID
        workspaceStyle.textContent = [
          '.vxsVeraSessionTabs{display:flex;align-items:center;gap:4px;flex:none;min-width:0}',
          '.vxsVeraPersistentTab{height:24px;min-width:126px;max-width:220px;display:flex;align-items:center;',
          'justify-content:center;gap:6px;padding:0 9px;border:1px solid #26394B;border-radius:5px;',
          'background:#111923;color:#718195;font:800 8px/1 "Cascadia Mono",Consolas,monospace;',
          'white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
          '.vxsVeraPersistentTab.active{color:#CBD5DF;border-color:#168CFF;background:#102C44;',
          'box-shadow:inset 0 -1px 0 #168CFF}',
          '.vxsVeraPersistentTab[data-state="RUNNING"]::before{content:"●";color:#F1B85B;font-size:7px}',
          '.vxsVeraPersistentTab[data-state="SUCCEEDED"]::before{content:"●";color:#55D69E;font-size:7px}',
          '.vxsVeraPersistentTab[data-state="FAILED"]::before{content:"●";color:#FF6F7C;font-size:7px}',
          '.vxsVeraWorkspace{grid-row:3 / 6;min-height:0;display:grid;grid-template-rows:34px minmax(0,1fr);',
          'background:#070B10;border-top:1px solid #1C2935}',
          '.vxsVeraWorkspace[hidden]{display:none}',
          '.vxsVeraWorkspaceHead{display:flex;align-items:center;justify-content:space-between;gap:10px;',
          'padding:0 10px;background:#0C121A;border-bottom:1px solid #1C2935}',
          '.vxsVeraWorkspaceIdentity{font:800 9px/1 system-ui,sans-serif;letter-spacing:.06em;color:#CBD5DF}',
          '.vxsVeraWorkspaceRoute{font:700 8px/1 "Cascadia Mono",Consolas,monospace;color:#718195}',
          '.vxsVeraWorkspaceHistory{min-height:0;overflow:auto;padding:9px 10px 14px;scrollbar-color:#26394B #070B10}',
          '.vxsVeraRun{padding:9px 10px;margin:0 0 8px;border:1px solid #1C2935;border-radius:6px;background:#0C121A}',
          '.vxsVeraRun:last-child{margin-bottom:0}',
          '.vxsVeraRunHead{display:flex;align-items:center;justify-content:space-between;gap:8px;',
          'margin-bottom:6px;color:#718195;font:800 8px/1 system-ui,sans-serif;letter-spacing:.04em}',
          '.vxsVeraRunState[data-state="RUNNING"]{color:#F1B85B}',
          '.vxsVeraRunState[data-state="SUCCEEDED"]{color:#55D69E}',
          '.vxsVeraRunState[data-state="FAILED"]{color:#FF6F7C}',
          '.vxsVeraRunInput,.vxsVeraRunOutput{margin:0;white-space:pre-wrap;word-break:break-word;',
          'font:11px/1.5 "Cascadia Mono",Consolas,monospace}',
          '.vxsVeraRunInput{padding:7px 9px;border:1px solid #26394B;border-radius:5px;',
          'background:#111923;color:#CBD5DF}',
          '.vxsVeraRunInput::before{content:"VSH › ";color:#168CFF;font-weight:900}',
          '.vxsVeraRunOutput{padding:7px 2px 0;color:#CBD5DF}',
          '.vxsVeraRunOutput:empty{display:none}',
          '@media(max-width:760px){.vxsVeraPersistentTab{min-width:100px;max-width:150px}.vxsVeraWorkspaceRoute{display:none}}'
        ].join('')
        shadow.appendChild(workspaceStyle)
      }

      let sessionTabs = shadow.getElementById(SESSION_TABS_ID)
      if (!sessionTabs) {
        sessionTabs = document.createElement('div')
        sessionTabs.id = SESSION_TABS_ID
        sessionTabs.className = 'vxsVeraSessionTabs'
        tabsRow.insertBefore(sessionTabs, sessionBadge || tabAdd || null)
      }

      const sessionKey = String(activity.originSession)
      const allWorkspaces = () => Array.from(shadow.querySelectorAll('.vxsVeraWorkspace'))
      const allVeraTabs = () => Array.from(shadow.querySelectorAll('.vxsVeraPersistentTab'))

      const showNativeWorkspace = () => {
        for (const node of [cwdRow, nativeOutput, composer]) {
          if (node) node.style.display = ''
        }
        for (const pane of allWorkspaces()) pane.hidden = true
        for (const button of allVeraTabs()) button.classList.remove('active')
      }

      const showVeraWorkspace = (button, pane) => {
        for (const node of [cwdRow, nativeOutput, composer]) {
          if (node) node.style.display = 'none'
        }
        for (const other of allWorkspaces()) other.hidden = other !== pane
        for (const other of allVeraTabs()) other.classList.toggle('active', other === button)
        pane.hidden = false
        const history = pane.querySelector('.vxsVeraWorkspaceHistory')
        if (history) history.scrollTop = history.scrollHeight
      }

      if (nativeTabs.dataset.vxsVeraWorkspaceBound !== '1') {
        nativeTabs.dataset.vxsVeraWorkspaceBound = '1'
        nativeTabs.addEventListener('click', event => {
          const target = event.target
          if (target && target.closest && target.closest('.tab')) showNativeWorkspace()
        })
      }

      if (tabAdd && tabAdd.dataset.vxsVeraWorkspaceBound !== '1') {
        tabAdd.dataset.vxsVeraWorkspaceBound = '1'
        tabAdd.addEventListener('click', () => showNativeWorkspace())
      }

      let sessionTab = Array.from(sessionTabs.querySelectorAll('.vxsVeraPersistentTab'))
        .find(button => button.dataset.session === sessionKey)
      const createdSessionTab = !sessionTab

      if (!sessionTab) {
        sessionTab = document.createElement('button')
        sessionTab.type = 'button'
        sessionTab.className = 'vxsVeraPersistentTab'
        sessionTab.dataset.session = sessionKey
        sessionTabs.appendChild(sessionTab)
      }

      let workspace = allWorkspaces().find(pane => pane.dataset.session === sessionKey)
      if (!workspace) {
        workspace = document.createElement('section')
        workspace.className = 'vxsVeraWorkspace'
        workspace.dataset.session = sessionKey
        workspace.hidden = true

        const workspaceHead = document.createElement('div')
        workspaceHead.className = 'vxsVeraWorkspaceHead'
        const identity = document.createElement('span')
        identity.className = 'vxsVeraWorkspaceIdentity'
        const route = document.createElement('span')
        route.className = 'vxsVeraWorkspaceRoute'
        route.textContent = 'VRA → VXS · persistent session workspace'
        const history = document.createElement('div')
        history.className = 'vxsVeraWorkspaceHistory'
        workspaceHead.append(identity, route)
        workspace.append(workspaceHead, history)
        shellPanel.appendChild(workspace)
      }

      const sessionNumber = sessionKey.slice(-2)
      const workspaceIdentity = workspace.querySelector('.vxsVeraWorkspaceIdentity')
      if (workspaceIdentity) workspaceIdentity.textContent = activity.originVera + ' · S' + sessionNumber

      sessionTab.dataset.state = activity.state
      sessionTab.textContent = activity.originVera + ' · S' + sessionNumber
      sessionTab.title = 'Persistent VXS workspace · ' + activity.originVera + ' / ' + sessionKey

      if (sessionTab.dataset.vxsVeraWorkspaceBound !== '1') {
        sessionTab.dataset.vxsVeraWorkspaceBound = '1'
        sessionTab.addEventListener('click', () => showVeraWorkspace(sessionTab, workspace))
      }

      const history = workspace.querySelector('.vxsVeraWorkspaceHistory')
      let run = history
        ? Array.from(history.querySelectorAll('.vxsVeraRun')).find(node => node.dataset.requestId === activity.requestId)
        : null

      if (!run && history) {
        run = document.createElement('article')
        run.className = 'vxsVeraRun'
        run.dataset.requestId = activity.requestId
        const runHead = document.createElement('div')
        runHead.className = 'vxsVeraRunHead'
        const request = document.createElement('span')
        request.className = 'vxsVeraRunRequest'
        request.textContent = activity.requestId.length > 42 ? activity.requestId.slice(0, 41) + '…' : activity.requestId
        const runState = document.createElement('span')
        runState.className = 'vxsVeraRunState'
        const runInput = document.createElement('pre')
        runInput.className = 'vxsVeraRunInput'
        const runOutput = document.createElement('pre')
        runOutput.className = 'vxsVeraRunOutput'
        runHead.append(request, runState)
        run.append(runHead, runInput, runOutput)
        history.appendChild(run)
        const runs = Array.from(history.querySelectorAll('.vxsVeraRun'))
        while (runs.length > 50) {
          const oldest = runs.shift()
          if (oldest) oldest.remove()
        }
      }

      if (run) {
        const runState = run.querySelector('.vxsVeraRunState')
        const runInput = run.querySelector('.vxsVeraRunInput')
        const runOutput = run.querySelector('.vxsVeraRunOutput')
        if (runState) {
          runState.dataset.state = activity.state
          runState.textContent =
            activity.state === 'RUNNING'
              ? 'RUNNING'
              : activity.state === 'SUCCEEDED'
                ? 'OK' + (typeof activity.exitCode === 'number' ? ' · EXIT ' + activity.exitCode : '')
                : activity.state === 'FAILED'
                  ? 'FAIL'
                  : 'IDLE'
        }
        if (runInput) runInput.textContent = activity.command || ''
        if (runOutput) runOutput.textContent = activity.visibleOutput || (activity.error ? 'ERR | ' + activity.error : '')
      }

      if (createdSessionTab) {
        if (typeof window.__VERTEX_SHELL_SET_VISIBILITY__ === 'function') {
          window.__VERTEX_SHELL_SET_VISIBILITY__(true)
        }
        shellPanel.classList.remove('collapsed')
        showVeraWorkspace(sessionTab, workspace)
      } else if (sessionTab.classList.contains('active')) {
        showVeraWorkspace(sessionTab, workspace)
      }

      if (history && sessionTab.classList.contains('active')) {
        history.scrollTop = history.scrollHeight
      }
    }

    const lines = [
      'Route: ' + activity.route,
      'State: ' + activity.state,
      activity.originVera ? 'Origin: ' + activity.originVera : '',
      activity.originSession ? 'Session: ' + activity.originSession : '',
      activity.command ? 'Command: ' + activity.command : '',
      activity.requestId ? 'Request: ' + activity.requestId : '',
      activity.correlationId ? 'Correlation: ' + activity.correlationId : '',
      activity.error ? 'Error: ' + activity.error : ''
    ].filter(Boolean)
    chip.title = lines.join('\\n')
    sessionBadge.title = lines.join('\\n')
    return 'vxs-vera-activity-updated'
  })()`

  for (const window of BrowserWindow.getAllWindows()) {
    if (window.isDestroyed() || window.webContents.isDestroyed()) continue
    void window.webContents
      .executeJavaScript(script, true)
      .catch(() => undefined)
  }
}

export function getVeraVxsActivity(): VeraVxsActivitySnapshot {
  return cloneActivity()
}

export function beginVeraVxsActivity(input: {
  originVera: string
  originSession: string
  command: string
  requestId: string
  correlationId: string
}): VeraVxsActivitySnapshot {
  const now = Date.now()
  activity = {
    schema: VERA_VXS_ACTIVITY_SCHEMA,
    state: 'RUNNING',
    originVera: input.originVera,
    originSession: input.originSession,
    route: 'VRA→VXS',
    command: redactCommand(input.command),
    requestId: input.requestId,
    correlationId: input.correlationId,
    startedAt: now,
    completedAt: null,
    updatedAt: now,
    visibleOutput: null,
    exitCode: null,
    error: null
  }
  publishActivity(activity)
  return cloneActivity()
}

export function completeVeraVxsActivity(
  requestId: string,
  result?: unknown
): VeraVxsActivitySnapshot {
  if (activity.requestId !== requestId) return cloneActivity()
  const now = Date.now()
  const visible = visibleResult(result)
  activity = {
    ...activity,
    state: 'SUCCEEDED',
    completedAt: now,
    updatedAt: now,
    visibleOutput: visible.output,
    exitCode: visible.exitCode,
    error: null
  }
  publishActivity(activity)
  return cloneActivity()
}

export function failVeraVxsActivity(
  requestId: string,
  error: unknown
): VeraVxsActivitySnapshot {
  if (activity.requestId !== requestId) return cloneActivity()
  const now = Date.now()
  activity = {
    ...activity,
    state: 'FAILED',
    completedAt: now,
    updatedAt: now,
    visibleOutput: boundedError(error),
    exitCode: null,
    error: boundedError(error)
  }
  publishActivity(activity)
  return cloneActivity()
}
