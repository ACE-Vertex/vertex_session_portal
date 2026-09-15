// VXS_PRODUCTION_BOOTSTRAP_VISUAL_000092V4H1_IMPORT
import { registerVertexShellIpc } from '../ipc/register-vertex-shell-ipc'
// VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_IMPORT
import { getVeraVxsHumanAuthorityState, toggleVeraVxsHumanFullAccess } from './vxs/vera-vxs-human-authority'
// VERTEX_SHELL_NATIVE_VRA_DISPATCH_000080V4G
// VERTEX_SHELL_CTRL_N_NEW_TAB_000080V4F
// VERTEX_SHELL_RIGHTCLICK_PASTE_000080V4DH2
// VERTEX_SHELL_RIGHTCLICK_PASTE_000080V4DH1
// VERTEX_SHELL_RIGHTCLICK_PASTE_000080V4D
// VERTEX_SHELL_ONECLIP_COMPOUND_COMMAND_000080V4C
import {
  app,
  BrowserWindow,
  clipboard,
  globalShortcut,
  type WebContents
} from 'electron'
import { randomBytes, randomUUID } from 'node:crypto'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { VertexShellService } from './vertex-shell-service'
import type {
  VertexShellCommandRequest,
  VertexShellStreamEvent
} from '../../shared/vertex-shell-contracts'

const GENERATION = '000080V4G'
const HOST_PREFIX = '[VERTEX_SHELL_HOST]'
const HOTKEY = 'CommandOrControl+Alt+Space'
const TOPMOST_OFF_HOTKEY = 'CommandOrControl+B'
const TOPMOST_ON_HOTKEY = 'CommandOrControl+F'
const MAX_BRIDGE_MESSAGE = 96 * 1024
const MAX_UI_STREAM_CHUNK = 48 * 1024

type HostMessage = {
  nonce?: string
  action?: string
  requestId?: string
  command?: string
  cwd?: string
}

type HostBinding = {
  wc: WebContents
  nonce: string
  topmost: boolean
  injected: boolean
  shellVisible: boolean
}

const service = new VertexShellService()
// VXS_PRODUCTION_BOOTSTRAP_VISUAL_000092V4H1_CALL
registerVertexShellIpc(service)
const hosts = new Map<number, HostBinding>()
let started = false
let lastFocusedHostId: number | null = null
let topmostHotkeysRegistered = false
let logPath = ''

function iso(): string {
  return new Date().toISOString()
}

function writeBridgeLog(event: string, payload: Record<string, unknown> = {}): void {
  if (!logPath) return
  try {
    fs.appendFileSync(
      logPath,
      `${JSON.stringify({
        schema: 'vertex-shell/host-bridge-log-1',
        generation: GENERATION,
        ts: iso(),
        event,
        ...payload
      })}\n`,
      'utf8'
    )
  } catch {}
}

function safeJsonForScript(value: unknown): string {
  return JSON.stringify(value)
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029')
    .replace(/</g, '\\u003c')
}

async function sendToHost(
  binding: HostBinding,
  payload: Record<string, unknown>
): Promise<void> {
  if (binding.wc.isDestroyed()) return
  const encoded = safeJsonForScript(payload)
  if (encoded.length > MAX_BRIDGE_MESSAGE) {
    writeBridgeLog('host_payload_dropped_too_large', {
      wc_id: binding.wc.id,
      bytes: encoded.length
    })
    return
  }
  try {
    await binding.wc.executeJavaScript(
      `window.__VERTEX_SHELL_HOST_RECEIVE__?.(${encoded})`,
      true
    )
  } catch (error) {
    writeBridgeLog('host_send_failed', {
      wc_id: binding.wc.id,
      error: error instanceof Error ? error.message : String(error)
    })
  }
}

function emitStream(binding: HostBinding, event: VertexShellStreamEvent): void {
  const text = String(event.chunk ?? '')
  if (!text) return
  for (let offset = 0; offset < text.length; offset += MAX_UI_STREAM_CHUNK) {
    void sendToHost(binding, {
      type: 'stream',
      event: {
        ...event,
        chunk: text.slice(offset, offset + MAX_UI_STREAM_CHUNK)
      }
    })
  }
}

function hostWindow(binding: HostBinding): BrowserWindow | null {
  if (binding.wc.isDestroyed()) return null
  return BrowserWindow.fromWebContents(binding.wc)
}

function hostState(binding: HostBinding): Record<string, unknown> {
  const win = hostWindow(binding)
  return {
    type: 'state',
    generation: GENERATION,
    shell: service.state(),
    topmost: win?.isAlwaysOnTop() ?? false,
    shellVisible: binding.shellVisible,
    hotkey: HOTKEY,
    topmostOffHotkey: TOPMOST_OFF_HOTKEY,
    topmostOnHotkey: TOPMOST_ON_HOTKEY
  }
}

async function publishState(binding: HostBinding): Promise<void> {
  await sendToHost(binding, hostState(binding))
}

async function setTopmost(binding: HostBinding, enabled: boolean): Promise<void> {
  const win = hostWindow(binding)
  if (!win) return
  win.setAlwaysOnTop(enabled, enabled ? 'floating' : 'normal')
  binding.topmost = win.isAlwaysOnTop()
  writeBridgeLog('topmost_changed', {
    wc_id: binding.wc.id,
    topmost: binding.topmost
  })
  await publishState(binding)
}

function isHumanHost(wc: WebContents): boolean {
  if (wc.isDestroyed()) return false
  return BrowserWindow.fromWebContents(wc) !== null
}

function bestHost(): HostBinding | null {
  let binding =
    lastFocusedHostId !== null
      ? hosts.get(lastFocusedHostId) ?? null
      : null

  if (!binding) {
    binding = hosts.values().next().value ?? null
  }

  return binding
}

