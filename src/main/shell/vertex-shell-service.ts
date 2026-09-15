// VXS_BARE_HELP_ALIAS_000030
// VXS_CLIPBOARD_OWNERSHIP_REPAIR_000029
// VXS_CLIPBOARD_NORMALIZATION_000027
// VERTEX_SHELL_ONECLIP_COMPOUND_COMMAND_000080V4C
// VXS_FORMALIZATION_000002
// VXS_SETTINGS_AND_TAB_CLOSE_000005
// VXS_COMMAND_FOUNDATION_000006
// VXS_VSH_PREFIX_RUNTIME_REPAIR_000007H1
// VXS_DEVELOPMENT_CAPABILITY_PACK_000008
// VXS_VERTEX_CAPABILITY_PACK_000009
import { app, BrowserWindow } from 'electron'
import { spawn, type ChildProcessWithoutNullStreams } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { executeVxsCommand } from './vxs/vxs-command-registry'
import { planVxsProviderExecution } from './vxs/vxs-provider-resolver'
import * as fs from 'node:fs'
import * as path from 'node:path'
import type {
  VertexShellCommandRequest,
  VertexShellCommandResult,
  VertexShellSetCwdRequest,
  VertexShellState,
  VertexShellStreamEvent
} from '../../shared/vertex-shell-contracts'

const GENERATION = '000080V4A' as const
const VXS_VERSION = '0.1.0' as const
const VXS_CANONICAL_NAME = 'Vertex eXecution Shell' as const
const DEFAULT_CWD = 'G:\\Vertex_Project\\Development'
const MAX_COMMAND_CHARS = 32_000
const MAX_STREAM_BYTES = 2 * 1024 * 1024

type OutputSink = (event: VertexShellStreamEvent) => void

interface ActiveExecution {
  commandId: string
  command: string
  cwd: string
  backend: string
  child: ChildProcessWithoutNullStreams
  startedAt: number
  stdoutBytes: number
  stderrBytes: number
  stdoutTruncated: boolean
  stderrTruncated: boolean
  stopped: boolean
}

function nowIso(): string {
  return new Date().toISOString()
}

function redactCommand(command: string): string {
  return command
    .replace(/(api[_-]?key|token|password|passwd|secret)\s*=\s*("[^"]*"|'[^']*'|\S+)/gi, '$1=[REDACTED]')
    .replace(/(authorization\s*:\s*bearer)\s+\S+/gi, '$1 [REDACTED]')
    .replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, '[REDACTED]')
}

function safeExistingDirectory(candidate: string): string {
  const resolved = path.resolve(candidate)
  const stat = fs.statSync(resolved)
  if (!stat.isDirectory()) {
    throw new Error(`Not a directory: ${resolved}`)
  }
  return resolved
}

function resolveBackend(): string {
  // Keep PowerShell as a compatibility organ during predation.
  // Windows resolves pwsh.exe through PATH without shell=true.
  return 'pwsh.exe'
}

