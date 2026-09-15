import type {
  VertexShellBridge,
  VertexShellState,
  VertexShellStreamEvent
} from '../../../../shared/vertex-shell-contracts'
import { escapeHtml } from '../../shared/escape'
import styles from './VertexShellUnit.css?inline'

type ShellApi = VertexShellBridge | undefined

function shellApi(): ShellApi {
  return (window as any)?.api?.vertexShell as ShellApi
}

export class VertexShellUnit extends HTMLElement {
  private state: VertexShellState | null = null
  private unsubscribeOutput?: () => void
  private history: string[] = []
  private historyIndex = -1
  private expanded = true

  connectedCallback(): void {
    this.attachShadow({ mode: 'open' })
    this.render()
    void this.refresh()
    this.bindOutput()
  }

  disconnectedCallback(): void {
    this.unsubscribeOutput?.()
    this.unsubscribeOutput = undefined
  }

  private bindOutput(): void {
    const api = shellApi()
    this.unsubscribeOutput?.()
    this.unsubscribeOutput = api?.onOutput((event: VertexShellStreamEvent) => {
      this.appendOutput(event)
    })
  }

  private async refresh(): Promise<void> {
    const api = shellApi()
    if (!api) {
      this.state = null
      this.render()
      return
    }
    try {
      this.state = await api.state()
    } catch {
      this.state = null
    }
    this.render()
  }

  private appendOutput(event: VertexShellStreamEvent): void {
    const out = this.shadowRoot?.querySelector<HTMLPreElement>('.output')
    if (!out) return
    const prefix =
      event.kind === 'stderr'
        ? 'ERR │ '
        : event.kind === 'system'
          ? 'VXS │ '
          : '    │ '
    out.textContent += `${prefix}${event.chunk}`
    out.scrollTop = out.scrollHeight
  }

  private render(): void {
    if (!this.shadowRoot) return

    const bridgeReady = Boolean(shellApi())
    const busy = this.state?.busy ?? false
    const cwd = this.state?.cwd ?? 'G:\\Vertex_Project\\Development'
    const backend = this.state?.backend ?? 'pwsh.exe'
    const status = bridgeReady
      ? busy
        ? `RUNNING · PID ${this.state?.activePid ?? '…'}`
        : 'READY'
      : 'BRIDGE OFFLINE'

    this.shadowRoot.innerHTML = `
      <style>${styles}</style>
      <section class="shell ${this.expanded ? 'expanded' : 'collapsed'}">
        <header class="header">
          <div class="brand">
            <span class="glyph">›_</span>
            <div>
              <strong>VXS</strong>
              <small>VERTEX eXecution Shell · POWERSHELL COMPATIBILITY</small>
            </div>
          </div>
          <div class="telemetry">
            <span class="status ${busy ? 'busy' : bridgeReady ? 'ready' : 'offline'}">${escapeHtml(status)}</span>
            <span class="backend">${escapeHtml(backend)}</span>
            <button class="toggle" title="Collapse / expand">${this.expanded ? '⌄' : '⌃'}</button>
          </div>
        </header>

        <div class="cwdRow">
          <span>CWD</span>
          <input class="cwd" value="${escapeHtml(cwd)}" spellcheck="false">
          <button class="setCwd">SET</button>
        </div>

        <pre class="output" aria-live="polite">VXS 0.1.0
Vertex eXecution Shell
Type --version or vxs --version for identity.
PowerShell remains the compatibility backend while Vertex-native commands expand.
</pre>

        <div class="composer">
          <span class="prompt">VXS ›</span>
          <input
            class="command"
            type="text"
            autocomplete="off"
            spellcheck="false"
            placeholder="${bridgeReady ? 'Enter VXS or host command…' : 'Awaiting Session Portal wiring…'}"
            ${bridgeReady ? '' : 'disabled'}
          >
          <button class="run" ${bridgeReady && !busy ? '' : 'disabled'}>RUN</button>
          <button class="stop" ${busy ? '' : 'disabled'}>STOP</button>
          <button class="clear">CLEAR</button>
        </div>
      </section>
    `

    this.bindUi()
  }

  private bindUi(): void {
    const root = this.shadowRoot
    if (!root) return

    const command = root.querySelector<HTMLInputElement>('.command')
    const run = root.querySelector<HTMLButtonElement>('.run')
    const stop = root.querySelector<HTMLButtonElement>('.stop')
    const clear = root.querySelector<HTMLButtonElement>('.clear')
    const toggle = root.querySelector<HTMLButtonElement>('.toggle')
    const cwd = root.querySelector<HTMLInputElement>('.cwd')
    const setCwd = root.querySelector<HTMLButtonElement>('.setCwd')

    const execute = async (): Promise<void> => {
      const api = shellApi()
      const value = command?.value.trim() ?? ''
      if (!api || !value || this.state?.busy) return

      this.history.push(value)
      this.historyIndex = this.history.length
      if (command) {
        command.value = ''
        command.disabled = true
      }

      try {
        this.state = {
          ...(this.state ?? await api.state()),
          busy: true
        }
        this.render()
        await api.execute({
          command: value,
          cwd: this.state?.cwd ?? undefined
        })
      } catch (error) {
        this.appendOutput({
          commandId: 'local',
          kind: 'stderr',
          chunk: `${error instanceof Error ? error.message : String(error)}\n`,
          at: new Date().toISOString()
        })
      } finally {
        await this.refresh()
        this.shadowRoot?.querySelector<HTMLInputElement>('.command')?.focus()
      }
    }

    run?.addEventListener('click', () => void execute())

    command?.addEventListener('keydown', event => {
      if (event.isComposing) return

      if (event.key === 'Enter') {
        event.preventDefault()
        void execute()
        return
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault()
        if (this.history.length === 0) return
        this.historyIndex = Math.max(0, this.historyIndex - 1)
        command.value = this.history[this.historyIndex] ?? ''
        command.setSelectionRange(command.value.length, command.value.length)
        return
      }

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        if (this.history.length === 0) return
        this.historyIndex = Math.min(this.history.length, this.historyIndex + 1)
        command.value =
          this.historyIndex >= this.history.length
            ? ''
            : this.history[this.historyIndex] ?? ''
      }
    })

    stop?.addEventListener('click', async () => {
      const api = shellApi()
      if (!api) return
      await api.stop()
      await this.refresh()
    })

    clear?.addEventListener('click', () => {
      const out = root.querySelector<HTMLPreElement>('.output')
      if (out) out.textContent = ''
    })

    toggle?.addEventListener('click', () => {
      this.expanded = !this.expanded
      this.render()
    })

    setCwd?.addEventListener('click', async () => {
      const api = shellApi()
      const value = cwd?.value.trim() ?? ''
      if (!api || !value) return
      try {
        this.state = await api.setCwd({ cwd: value })
      } catch (error) {
        this.appendOutput({
          commandId: 'local',
          kind: 'stderr',
          chunk: `CWD ERROR: ${error instanceof Error ? error.message : String(error)}\n`,
          at: new Date().toISOString()
        })
      }
      this.render()
    })
  }
}

if (!customElements.get('vertex-shell-unit')) {
  customElements.define('vertex-shell-unit', VertexShellUnit)
}