function unregisterTopmostHotkeys(): void {
  try { globalShortcut.unregister(TOPMOST_OFF_HOTKEY) } catch {}
  try { globalShortcut.unregister(TOPMOST_ON_HOTKEY) } catch {}
  if (topmostHotkeysRegistered) {
    writeBridgeLog('topmost_hotkeys_unregistered')
  }
  topmostHotkeysRegistered = false
}

function updateTopmostHotkeys(): void {
  const anyVisible = Array.from(hosts.values()).some(binding => binding.shellVisible)

  if (!anyVisible) {
    unregisterTopmostHotkeys()
    return
  }

  if (topmostHotkeysRegistered) return

  try {
    const offOk = globalShortcut.register(TOPMOST_OFF_HOTKEY, () => {
      const binding = bestHost()
      if (!binding || !binding.shellVisible) return
      void setTopmost(binding, false)
      writeBridgeLog('topmost_hotkey', {
        wc_id: binding.wc.id,
        hotkey: TOPMOST_OFF_HOTKEY,
        requested: false
      })
    })

    const onOk = globalShortcut.register(TOPMOST_ON_HOTKEY, () => {
      const binding = bestHost()
      if (!binding || !binding.shellVisible) return
      void setTopmost(binding, true)
      writeBridgeLog('topmost_hotkey', {
        wc_id: binding.wc.id,
        hotkey: TOPMOST_ON_HOTKEY,
        requested: true
      })
    })

    if (!offOk || !onOk) {
      unregisterTopmostHotkeys()
      writeBridgeLog('topmost_hotkey_registration_failed', {
        off_registered: offOk,
        on_registered: onOk
      })
      return
    }

    topmostHotkeysRegistered = true
    writeBridgeLog('topmost_hotkeys_registered', {
      off_hotkey: TOPMOST_OFF_HOTKEY,
      on_hotkey: TOPMOST_ON_HOTKEY
    })
  } catch (error) {
    unregisterTopmostHotkeys()
    writeBridgeLog('topmost_hotkey_registration_failed', {
      error: error instanceof Error ? error.message : String(error)
    })
  }
}

async function setShellVisibility(
  binding: HostBinding,
  visible: boolean
): Promise<boolean> {
  const win = hostWindow(binding)
  if (!win) return false

  if (visible) {
    if (win.isMinimized()) win.restore()
    if (!win.isVisible()) win.show()
    win.focus()
    lastFocusedHostId = binding.wc.id
  }

  try {
    const result = await binding.wc.executeJavaScript(
      `window.__VERTEX_SHELL_SET_VISIBILITY__?.(${visible ? 'true' : 'false'}) ?? false`,
      true
    )
    binding.shellVisible = Boolean(result)
  } catch (error) {
    writeBridgeLog('shell_visibility_failed', {
      wc_id: binding.wc.id,
      requested: visible,
      error: error instanceof Error ? error.message : String(error)
    })
    return false
  }

  updateTopmostHotkeys()
  await publishState(binding)

  writeBridgeLog('shell_visibility_changed', {
    wc_id: binding.wc.id,
    visible: binding.shellVisible
  })

  return binding.shellVisible
}

async function toggleBestHostShell(): Promise<void> {
  const binding = bestHost()
  if (!binding) return
  await setShellVisibility(binding, !binding.shellVisible)
}

function randomNonce(): string {
  return randomBytes(24).toString('hex')
}

function extractConsoleMessage(args: any[]): string | null {
  if (typeof args[2] === 'string') return args[2]
  if (
    args[1] &&
    typeof args[1] === 'object' &&
    typeof args[1].message === 'string'
  ) {
    return args[1].message
  }
  return null
}

async function handleMessage(binding: HostBinding, raw: string): Promise<void> {
  if (!raw.startsWith(HOST_PREFIX)) return
  const body = raw.slice(HOST_PREFIX.length)
  if (body.length > MAX_BRIDGE_MESSAGE) return

  let message: HostMessage
  try {
    message = JSON.parse(body) as HostMessage
  } catch {
    return
  }

  if (message.nonce !== binding.nonce) {
    writeBridgeLog('message_rejected_nonce', { wc_id: binding.wc.id })
    return
  }

  const requestId =
    typeof message.requestId === 'string' && message.requestId
      ? message.requestId
      : randomUUID()
  const action = String(message.action ?? '')

  writeBridgeLog('host_action', {
    wc_id: binding.wc.id,
    action,
    request_id: requestId
  })

  try {
    switch (action) {
      case 'state':
        await publishState(binding)
        return

      case 'execute': {
        const command = String(message.command ?? '').trim()
        if (!command) throw new Error('VERTEX_SHELL_COMMAND_REQUIRED')

        await sendToHost(binding, { type: 'execution_start', requestId })

        const result = await service.execute(
          {
            command,
            cwd:
              typeof message.cwd === 'string' && message.cwd.trim()
                ? message.cwd.trim()
                : undefined
          } satisfies VertexShellCommandRequest,
          event => emitStream(binding, event)
        )

        await sendToHost(binding, {
          type: 'execution_result',
          requestId,
          result
        })
        await publishState(binding)

        writeBridgeLog('execution_completed', {
          wc_id: binding.wc.id,
          command_id: result.commandId,
          exit_code: result.exitCode,
          duration_ms: result.durationMs,
          stopped: result.stopped
        })
        return
      }

      case 'stop':
        await service.stop()
        await publishState(binding)
        return

      case 'set_cwd':
        service.setCwd({ cwd: String(message.cwd ?? '').trim() })
        await publishState(binding)
        return

      case 'toggle_topmost': {
        const win = hostWindow(binding)
        if (!win) throw new Error('VERTEX_SHELL_HOST_WINDOW_UNAVAILABLE')
        await setTopmost(binding, !win.isAlwaysOnTop())
        return
      }

      // VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_ACTION_BEGIN
      case 'vera_authority_state': {
        const state = getVeraVxsHumanAuthorityState()
        await sendToHost(binding, {
          type: 'vera_authority_state',
          state
        })
        return
      }

      case 'toggle_vera_full_access': {
        const state = toggleVeraVxsHumanFullAccess()
        await sendToHost(binding, {
          type: 'vera_authority_state',
          state
        })
        writeBridgeLog('vera_full_access_human_gate', {
          wc_id: binding.wc.id,
          mode: state.mode,
          generation: state.generation,
          granted_by: state.grantedBy
        })
        return
      }
      // VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_ACTION_END

      case 'paste_clipboard': {
        const text = await clipboard.readText()
        await sendToHost(binding, {
          type: 'clipboard_text',
          requestId,
          text
        })
        writeBridgeLog('clipboard_paste_delivered', {
          wc_id: binding.wc.id,
          request_id: requestId,
          chars: text.length
        })
        return
      }

      case 'summon':
        summon(binding)
        return

      default:
        throw new Error(`VERTEX_SHELL_UNKNOWN_ACTION:${action}`)
    }
  } catch (error) {
    const messageText =
      error instanceof Error ? error.message : String(error)

    await sendToHost(binding, {
      type: 'error',
      requestId,
      message: messageText
    })
    await publishState(binding)

    writeBridgeLog('host_action_failed', {
      wc_id: binding.wc.id,
      action,
      request_id: requestId,
      error: messageText
    })
  }
}