export class VertexShellService {
  private syncVxsBranding(): void {
    const script = String.raw`(() => {
      const ROOT_ID = 'vertex-shell-internal-unit'
      const SETTINGS_KEY = 'vxs:editor-settings:v1'
      const root = document.getElementById(ROOT_ID)
      if (!root || !root.shadowRoot) return 'vxs-host-not-ready'

      const shadow = root.shadowRoot

      if (root.__VXS_RUNTIME__?.refresh) {
        root.__VXS_RUNTIME__.refresh()
        return 'vxs-runtime-refreshed'
      }

      const closedTabs = new Set()
      let settingsOpenPinned = false
      let closeTimer = 0
      let styling = false
      let refreshQueued = false
      let lastStyledText = ''
      let lastStyledMode = ''

      const q = selector => shadow.querySelector(selector)
      const qa = selector => Array.from(shadow.querySelectorAll(selector))

      const output = () => q('.output')
      const shellPanel = () => q('.vsh')

      const installNativeVraAlias = () => {
        if (root.__VXS_NATIVE_VRA_ALIAS__) return

        const rewrite = () => {
          const input = q('.command')
          if (!input) return
          const current = String(input.value || '').trim()
          if (!/^vxs\s+vra(?:\s|$)/i.test(current)) return
          input.value = current.replace(/^vxs\s+/i, '')
          input.dispatchEvent(new Event('input', { bubbles: true }))
        }

        shadow.addEventListener(
          'keydown',
          event => {
            if (event.isComposing || event.key !== 'Enter') return
            rewrite()
          },
          true
        )

        shadow.addEventListener(
          'click',
          event => {
            const target = event.target
            if (!(target instanceof Element)) return
            if (!target.closest('.run')) return
            rewrite()
          },
          true
        )

        root.__VXS_NATIVE_VRA_ALIAS__ = true
      }

      const normalizeVxsBrandText = value =>
        String(value ?? '')
          .replaceAll('VSH │', 'VXS │')
          .replaceAll('VSH ›', 'VXS ›')
          .replaceAll(
            'VERTEX SHELL 000080V4G · SHELL',
            'VXS 0.1.0 · SHELL'
          )


      const installCanonicalClipboardCopy = () => {
        if (root.__VXS_CANONICAL_CLIPBOARD_COPY__) return

        shadow.addEventListener(
          'click',
          event => {
            const target = event.target
            if (!(target instanceof Element)) return

            const button = target.closest('button')
            if (!button) return

            const label = String(button.textContent || '')
              .trim()
              .toUpperCase()

            // Scope strictly to the VXS transcript COPY button.
            // Explorer COPY PATH lives outside this shell shadow root.
            if (label !== 'COPY') return

            const node = output()
            if (!node) return

            const clipboard = navigator.clipboard
            if (!clipboard?.writeText) return

            const canonicalTranscript = normalizeVxsBrandText(
              node.textContent || ''
            )

            // VXS owns transcript COPY.
            //
            // The legacy Host COPY handler reads the internal transcript,
            // whose historical prefix can still be VSH even though the
            // presentation layer is already canonicalized to VXS.
            //
            // Intercept during capture before the button's legacy handler
            // runs, then stop the legacy path so two asynchronous clipboard
            // writes cannot race and re-introduce VSH.
            event.preventDefault()
            event.stopImmediatePropagation()

            void clipboard
              .writeText(canonicalTranscript)
              .catch(() => undefined)
          },
          true
        )

        root.__VXS_CANONICAL_CLIPBOARD_COPY__ = true
      }

      const installSynchronousOutputBranding = () => {
        const node = output()
        if (!node || node.__VXS_TEXT_CONTENT_PATCHED__) return

        const descriptor = Object.getOwnPropertyDescriptor(
          Node.prototype,
          'textContent'
        )

        if (!descriptor?.get || !descriptor?.set) return

        Object.defineProperty(node, 'textContent', {
          configurable: true,
          enumerable: descriptor.enumerable ?? false,
          get() {
            return descriptor.get.call(this)
          },
          set(value) {
            descriptor.set.call(this, normalizeVxsBrandText(value))
          }
        })

        node.__VXS_TEXT_CONTENT_PATCHED__ = true
        node.textContent = normalizeVxsBrandText(node.textContent)
      }

      const addRuntimeStyle = () => {
        if (q('#vxs-runtime-style')) return
        const style = document.createElement('style')
        style.id = 'vxs-runtime-style'
        style.textContent = [
          '.vsh{--vxs-editor-font-size:11px}',
          '.vxsSettingsButton{width:29px!important;padding:0!important;font-size:15px!important;color:#3AB8FF!important;border-color:#26394B!important}',
          '.vxsSettingsButton:hover,.vxsSettingsButton.open{border-color:#168CFF!important;background:#102C44!important;box-shadow:0 0 15px rgba(22,140,255,.18)!important}',
          '.vxsSettingsPopover{position:absolute;top:38px;right:8px;width:min(320px,calc(100% - 16px));z-index:80;padding:12px;background:rgba(12,18,26,.985);border:1px solid #168CFF;border-radius:8px;box-shadow:0 18px 46px rgba(0,0,0,.52),0 0 18px rgba(22,140,255,.12);font-family:system-ui,sans-serif;color:#CBD5DF;opacity:0;visibility:hidden;pointer-events:none;transform:translateY(-4px);transition:opacity .12s ease,transform .12s ease,visibility .12s ease}',
          '.vxsSettingsPopover.open{opacity:1;visibility:visible;pointer-events:auto;transform:translateY(0)}',
          '.vxsSettingsTitle{display:flex;align-items:center;justify-content:space-between;margin:0 0 10px;font-size:11px;font-weight:800;letter-spacing:.06em;color:#CBD5DF}',
          '.vxsSettingsSection{padding-top:10px;margin-top:10px;border-top:1px solid #26394B}',
          '.vxsSettingsSection:first-of-type{padding-top:0;margin-top:0;border-top:0}',
          '.vxsSettingsLabel{display:block;margin-bottom:8px;font-size:10px;font-weight:800;color:#CBD5DF}',
          '.vxsMode{display:grid;grid-template-columns:18px minmax(0,1fr);gap:7px;padding:8px;margin:0 0 7px;border:1px solid #1C2935;border-radius:7px;background:#0C121A;cursor:pointer}',
          '.vxsMode:has(input:checked){border-color:#168CFF;background:#102C44}',
          '.vxsMode input{margin:2px 0 0;accent-color:#168CFF}',
          '.vxsModeName{font-size:10px;font-weight:800;color:#CBD5DF}',
          '.vxsLegend{display:grid;gap:5px;margin-top:7px;font-size:9px;color:#718195}',
          '.vxsLegendRow{display:flex;align-items:center;gap:7px}',
          '.vxsDot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}',
          '.vxsFontRow{display:grid;grid-template-columns:16px minmax(0,1fr) 44px;gap:8px;align-items:center}',
          '.vxsFontRow input[type=range]{width:100%;accent-color:#168CFF}',
          '.vxsFontValue{text-align:right;font:800 9px "Cascadia Mono",Consolas,monospace;color:#CBD5DF}',
          '.output,.cwd,.command,.prompt{font-size:var(--vxs-editor-font-size)!important}',
          '.vxsLine{color:#CBD5DF}',
          '[data-vxs-editor-mode="default"] .vxsLine.info{color:#CBD5DF}',
          '[data-vxs-editor-mode="default"] .vxsLine.success{color:#55D69E}',
          '[data-vxs-editor-mode="default"] .vxsLine.warning{color:#F1B85B}',
          '[data-vxs-editor-mode="default"] .vxsLine.error{color:#FF6F7C}',
          '[data-vxs-editor-mode="old"] .vxsLine{color:#55D69E}',
          '[data-vxs-editor-mode="old"] .vxsLine.error{color:#FF6F7C}',
          '.tab{position:relative!important;padding-right:27px!important}',
          '.vxsTabClose{position:absolute;right:5px;top:50%;transform:translateY(-50%);display:grid;place-items:center;width:15px;height:15px;border-radius:4px;color:#718195;font:800 12px/1 system-ui,sans-serif;cursor:pointer;opacity:.72}',
          '.tab:hover .vxsTabClose,.tab.active .vxsTabClose{opacity:1}',
          '.vxsTabClose:hover{color:#FF6F7C;background:rgba(255,111,124,.10)}',
          '.vxsTabClose.busy{opacity:.25!important;cursor:not-allowed}',
          '.vxsTabClosed{display:none!important}'
        ].join('')
        shadow.appendChild(style)
      }

      const readSettings = () => {
        let saved = null
        try { saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null') } catch {}
        const currentOutput = output()
        const currentSize = currentOutput
          ? Math.round(parseFloat(getComputedStyle(currentOutput).fontSize) || 11)
          : 11
        const mode = saved?.mode === 'old' ? 'old' : 'default'
        const fontSize = Number.isFinite(Number(saved?.fontSize))
          ? Math.max(9, Math.min(20, Number(saved.fontSize)))
          : currentSize
        return { mode, fontSize }
      }

      let settings = readSettings()

      const saveSettings = () => {
        try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)) } catch {}
      }

      const classifyLine = line => {
        const upper = String(line || '').toUpperCase()
        if (
          upper.startsWith('ERR │') ||
          /\b(ERROR|FAILED|FAILURE|REJECTED|ROLLED_BACK)\b/.test(upper) ||
          /\bEXIT\s+[1-9][0-9]*\b/.test(upper) ||
          /\bRESULT\s+EXIT=[1-9][0-9]*\b/.test(upper)
        ) return 'error'
        if (
          /\b(WARN|WARNING|CAUTION|ATTN|RUNNING|HOLD|TRUNCATED|STOPPED)\b/.test(upper)
        ) return 'warning'
        if (
          /\b(PASS|SUCCESS|SUCCEEDED|VERIFIED|READY)\b/.test(upper) ||
          /\bEXIT\s+0\b/.test(upper) ||
          /\bRESULT\s+EXIT=0\b/.test(upper)
        ) return 'success'
        return 'info'
      }

      const styleOutput = () => {
        if (styling) return
        const node = output()
        if (!node) return
        const raw = node.textContent || ''
        if (
          raw === lastStyledText &&
          settings.mode === lastStyledMode &&
          node.querySelector('.vxsLine')
        ) return

        styling = true
        const wasNearBottom =
          node.scrollHeight - node.scrollTop - node.clientHeight < 32
        const parts = raw.split('\n')
        const fragment = document.createDocumentFragment()

        parts.forEach((line, index) => {
          const span = document.createElement('span')
          span.className = 'vxsLine ' + classifyLine(line)
          span.textContent = line
          fragment.appendChild(span)
          if (index < parts.length - 1) {
            fragment.appendChild(document.createTextNode('\n'))
          }
        })

        node.replaceChildren(fragment)
        lastStyledText = raw
        lastStyledMode = settings.mode
        if (wasNearBottom) node.scrollTop = node.scrollHeight
        styling = false
      }

      const applySettings = () => {
        const panel = shellPanel()
        if (!panel) return
        panel.dataset.vxsEditorMode = settings.mode
        panel.style.setProperty(
          '--vxs-editor-font-size',
          Math.round(settings.fontSize) + 'px'
        )

        const modeDefault = q('#vxs-mode-default')
        const modeOld = q('#vxs-mode-old')
        const font = q('#vxs-font-size')
        const value = q('.vxsFontValue')

        if (modeDefault) modeDefault.checked = settings.mode === 'default'
        if (modeOld) modeOld.checked = settings.mode === 'old'
        if (font) font.value = String(Math.round(settings.fontSize))
        if (value) value.textContent = Math.round(settings.fontSize) + ' px'

        lastStyledMode = ''
        styleOutput()
      }

      const setPopoverOpen = open => {
        const popover = q('.vxsSettingsPopover')
        const gear = q('.vxsSettingsButton')
        if (!popover || !gear) return
        popover.classList.toggle('open', Boolean(open))
        gear.classList.toggle('open', Boolean(open))
      }

      const cancelClose = () => {
        if (closeTimer) window.clearTimeout(closeTimer)
        closeTimer = 0
      }

      const scheduleClose = () => {
        cancelClose()
        if (settingsOpenPinned) return
        closeTimer = window.setTimeout(() => setPopoverOpen(false), 160)
      }

      const ensureSettingsUi = () => {
        addRuntimeStyle()

        let gear = q('.vxsSettingsButton')
        const collapse = q('.collapse')

        if (!gear && collapse) {
          gear = collapse.cloneNode(true)
          gear.classList.add('vxsSettingsButton')
          gear.dataset.vxsSettingsButton = '1'
          gear.textContent = '⚙'
          gear.title = 'VXS Settings'
          gear.setAttribute('aria-label', 'VXS Settings')
          collapse.replaceWith(gear)

          gear.addEventListener('mouseenter', () => {
            cancelClose()
            setPopoverOpen(true)
          })
          gear.addEventListener('mouseleave', scheduleClose)
          gear.addEventListener('click', event => {
            event.preventDefault()
            event.stopPropagation()
            settingsOpenPinned = !settingsOpenPinned
            setPopoverOpen(settingsOpenPinned || !q('.vxsSettingsPopover')?.classList.contains('open'))
          })
        } else if (gear) {
          gear.textContent = '⚙'
          gear.title = 'VXS Settings'
        }

        let popover = q('.vxsSettingsPopover')
        if (!popover) {
          popover = document.createElement('section')
          popover.className = 'vxsSettingsPopover'
          popover.setAttribute('aria-label', 'VXS Settings')
          popover.innerHTML =
            '<div class="vxsSettingsTitle"><span>VXS SETTINGS</span><span>0.1.0</span></div>' +
            '<div class="vxsSettingsSection">' +
              '<span class="vxsSettingsLabel">Editor Display Mode</span>' +
              '<label class="vxsMode">' +
                '<input id="vxs-mode-default" type="radio" name="vxs-display-mode" value="default">' +
                '<span><span class="vxsModeName">Default Mode</span>' +
                  '<span class="vxsLegend">' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#CBD5DF"></i>White = Standard / Info</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#55D69E"></i>Green = Success / Ready</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#F1B85B"></i>Orange = Warning / Caution</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#FF6F7C"></i>Red = Error / Failed</span>' +
                  '</span>' +
                '</span>' +
              '</label>' +
              '<label class="vxsMode">' +
                '<input id="vxs-mode-old" type="radio" name="vxs-display-mode" value="old">' +
                '<span><span class="vxsModeName">OLD Mode</span>' +
                  '<span class="vxsLegend">' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#55D69E"></i>Green = Default text</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#FF6F7C"></i>Red = Error only</span>' +
                  '</span>' +
                '</span>' +
              '</label>' +
            '</div>' +
            '<div class="vxsSettingsSection">' +
              '<span class="vxsSettingsLabel">Font Size</span>' +
              '<div class="vxsFontRow"><span>A</span><input id="vxs-font-size" type="range" min="9" max="20" step="1"><span class="vxsFontValue"></span></div>' +
            '</div>'

          shellPanel()?.appendChild(popover)

          popover.addEventListener('mouseenter', cancelClose)
          popover.addEventListener('mouseleave', scheduleClose)

          q('#vxs-mode-default')?.addEventListener('change', event => {
            if (!event.target.checked) return
            settings = { ...settings, mode: 'default' }
            saveSettings()
            applySettings()
          })

          q('#vxs-mode-old')?.addEventListener('change', event => {
            if (!event.target.checked) return
            settings = { ...settings, mode: 'old' }
            saveSettings()
            applySettings()
          })

          q('#vxs-font-size')?.addEventListener('input', event => {
            settings = {
              ...settings,
              fontSize: Math.max(9, Math.min(20, Number(event.target.value) || 11))
            }
            saveSettings()
            applySettings()
          })
        }

        applySettings()
      }

      const tabLabel = tab =>
        String(tab?.title || '').split(' · ')[0].trim() ||
        String(tab?.firstChild?.textContent || '').trim()

      const visibleTabs = () =>
        qa('.tab').filter(tab => !closedTabs.has(tabLabel(tab)))

      const dismissTab = tab => {
        const label = tabLabel(tab)
        if (!label) return

        if (tab.classList.contains('busy')) {
          const close = tab.querySelector('.vxsTabClose')
          if (close) {
            close.classList.add('busy')
            close.title = 'Running shell cannot be closed'
          }
          return
        }

        const visible = visibleTabs()
        const active = tab.classList.contains('active')

        if (visible.length <= 1) {
          q('.tabAdd')?.click()
          closedTabs.add(label)
          queueRefresh()
          return
        }

        if (active) {
          const index = visible.indexOf(tab)
          const target = visible[index - 1] || visible[index + 1]
          target?.click()
        }

        closedTabs.add(label)
        queueRefresh()
      }

      const enhanceTabs = () => {
        for (const tab of qa('.tab')) {
          const label = tabLabel(tab)
          tab.classList.toggle('vxsTabClosed', closedTabs.has(label))
          if (closedTabs.has(label)) continue

          let close = tab.querySelector('.vxsTabClose')
          if (!close) {
            close = document.createElement('span')
            close.className = 'vxsTabClose'
            close.textContent = '×'
            close.setAttribute('role', 'button')
            close.setAttribute('aria-label', 'Close ' + label)
            close.title = 'Close ' + label
            close.addEventListener('pointerdown', event => {
              event.preventDefault()
              event.stopPropagation()
            })
            close.addEventListener('click', event => {
              event.preventDefault()
              event.stopPropagation()
              dismissTab(tab)
            })
            tab.appendChild(close)
          }

          const busy = tab.classList.contains('busy')
          close.classList.toggle('busy', busy)
          close.title = busy
            ? 'Running shell cannot be closed'
            : 'Close ' + label
        }
      }

      const applyBranding = () => {
        const brand = q('.title strong')
        if (brand) brand.textContent = 'Vertex eXecution Shell'

        const prompt = q('.prompt')
        if (prompt && prompt.textContent?.includes('VSH')) {
          prompt.textContent = prompt.textContent.replace('VSH', 'VXS')
        }

        const node = output()
        if (node) {
          const currentText = node.textContent || ''
          const nextText = normalizeVxsBrandText(currentText)

          if (nextText !== currentText) {
            node.textContent = nextText
            lastStyledText = ''
          }
        }

        qa('[title]').forEach(node => {
          const title = node.getAttribute('title')
          if (title?.includes('Vertex Shell')) {
            node.setAttribute('title', title.replaceAll('Vertex Shell', 'VXS'))
          }
        })
      }

      const refresh = () => {
        refreshQueued = false
        installSynchronousOutputBranding()
        installCanonicalClipboardCopy()
        installNativeVraAlias()
        applyBranding()
        ensureSettingsUi()
        enhanceTabs()
        styleOutput()
      }

      function queueRefresh() {
        if (refreshQueued) return
        refreshQueued = true
        window.requestAnimationFrame(refresh)
      }

      const observer = new MutationObserver(() => queueRefresh())
      observer.observe(shadow, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['class', 'title']
      })

      root.__VXS_RUNTIME__ = {
        refresh,
        settingsVersion: 1,
        closedTabs
      }

      refresh()
      return 'vxs-settings-tabs-runtime-installed'
    })()`

    for (const window of BrowserWindow.getAllWindows()) {
      if (window.isDestroyed() || window.webContents.isDestroyed()) continue
      window.setTitle('Vertex eXecution Shell')
      void window.webContents.executeJavaScript(script, true).catch(() => undefined)
    }
  }