function summon(binding: HostBinding): void {
  const win = hostWindow(binding)
  if (!win) return
  if (win.isMinimized()) win.restore()
  if (!win.isVisible()) win.show()
  win.focus()
  lastFocusedHostId = binding.wc.id
  void sendToHost(binding, { type: 'summon' })
  writeBridgeLog('shell_summoned', {
    wc_id: binding.wc.id,
    topmost: win.isAlwaysOnTop()
  })
}

const hostUi = "(() => {\n  const GENERATION = '000080V4G'\n  const PREFIX = '[VERTEX_SHELL_HOST]'\n  const ROOT_ID = 'vertex-shell-internal-unit'\n  const SIZE_KEY = 'vertex-shell:v4e:size'\n  if (document.getElementById(ROOT_ID)) return 'already-installed'\n  if (!document.body) return 'body-unavailable'\n\n  const nonce = '__VERTEX_SHELL_NONCE__'\n  const root = document.createElement('div')\n  root.id = ROOT_ID\n  Object.assign(root.style, {\n    position: 'fixed',\n    right: '12px',\n    bottom: '12px',\n    width: 'min(980px, calc(100vw - 24px))',\n    height: '500px',\n    minWidth: '520px',\n    minHeight: '260px',\n    maxWidth: 'calc(100vw - 24px)',\n    maxHeight: 'calc(100vh - 24px)',\n    zIndex: '2147483647',\n    pointerEvents: 'auto',\n    overflow: 'hidden'\n  })\n\n  try {\n    const saved = JSON.parse(localStorage.getItem(SIZE_KEY) || 'null')\n    if (saved && Number.isFinite(saved.width) && Number.isFinite(saved.height)) {\n      root.style.width = `${Math.max(520, Math.min(window.innerWidth - 24, saved.width))}px`\n      root.style.height = `${Math.max(260, Math.min(window.innerHeight - 24, saved.height))}px`\n    }\n  } catch {}\n\n  const shadow = root.attachShadow({ mode: 'open' })\n  shadow.innerHTML = `\n    <style>\n      *{box-sizing:border-box}\n      .vsh{\n        height:100%;display:grid;\n        grid-template-rows:42px 32px 34px minmax(0,1fr) 48px;\n        color:#CBD5DF;\n        background:linear-gradient(180deg,rgba(22,140,255,.05),transparent 24%),#070B10;\n        border:1px solid #26394B;border-radius:10px;overflow:hidden;\n        box-shadow:0 18px 60px rgba(0,0,0,.42);\n        font-family:\"Cascadia Mono\",Consolas,monospace;\n        position:relative\n      }\n      .vsh.collapsed{grid-template-rows:42px 0 0 0 0}\n      .vsh.collapsed .tabsRow,.vsh.collapsed .cwdRow,.vsh.collapsed .output,.vsh.collapsed .composer{display:none}\n      .head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0 8px 0 10px;background:#0C121A;border-bottom:1px solid #1C2935;user-select:none}\n      .drag{display:flex;align-items:center;gap:9px;min-width:0;flex:1;cursor:grab}\n      .drag:active{cursor:grabbing}\n      .mark{display:grid;place-items:center;width:27px;height:27px;border:1px solid #168CFF;border-radius:6px;color:#3AB8FF;background:#102C44;font-weight:900;box-shadow:0 0 18px rgba(22,140,255,.18)}\n      .title strong{display:block;font:800 12px/1.1 system-ui,sans-serif;letter-spacing:.09em;color:#CBD5DF}\n      .title small{display:block;margin-top:2px;font:700 8px/1 system-ui,sans-serif;letter-spacing:.07em;color:#718195}\n      .actions{display:flex;align-items:center;gap:6px}\n      button{height:27px;border:1px solid #26394B;border-radius:5px;padding:0 8px;color:#CBD5DF;background:#111923;font:700 9px \"Cascadia Mono\",Consolas,monospace;cursor:pointer}\n      button:hover:not(:disabled){border-color:#168CFF;background:#14202C}\n      button:disabled{color:#455364;cursor:default}\n      .pin.on{color:#55D69E;border-color:#55D69E}.authority{color:#F1B85B}.authority.on{color:#55D69E;border-color:#55D69E;background:rgba(85,214,158,.08)}\n      .status{padding:4px 7px;border:1px solid #1C2935;border-radius:999px;color:#55D69E;background:#111923;font:800 8px system-ui,sans-serif}\n      .status.busy{color:#F1B85B}\n      .tabsRow{display:flex;align-items:center;gap:4px;padding:3px 7px;background:#0A1017;border-bottom:1px solid #1C2935;overflow:hidden}\n      .tabs{display:flex;align-items:center;gap:4px;min-width:0;overflow:auto;scrollbar-width:none;flex:1}\n      .tabs::-webkit-scrollbar{display:none}\n      .tab{height:24px;min-width:88px;max-width:160px;display:flex;align-items:center;gap:6px;justify-content:center;padding:0 10px;border:1px solid #1C2935;border-radius:5px;background:#0C121A;color:#718195;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n      .tab.active{color:#CBD5DF;border-color:#168CFF;background:#102C44;box-shadow:inset 0 -1px 0 #168CFF}\n      .tab.busy::before{content:\"●\";color:#F1B85B;font-size:7px}\n      .tabAdd{width:28px;padding:0;color:#3AB8FF;font-size:15px}\n      .cwdRow{display:grid;grid-template-columns:34px minmax(0,1fr) 44px;gap:6px;align-items:center;padding:4px 8px;background:#0C121A;border-bottom:1px solid #1C2935;color:#718195;font:700 9px system-ui,sans-serif}\n      input{min-width:0;outline:none;border:1px solid #1C2935;border-radius:4px;background:#111923;color:#CBD5DF;font:11px \"Cascadia Mono\",Consolas,monospace}\n      input:focus{border-color:#168CFF;box-shadow:0 0 0 1px rgba(22,140,255,.24)}\n      .cwd{height:24px;padding:0 8px}\n      .output{min-height:0;margin:0;padding:10px 12px;overflow:auto;white-space:pre-wrap;word-break:break-word;background:#070B10;color:#CBD5DF;font:11px/1.5 \"Cascadia Mono\",Consolas,monospace;scrollbar-color:#26394B #070B10}\n      .composer{display:grid;grid-template-columns:52px minmax(0,1fr) 50px 54px 56px 72px;gap:6px;align-items:center;padding:8px;background:#0C121A;border-top:1px solid #1C2935}\n      .prompt{color:#168CFF;font:900 11px \"Cascadia Mono\",Consolas,monospace}\n      .command{height:32px;padding:0 10px}\n      .run{color:#55D69E}.stop{color:#FF6F7C}\n      .resizeGrip{position:absolute;right:0;bottom:0;width:18px;height:18px;cursor:nwse-resize;z-index:10}\n      .resizeGrip::before,.resizeGrip::after{content:\"\";position:absolute;right:3px;bottom:3px;width:8px;height:1px;background:#26394B;transform:rotate(-45deg);transform-origin:right center}\n      .resizeGrip::after{right:2px;bottom:7px;width:5px;background:#168CFF}\n    </style>\n    <div class=\"vsh\">\n      <header class=\"head\">\n        <div class=\"drag\" title=\"Drag to move · double-click to dock\">\n          <span class=\"mark\">›_</span>\n          <span class=\"title\">\n            <strong>VERTEX SHELL</strong>\n            <small>CTRL+ALT+SPACE ON/OFF · AUTH = VERA FULL ACCESS</small>\n          </span>\n        </div>\n        <div class=\"actions\">\n          <span class=\"status\">READY</span>\n          <button class=\"pin\" title=\"Keep Session Portal above other apps\">PIN</button>\n          <button class=\"authority\" title=\"Grant VERA Full Access · Human Gate\">AUTH</button>\n          <button class=\"collapse\" title=\"Collapse / expand\">⌄</button>\n        </div>\n      </header>\n\n      <div class=\"tabsRow\">\n        <div class=\"tabs\"></div>\n        <button class=\"tabAdd\" title=\"New Vertex Shell tab\">＋</button>\n      </div>\n\n      <div class=\"cwdRow\">\n        <span>CWD</span>\n        <input class=\"cwd\" spellcheck=\"false\" value=\"G:\\\\Vertex_Project\\\\Development\">\n        <button class=\"cwdSet\">SET</button>\n      </div>\n\n      <pre class=\"output\"></pre>\n\n      <div class=\"composer\">\n        <span class=\"prompt\">VSH ›</span>\n        <input class=\"command\" autocomplete=\"off\" spellcheck=\"false\" placeholder=\"Enter command…\">\n        <button class=\"run\">RUN</button>\n        <button class=\"stop\" disabled>STOP</button>\n        <button class=\"clear\">CLEAR</button>\n        <button class=\"copy\" title=\"Copy current tab last command + clean result for Vera\">COPY</button>\n      </div>\n\n      <div class=\"resizeGrip\" title=\"Resize Vertex Shell\"></div>\n    </div>`\n\n  document.body.appendChild(root)\n\n  const q = s => shadow.querySelector(s)\n  const panel = q('.vsh')\n  const tabsNode = q('.tabs')\n  const output = q('.output')\n  const command = q('.command')\n  const cwd = q('.cwd')\n  const status = q('.status')\n  const pin = q('.pin')\n  const authority = q('.authority')\n  const run = q('.run')\n  const stop = q('.stop')\n  const copy = q('.copy')\n\n  const tabs = []\n  let tabSeq = 0\n  let activeTabId = null\n  let runningTabId = null\n  let busy = false\n  let collapsed = false\n  let dragState = null\n  let resizeState = null\n  let stateInitialized = false\n\n  const stripAnsi = value =>\n    String(value ?? '').replace(\n      /\\x1B(?:\\[[0-?]*[ -/]*[@-~]|\\][^\\x07]*(?:\\x07|\\x1B\\\\))/g,\n      ''\n    )\n\n  const currentTab = () =>\n    tabs.find(tab => tab.id === activeTabId) || tabs[0] || null\n\n  const tabById = id =>\n    tabs.find(tab => tab.id === id) || null\n\n  const saveActiveView = () => {\n    const tab = currentTab()\n    if (!tab) return\n    tab.cwd = cwd.value\n    tab.command = command.value\n    tab.output = output.textContent || ''\n  }\n\n  const restoreActiveView = () => {\n    const tab = currentTab()\n    if (!tab) return\n    cwd.value = tab.cwd\n    command.value = tab.command\n    output.textContent = tab.output\n    output.scrollTop = output.scrollHeight\n  }\n\n  const renderTabs = () => {\n    tabsNode.textContent = ''\n    for (const tab of tabs) {\n      const button = document.createElement('button')\n      button.className = 'tab'\n      if (tab.id === activeTabId) button.classList.add('active')\n      if (tab.id === runningTabId && busy) button.classList.add('busy')\n      button.textContent = tab.label\n      button.title = `${tab.label} · ${tab.cwd}`\n      button.addEventListener('click', () => {\n        if (tab.id === activeTabId) return\n        saveActiveView()\n        activeTabId = tab.id\n        restoreActiveView()\n        renderTabs()\n        command.focus()\n      })\n      tabsNode.appendChild(button)\n    }\n  }\n\n  const createTab = (initialCwd, activate = true) => {\n    saveActiveView()\n    tabSeq += 1\n    const tab = {\n      id: `shell-${tabSeq}`,\n      label: `SHELL ${tabSeq}`,\n      cwd: initialCwd || currentTab()?.cwd || 'G:\\\\Vertex_Project\\\\Development',\n      command: '',\n      output:\n        `VERTEX SHELL 000080V4G · ${`SHELL ${tabSeq}`}\\n` +\n        `Tabs are independent workspaces; pwsh execution remains single-flight.\\n` +\n        `Right-click = paste · + / Ctrl+N = new tab · drag bottom-right = resize\\nNative VRA: vra list · vra dispatch <artifact-id|card-id>\\n\\n`,\n      lastClip: '',\n      history: [],\n      historyIndex: 0\n    }\n    tabs.push(tab)\n    if (activate) activeTabId = tab.id\n    restoreActiveView()\n    renderTabs()\n    return tab\n  }\n\n  const setShellVisible = visible => {\n    root.style.display = visible ? '' : 'none'\n    if (visible) {\n      restoreActiveView()\n      window.setTimeout(() => command.focus(), 0)\n    }\n    return visible\n  }\n\n  window.__VERTEX_SHELL_SET_VISIBILITY__ = visible =>\n    setShellVisible(Boolean(visible))\n\n  const append = (kind, text, tabId = activeTabId) => {\n    const tab = tabById(tabId) || currentTab()\n    if (!tab) return\n    const prefix = kind === 'stderr' ? 'ERR │ ' : kind === 'system' ? 'VSH │ ' : '    │ '\n    const clean = stripAnsi(text)\n    const rendered = prefix + clean\n    tab.output += rendered\n    tab.lastClip += rendered\n    if (tab.id === activeTabId) {\n      output.textContent = tab.output\n      output.scrollTop = output.scrollHeight\n    }\n  }\n\n  const writeClipboard = async text => {\n    const value = String(text ?? '').trimEnd()\n    if (!value) return false\n\n    try {\n      await navigator.clipboard.writeText(value)\n      return true\n    } catch {}\n\n    try {\n      const area = document.createElement('textarea')\n      area.value = value\n      area.style.position = 'fixed'\n      area.style.left = '-10000px'\n      area.style.top = '-10000px'\n      document.body.appendChild(area)\n      area.focus()\n      area.select()\n      const ok = document.execCommand('copy')\n      area.remove()\n      return ok\n    } catch {\n      return false\n    }\n  }\n\n  const send = (action, payload = {}) => {\n    const requestId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`\n    console.log(PREFIX + JSON.stringify({ nonce, action, requestId, ...payload }))\n    return requestId\n  }\n\n  const setBusy = value => {\n    busy = Boolean(value)\n    status.textContent = busy ? 'RUNNING' : 'READY'\n    status.classList.toggle('busy', busy)\n    run.disabled = busy\n    stop.disabled = !busy\n    command.disabled = busy\n    renderTabs()\n  }\n\n  const insertTextAtCaret = (field, text) => {\n    const value = String(text ?? '')\n    if (!value) return\n    const start =\n      typeof field.selectionStart === 'number'\n        ? field.selectionStart\n        : field.value.length\n    const end =\n      typeof field.selectionEnd === 'number'\n        ? field.selectionEnd\n        : start\n\n    field.value =\n      field.value.slice(0, start) +\n      value +\n      field.value.slice(end)\n\n    const next = start + value.length\n    try { field.setSelectionRange(next, next) } catch {}\n    field.focus()\n\n    const tab = currentTab()\n    if (tab) {\n      if (field === command) tab.command = field.value\n      if (field === cwd) tab.cwd = field.value\n    }\n  }\n\n  window.__VERTEX_SHELL_HOST_RECEIVE__ = message => {\n    if (!message || typeof message !== 'object') return\n\n    if (message.type === 'clipboard_text') {\n      const active = shadow.activeElement\n      const target =\n        active === command || active === cwd\n          ? active\n          : command\n      insertTextAtCaret(target, message.text || '')\n      return\n    }\n\n    if (message.type === 'stream') {\n      const event = message.event || {}\n      append(event.kind || 'stdout', event.chunk || '', runningTabId || activeTabId)\n      return\n    }\n\n    if (message.type === 'state') {\n      const shell = message.shell || {}\n      if (!stateInitialized) {\n        const tab = currentTab()\n        if (tab && shell.cwd) {\n          tab.cwd = shell.cwd\n          cwd.value = shell.cwd\n        }\n        stateInitialized = true\n      } else if (!busy) {\n        const tab = currentTab()\n        if (tab && shell.cwd) {\n          tab.cwd = shell.cwd\n          cwd.value = shell.cwd\n        }\n      }\n\n      setBusy(Boolean(shell.busy))\n      pin.classList.toggle('on', Boolean(message.topmost))\n      pin.textContent = message.topmost ? 'PINNED' : 'PIN'\n      return\n    }\n\n    if (message.type === 'vera_authority_state') {\n      const gate = message.state || {}\n      const full = gate.mode === 'FULL' && gate.granted === true && gate.grantedBy === 'HUMAN'\n      authority.classList.toggle('on', full)\n      authority.textContent = full ? 'FULL' : 'AUTH'\n      authority.title = full\n        ? 'VERA Full Access · HUMAN GRANTED · click to revoke'\n        : 'Grant VERA Full Access · Human Gate'\n      return\n    }\n\n    if (message.type === 'execution_start') {\n      setBusy(true)\n      return\n    }\n\n    if (message.type === 'execution_result') {\n      const result = message.result || {}\n      const targetId = runningTabId || activeTabId\n      append(\n        'system',\n        `RESULT exit=${result.exitCode ?? '?'} · ${result.durationMs ?? '?'} ms · ${result.backend ?? ''}\\n`,\n        targetId\n      )\n      runningTabId = null\n      setBusy(false)\n      command.focus()\n      return\n    }\n\n    if (message.type === 'error') {\n      append(\n        'stderr',\n        `${message.message || 'Unknown Vertex Shell error'}\\n`,\n        runningTabId || activeTabId\n      )\n      runningTabId = null\n      setBusy(false)\n      return\n    }\n\n    if (message.type === 'summon') {\n      setShellVisible(true)\n      if (collapsed) {\n        collapsed = false\n        panel.classList.remove('collapsed')\n        root.style.height = root.dataset.openHeight || '500px'\n        q('.collapse').textContent = '⌄'\n      }\n      command.focus()\n    }\n  }\n\n  const isNativeVraCommand = value =>\n    /^vra(?:\\s|$)/i.test(String(value || '').trim())\n\n  const nativeVraApi = () => {\n    const portal = window.vertexPortal\n    if (\n      !portal ||\n      typeof portal.getVraDispatchState !== 'function' ||\n      typeof portal.dispatchVraCard !== 'function'\n    ) {\n      throw new Error('VERTEX_SHELL_VRA_PORTAL_API_UNAVAILABLE')\n    }\n    return portal\n  }\n\n  const compactVraCard = card => {\n    const artifact = card.artifactId || card.filename || card.id || '(unknown)'\n    const title = card.title || card.jobTitle || ''\n    const origin =\n      [card.originVera, card.originSession]\n        .filter(Boolean)\n        .join('/') || 'UNKNOWN'\n    const requested = card.requestedLane || 'ANY'\n    const allocated = card.allocatedLane || '-'\n    const registration = card.workstationRegistration || '-'\n    const jobState = card.workstationJobState || '-'\n    const evidence = card.workstationEvidenceState || '-'\n\n    return [\n      `artifact=${artifact}`,\n      title ? `title=${title}` : '',\n      `card=${card.id || '-'}`,\n      `status=${card.status || '-'}`,\n      `approval=${card.humanApproval || '-'}`,\n      `phase=${card.dispatchPhase || '-'}`,\n      `origin=${origin}`,\n      `requested=${requested}`,\n      `allocated=${allocated}`,\n      `registration=${registration}`,\n      `job=${jobState}`,\n      `evidence=${evidence}`,\n    ].filter(Boolean).join(' · ')\n  }\n\n  const handleNativeVra = async (value, tabId) => {\n    const portal = nativeVraApi()\n    const trimmed = String(value || '').trim()\n    const body = trimmed.replace(/^vra\\b/i, '').trim()\n\n    if (!body || /^help$/i.test(body)) {\n      append(\n        'system',\n        [\n          'NATIVE VRA COMMANDS\\n',\n          'vra list\\n',\n          'vra dispatch <artifact-id|card-id|filename>\\n',\n          'Dispatch is an explicit Human command and uses the existing Portal dispatch service.\\n',\n        ].join(''),\n        tabId\n      )\n      return\n    }\n\n    if (/^list$/i.test(body)) {\n      const state = await portal.getVraDispatchState()\n      const cards = Array.isArray(state?.cards) ? state.cards : []\n\n      append(\n        'system',\n        `NATIVE VRA LIST · cards=${cards.length} · workstation=${state?.workstationOnline ? 'ONLINE' : 'OFFLINE'}\\n`,\n        tabId\n      )\n\n      if (!cards.length) {\n        append('system', 'No VRA cards are currently staged.\\n', tabId)\n        return\n      }\n\n      cards.forEach((card, index) => {\n        append('stdout', `[${index + 1}] ${compactVraCard(card)}\\n`, tabId)\n      })\n      return\n    }\n\n    const dispatchMatch = body.match(/^dispatch\\s+(.+)$/i)\n    if (!dispatchMatch) {\n      throw new Error(\n        'VERTEX_SHELL_VRA_COMMAND_UNKNOWN: use \"vra list\" or \"vra dispatch <artifact-id|card-id|filename>\"'\n      )\n    }\n\n    const selector = dispatchMatch[1].trim()\n    if (!selector) {\n      throw new Error('VERTEX_SHELL_VRA_SELECTOR_REQUIRED')\n    }\n\n    const state = await portal.getVraDispatchState()\n    const cards = Array.isArray(state?.cards) ? state.cards : []\n\n    const matches = cards.filter(card =>\n      [card.id, card.artifactId, card.filename]\n        .filter(Boolean)\n        .some(candidate => String(candidate) === selector)\n    )\n\n    if (matches.length === 0) {\n      throw new Error(\n        `VERTEX_SHELL_VRA_NOT_FOUND:${selector} · run \"vra list\"`\n      )\n    }\n\n    if (matches.length !== 1) {\n      throw new Error(\n        `VERTEX_SHELL_VRA_SELECTOR_AMBIGUOUS:${selector}:${matches.length}`\n      )\n    }\n\n    const card = matches[0]\n    if (card.status === 'DISPATCHED' || card.dispatchPhase === 'PUBLISHED') {\n      throw new Error(\n        `VERTEX_SHELL_VRA_ALREADY_DISPATCHED:${card.artifactId || card.id}`\n      )\n    }\n\n    append(\n      'system',\n      `NATIVE VRA DISPATCH · Human command · ${compactVraCard(card)}\\n`,\n      tabId\n    )\n\n    const result = await portal.dispatchVraCard(card.id)\n\n    append(\n      'system',\n      `NATIVE VRA RESULT · ${compactVraCard(result)}\\n`,\n      tabId\n    )\n\n    if (result.error) {\n      append('stderr', `VRA ERROR · ${result.error}\\n`, tabId)\n    }\n  }\n\n  const execute = async () => {\n    const tab = currentTab()\n    const value = command.value.trim()\n    if (!tab || !value || busy) return\n\n    tab.history.push(value)\n    tab.historyIndex = tab.history.length\n    tab.lastClip = ''\n    tab.command = ''\n    tab.cwd = cwd.value.trim()\n\n    append('system', `> ${value}\\n`, tab.id)\n    command.value = ''\n\n    if (isNativeVraCommand(value)) {\n      setBusy(true)\n      try {\n        await handleNativeVra(value, tab.id)\n      } catch (error) {\n        append(\n          'stderr',\n          `${error instanceof Error ? error.message : String(error)}\\n`,\n          tab.id\n        )\n      } finally {\n        setBusy(false)\n        command.focus()\n      }\n      return\n    }\n\n    runningTabId = tab.id\n    setBusy(true)\n    send('execute', { command: value, cwd: tab.cwd })\n  }\n\n  run.addEventListener('click', execute)\n  stop.addEventListener('click', () => send('stop'))\n\n  q('.clear').addEventListener('click', () => {\n    const tab = currentTab()\n    if (!tab) return\n    tab.output = ''\n    tab.lastClip = ''\n    output.textContent = ''\n  })\n\n  copy.addEventListener('click', async () => {\n    saveActiveView()\n    const tab = currentTab()\n    const source = tab?.lastClip || tab?.output || ''\n    const ok = await writeClipboard(stripAnsi(source))\n    const original = copy.textContent\n    copy.textContent = ok ? 'COPIED' : 'COPY ERR'\n    copy.style.color = ok ? '#55D69E' : '#FF6F7C'\n    window.setTimeout(() => {\n      copy.textContent = original || 'COPY'\n      copy.style.color = ''\n    }, 900)\n  })\n\n  q('.cwdSet').addEventListener('click', () => {\n    const tab = currentTab()\n    if (tab) tab.cwd = cwd.value.trim()\n    send('set_cwd', { cwd: cwd.value.trim() })\n  })\n\n  q('.tabAdd').addEventListener('click', () => {\n    const base = currentTab()?.cwd || cwd.value.trim()\n    createTab(base, true)\n    command.focus()\n  })\n\n  window.addEventListener(\n    'keydown',\n    event => {\n      if (event.isComposing) return\n      if (root.style.display === 'none') return\n\n      const isCtrlN =\n        event.ctrlKey &&\n        !event.altKey &&\n        !event.shiftKey &&\n        String(event.key).toLowerCase() === 'n'\n\n      if (!isCtrlN) return\n\n      event.preventDefault()\n      event.stopPropagation()\n\n      const base = currentTab()?.cwd || cwd.value.trim()\n      createTab(base, true)\n      command.focus()\n    },\n    true\n  )\n\n  pin.addEventListener('click', () => send('toggle_topmost'))\n  authority.addEventListener('click', () => send('toggle_vera_full_access'))\n\n  q('.collapse').addEventListener('click', () => {\n    collapsed = !collapsed\n    if (collapsed) {\n      root.dataset.openHeight = root.style.height || '500px'\n      root.style.height = '42px'\n    } else {\n      root.style.height = root.dataset.openHeight || '500px'\n    }\n    panel.classList.toggle('collapsed', collapsed)\n    q('.collapse').textContent = collapsed ? '⌃' : '⌄'\n  })\n\n  command.addEventListener('input', () => {\n    const tab = currentTab()\n    if (tab) tab.command = command.value\n  })\n\n  cwd.addEventListener('input', () => {\n    const tab = currentTab()\n    if (tab) tab.cwd = cwd.value\n  })\n\n  command.addEventListener('keydown', event => {\n    if (event.isComposing) return\n\n    const tab = currentTab()\n    if (!tab) return\n\n    if (event.key === 'Enter') {\n      event.preventDefault()\n      execute()\n      return\n    }\n\n    if (event.key === 'ArrowUp') {\n      event.preventDefault()\n      if (!tab.history.length) return\n      tab.historyIndex = Math.max(0, tab.historyIndex - 1)\n      command.value = tab.history[tab.historyIndex] || ''\n      tab.command = command.value\n      command.setSelectionRange(command.value.length, command.value.length)\n      return\n    }\n\n    if (event.key === 'ArrowDown') {\n      event.preventDefault()\n      if (!tab.history.length) return\n      tab.historyIndex = Math.min(tab.history.length, tab.historyIndex + 1)\n      command.value =\n        tab.historyIndex >= tab.history.length\n          ? ''\n          : tab.history[tab.historyIndex] || ''\n      tab.command = command.value\n    }\n  })\n\n  root.addEventListener('contextmenu', event => {\n    event.preventDefault()\n    send('paste_clipboard')\n  })\n\n  const drag = q('.drag')\n  drag.addEventListener('pointerdown', event => {\n    if (event.button !== 0) return\n    const rect = root.getBoundingClientRect()\n    dragState = {\n      pointerId: event.pointerId,\n      dx: event.clientX - rect.left,\n      dy: event.clientY - rect.top\n    }\n    drag.setPointerCapture(event.pointerId)\n  })\n\n  drag.addEventListener('pointermove', event => {\n    if (!dragState || dragState.pointerId !== event.pointerId) return\n    const left = Math.max(\n      0,\n      Math.min(window.innerWidth - root.offsetWidth, event.clientX - dragState.dx)\n    )\n    const top = Math.max(\n      0,\n      Math.min(window.innerHeight - 42, event.clientY - dragState.dy)\n    )\n    root.style.left = `${left}px`\n    root.style.top = `${top}px`\n    root.style.right = 'auto'\n    root.style.bottom = 'auto'\n  })\n\n  drag.addEventListener('pointerup', event => {\n    if (dragState?.pointerId === event.pointerId) {\n      drag.releasePointerCapture(event.pointerId)\n      dragState = null\n    }\n  })\n\n  drag.addEventListener('dblclick', () => {\n    root.style.left = 'auto'\n    root.style.top = 'auto'\n    root.style.right = '12px'\n    root.style.bottom = '12px'\n  })\n\n  const grip = q('.resizeGrip')\n  grip.addEventListener('pointerdown', event => {\n    if (event.button !== 0) return\n    const rect = root.getBoundingClientRect()\n    resizeState = {\n      pointerId: event.pointerId,\n      startX: event.clientX,\n      startY: event.clientY,\n      width: rect.width,\n      height: rect.height\n    }\n    grip.setPointerCapture(event.pointerId)\n    event.preventDefault()\n  })\n\n  grip.addEventListener('pointermove', event => {\n    if (!resizeState || resizeState.pointerId !== event.pointerId) return\n\n    const nextWidth = Math.max(\n      520,\n      Math.min(window.innerWidth - 24, resizeState.width + event.clientX - resizeState.startX)\n    )\n    const nextHeight = Math.max(\n      260,\n      Math.min(window.innerHeight - 24, resizeState.height + event.clientY - resizeState.startY)\n    )\n\n    root.style.width = `${nextWidth}px`\n    root.style.height = `${nextHeight}px`\n  })\n\n  grip.addEventListener('pointerup', event => {\n    if (!resizeState || resizeState.pointerId !== event.pointerId) return\n\n    try {\n      localStorage.setItem(\n        SIZE_KEY,\n        JSON.stringify({\n          width: root.getBoundingClientRect().width,\n          height: root.getBoundingClientRect().height\n        })\n      )\n    } catch {}\n\n    try { grip.releasePointerCapture(event.pointerId) } catch {}\n    resizeState = null\n  })\n\n  createTab('G:\\\\Vertex_Project\\\\Development', true)\n  send('state')\n  send('vera_authority_state')\n  command.focus()\n  return 'installed'\n})()"

async function injectHostUi(binding: HostBinding, reason: string): Promise<void> {
  if (binding.wc.isDestroyed()) return
  try {
    const script = hostUi.replace(
      "'__VERTEX_SHELL_NONCE__'",
      JSON.stringify(binding.nonce)
    )
    const result = await binding.wc.executeJavaScript(script, true)
    binding.injected = result === 'installed' || result === 'already-installed'
    if (binding.injected) {
      binding.shellVisible = true
      updateTopmostHotkeys()
    }

    writeBridgeLog('host_ui_injected', {
      wc_id: binding.wc.id,
      reason,
      result
    })

    await publishState(binding)
  } catch (error) {
    writeBridgeLog('host_ui_injection_failed', {
      wc_id: binding.wc.id,
      reason,
      error: error instanceof Error ? error.message : String(error)
    })
  }
}

function attachHost(wc: WebContents): void {
  if (!isHumanHost(wc) || hosts.has(wc.id) || wc.isDestroyed()) return

  const binding: HostBinding = {
    wc,
    nonce: randomNonce(),
    topmost: BrowserWindow.fromWebContents(wc)?.isAlwaysOnTop() ?? false,
    injected: false,
    shellVisible: true
  }

  hosts.set(wc.id, binding)
  lastFocusedHostId = wc.id

  writeBridgeLog('host_attached', { wc_id: wc.id })

  const anyWc = wc as any

  anyWc.on('focus', () => {
    lastFocusedHostId = wc.id
  })

  anyWc.on('dom-ready', () => {
    void injectHostUi(binding, 'dom-ready')
  })

  anyWc.on('did-finish-load', () => {
    void injectHostUi(binding, 'did-finish-load')
  })

  anyWc.on('console-message', (...args: any[]) => {
    const message = extractConsoleMessage(args)
    if (!message || !message.startsWith(HOST_PREFIX)) return
    void handleMessage(binding, message)
  })

  anyWc.once('destroyed', () => {
    hosts.delete(wc.id)
    if (lastFocusedHostId === wc.id) lastFocusedHostId = null
    updateTopmostHotkeys()
    writeBridgeLog('host_destroyed', { wc_id: wc.id })
  })

  void injectHostUi(binding, 'attach')
}