  private active: ActiveExecution | null = null
  private cwd = fs.existsSync(DEFAULT_CWD)
    ? DEFAULT_CWD
    : process.cwd()

  private historyPath(): string {
    const root = path.join(app.getPath('userData'), 'vertex-shell')
    fs.mkdirSync(root, { recursive: true })
    return path.join(root, 'command-history.jsonl')
  }

  state(): VertexShellState {
    this.syncVxsBranding()
    return {
      generation: GENERATION,
      backend: resolveBackend(),
      cwd: this.cwd,
      busy: this.active !== null,
      activePid: this.active?.child.pid ?? null,
      activeCommandId: this.active?.commandId ?? null,
      historyPath: this.historyPath()
    }
  }

  setCwd(request: VertexShellSetCwdRequest): VertexShellState {
    if (this.active) {
      throw new Error('VERTEX_SHELL_BUSY')
    }
    if (!request?.cwd?.trim()) {
      throw new Error('VERTEX_SHELL_CWD_REQUIRED')
    }
    this.cwd = safeExistingDirectory(request.cwd.trim())
    return this.state()
  }

  async execute(
    request: VertexShellCommandRequest,
    sink: OutputSink
  ): Promise<VertexShellCommandResult> {
    this.syncVxsBranding()

    if (this.active) {
      throw new Error('VERTEX_SHELL_BUSY')
    }

    const command = request?.command?.trim() ?? ''
    if (!command) {
      throw new Error('VERTEX_SHELL_COMMAND_REQUIRED')
    }
    if (command.length > MAX_COMMAND_CHARS) {
      throw new Error('VERTEX_SHELL_COMMAND_TOO_LARGE')
    }

    const cwd = request.cwd?.trim()
      ? safeExistingDirectory(request.cwd.trim())
      : this.cwd
    this.cwd = cwd

    // VXS identity meta-command.
    // Inside the embedded VXS prompt, both `--version` and
    // the canonical `vxs --version` command are accepted.
    if (/^(?:vxs\s+)?--version$/i.test(command)) {
      const commandId = randomUUID()
      const versionText = [
        `VXS ${VXS_VERSION}`,
        VXS_CANONICAL_NAME,
        'Host: Vertex Session Portal',
        `Backend: ${resolveBackend()} (compatibility)`,
        ''
      ].join('\n')

      sink({
        commandId,
        kind: 'system',
        chunk: versionText,
        at: nowIso()
      })

      const result: VertexShellCommandResult = {
        commandId,
        command: redactCommand(command),
        cwd: this.cwd,
        backend: 'VXS_META',
        pid: null,
        exitCode: 0,
        durationMs: 0,
        stdoutBytes: Buffer.byteLength(versionText, 'utf8'),
        stderrBytes: 0,
        stopped: false
      }
      this.appendHistory(result)
      return result
    }

    // Bare VXS meta aliases are accepted inside the embedded VXS prompt.
    // Keep the original user command for history/redaction, but route the
    // recognized alias through the canonical command registry.
    const vxsRegistryCommand = /^--help$/i.test(command)
      ? 'vxs --help'
      : command

    const vxsStartedAt = Date.now()
    const vxsDispatch = executeVxsCommand(
      vxsRegistryCommand,
      {
        cwd: this.cwd,
        version: VXS_VERSION,
        canonicalName: VXS_CANONICAL_NAME,
        compatibilityBackend: resolveBackend()
      }
    )

    if (vxsDispatch?.kind === 'immediate') {
      const commandId = randomUUID()
      const outputBytes = Buffer.byteLength(vxsDispatch.output, 'utf8')

      sink({
        commandId,
        kind: vxsDispatch.stream,
        chunk: vxsDispatch.output,
        at: nowIso()
      })

      const result: VertexShellCommandResult = {
        commandId,
        command: redactCommand(command),
        cwd: this.cwd,
        backend: 'VXS_COMMAND',
        pid: null,
        exitCode: vxsDispatch.exitCode,
        durationMs: Date.now() - vxsStartedAt,
        stdoutBytes: vxsDispatch.stream === 'system' ? outputBytes : 0,
        stderrBytes: vxsDispatch.stream === 'stderr' ? outputBytes : 0,
        stopped: false
      }

      this.appendHistory(result)
      return result
    }

    const routedExecution = vxsDispatch?.kind === 'execute'
      ? vxsDispatch
      : null

    // Persistent cwd meta-command is only used for a simple standalone cd.
    // Compound PowerShell such as:
    //   cd G:\\...\\project; python scripts\\probe.py
    // must pass through to pwsh as one command.
    const hasCommandSeparator = /[;\r\n|&]/.test(command)
    const cd = routedExecution || hasCommandSeparator
      ? null
      : command.match(/^(?:cd|set-location)\s+(.+)$/i)
    if (cd) {
      const raw = cd[1].trim().replace(/^(['"])(.*)\1$/, '$2')
      const candidate = path.isAbsolute(raw) ? raw : path.resolve(cwd, raw)
      this.cwd = safeExistingDirectory(candidate)
      const commandId = randomUUID()
      sink({
        commandId,
        kind: 'system',
        chunk: `CWD → ${this.cwd}\n`,
        at: nowIso()
      })
      const result: VertexShellCommandResult = {
        commandId,
        command: redactCommand(command),
        cwd: this.cwd,
        backend: 'VERTEX_META',
        pid: null,
        exitCode: 0,
        durationMs: 0,
        stdoutBytes: 0,
        stderrBytes: 0,
        stopped: false
      }
      this.appendHistory(result)
      return result
    }

    const backend = resolveBackend()
    const executionCommand = routedExecution?.executionCommand ?? command
    const executionCwd = routedExecution?.executionCwd ?? cwd
    const providerPlan = routedExecution?.providerRequest
      ? planVxsProviderExecution(
          process.cwd(),
          routedExecution.providerRequest,
          backend,
          executionCommand
        )
      : null
    const executionBackend = providerPlan
      ? `VXS_${providerPlan.route}_${routedExecution?.capability ?? 'CAPABILITY'}`
      : routedExecution
        ? `VXS_${routedExecution.capability}`
        : backend
    const executionProgram = providerPlan?.program ?? backend
    const executionArgs = providerPlan?.args ?? [
      '-NoLogo',
      '-NoProfile',
      '-NonInteractive',
      '-Command',
      executionCommand
    ]
    const commandId = randomUUID()
    const startedAt = Date.now()

    if (routedExecution) {
      sink({
        commandId,
        kind: 'system',
        chunk: [
          `VXS ROUTE ${routedExecution.capability}`,
          `Workspace: ${executionCwd}`,
          `Adapter: ${routedExecution.routeSummary}`,
          `Provider: ${providerPlan?.route ?? 'POWERSHELL'}${providerPlan ? ` (${providerPlan.reason})` : ''}`,
          `Execute: ${providerPlan ? [executionProgram, ...executionArgs].join(' ') : executionCommand}`,
          ''
        ].join('\n'),
        at: nowIso()
      })
    }

    const child = spawn(
      executionProgram,
      executionArgs,
      {
        cwd: executionCwd,
        windowsHide: true,
        shell: false,
        stdio: ['pipe', 'pipe', 'pipe']
      }
    )

    const active: ActiveExecution = {
      commandId,
      command,
      cwd: executionCwd,
      backend: executionBackend,
      child,
      startedAt,
      stdoutBytes: 0,
      stderrBytes: 0,
      stdoutTruncated: false,
      stderrTruncated: false,
      stopped: false
    }
    this.active = active

    sink({
      commandId,
      kind: 'system',
      chunk: `RUN ${executionBackend} · PID ${child.pid ?? 'pending'} · ${executionCwd}\n`,
      at: nowIso()
    })

    const stream = (
      kind: 'stdout' | 'stderr',
      chunk: Buffer
    ): void => {
      const current = this.active
      if (!current || current.commandId !== commandId) return

      const byteField = kind === 'stdout' ? 'stdoutBytes' : 'stderrBytes'
      const truncateField = kind === 'stdout' ? 'stdoutTruncated' : 'stderrTruncated'
      current[byteField] += chunk.byteLength

      if (current[truncateField]) return
      if (current[byteField] > MAX_STREAM_BYTES) {
        current[truncateField] = true
        sink({
          commandId,
          kind: 'system',
          chunk: `[${kind.toUpperCase()} TRUNCATED AFTER ${MAX_STREAM_BYTES} BYTES]\n`,
          at: nowIso()
        })
        return
      }

      sink({
        commandId,
        kind,
        chunk: chunk.toString('utf8'),
        at: nowIso()
      })
    }

    child.stdout.on('data', (chunk: Buffer) => stream('stdout', chunk))
    child.stderr.on('data', (chunk: Buffer) => stream('stderr', chunk))

    return await new Promise<VertexShellCommandResult>((resolve, reject) => {
      child.once('error', error => {
        if (this.active?.commandId === commandId) {
          this.active = null
        }
        sink({
          commandId,
          kind: 'stderr',
          chunk: `START ERROR: ${error.message}\n`,
          at: nowIso()
        })
        reject(error)
      })

      child.once('close', code => {
        const snapshot = this.active?.commandId === commandId
          ? this.active
          : active

        const result: VertexShellCommandResult = {
          commandId,
          command: redactCommand(command),
          cwd: executionCwd,
          backend: executionBackend,
          pid: child.pid ?? null,
          exitCode: typeof code === 'number' ? code : -1,
          durationMs: Date.now() - startedAt,
          stdoutBytes: snapshot.stdoutBytes,
          stderrBytes: snapshot.stderrBytes,
          stopped: snapshot.stopped
        }

        if (this.active?.commandId === commandId) {
          this.active = null
        }

        this.appendHistory(result)
        sink({
          commandId,
          kind: 'system',
          chunk: `EXIT ${result.exitCode} · ${result.durationMs} ms${result.stopped ? ' · STOPPED' : ''}\n`,
          at: nowIso()
        })
        resolve(result)
      })
    })
  }

  async stop(): Promise<VertexShellState> {
    const current = this.active
    if (!current) return this.state()

    current.stopped = true
    const pid = current.child.pid

    if (typeof pid === 'number' && pid > 0) {
      await new Promise<void>(resolve => {
        const killer = spawn(
          'taskkill.exe',
          ['/PID', String(pid), '/T', '/F'],
          {
            windowsHide: true,
            shell: false,
            stdio: 'ignore'
          }
        )
        killer.once('error', () => {
          try { current.child.kill() } catch { /* best effort */ }
          resolve()
        })
        killer.once('close', () => resolve())
      })
    } else {
      try { current.child.kill() } catch { /* best effort */ }
    }

    return this.state()
  }

  private appendHistory(result: VertexShellCommandResult): void {
    const record = {
      schema: 'vertex-shell/command-evidence-1',
      generation: GENERATION,
      at: nowIso(),
      command_id: result.commandId,
      command: result.command,
      cwd: result.cwd,
      backend: result.backend,
      pid: result.pid,
      exit_code: result.exitCode,
      duration_ms: result.durationMs,
      stdout_bytes: result.stdoutBytes,
      stderr_bytes: result.stderrBytes,
      stopped: result.stopped
    }

    fs.appendFileSync(
      this.historyPath(),
      `${JSON.stringify(record)}\n`,
      'utf8'
    )
  }
}