function registerHotkey(): void {
  try {
    const ok = globalShortcut.register(HOTKEY, () => {
      void toggleBestHostShell()
    })
    writeBridgeLog('global_hotkey_registration', {
      hotkey: HOTKEY,
      registered: ok,
      behavior: 'shell_visibility_toggle'
    })
  } catch (error) {
    writeBridgeLog('global_hotkey_registration_failed', {
      hotkey: HOTKEY,
      error: error instanceof Error ? error.message : String(error)
    })
  }
}

export function startVertexShellHostBridge(): void {
  if (started) return
  started = true

  const root = path.join(app.getPath('userData'), 'vertex-shell')
  fs.mkdirSync(root, { recursive: true })
  logPath = path.join(root, 'host-bridge.jsonl')

  writeBridgeLog('vertex_shell_host_bridge_started', {
    pid: process.pid,
    hotkey: HOTKEY,
    human_only: true,
    vera_auto_execution: false,
    webview_execution: false,
    backend: service.state().backend
  })

  for (const win of BrowserWindow.getAllWindows()) {
    attachHost(win.webContents)
  }

  app.on('browser-window-created', (_event, win) => {
    attachHost(win.webContents)
  })

  registerHotkey()

  app.on('before-quit', () => {
    try { globalShortcut.unregister(HOTKEY) } catch {}
    unregisterTopmostHotkeys()
    void service.stop()
    writeBridgeLog('vertex_shell_host_bridge_stopping')
  })
}

void app.whenReady().then(startVertexShellHostBridge)
