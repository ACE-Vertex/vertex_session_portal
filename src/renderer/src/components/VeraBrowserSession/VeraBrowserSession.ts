import { escapeHtml } from '../../shared/escape'
import { injectRelayMessage, type VeraRelayMessage } from './VeraRelayInjector'
import {
  injectWorkstationEvidence,
  VERA_EVIDENCE_RETURN_EVENT,
  VERA_EVIDENCE_RETURN_RESULT_EVENT,
  type VeraEvidenceReturnMessage,
  type VeraEvidenceReturnResult
} from './VeraEvidenceReturnInjector'
import styles from './VeraBrowserSession.css?inline'

type ElectronWebviewElement = HTMLElement & {
  reload: () => void
  goBack: () => void
  goForward: () => void
  canGoBack: () => boolean
  canGoForward: () => boolean
  getURL: () => string
  getWebContentsId: () => number
  loadURL: (url: string) => Promise<void>
}

type WebviewNavigateEvent = Event & {
  url?: string
}

type WebviewFailEvent = Event & {
  errorDescription?: string
  validatedURL?: string
}

const CHATGPT_HOME = 'https://chatgpt.com/'
const CHATGPT_PARTITION = 'persist:vertex-vera-chatgpt'
const VERA_RELAY_EVENT = 'vertex-vera-peer-relay'
const VERA_RELAY_RESULT_EVENT = 'vertex-vera-peer-relay-result'
const MAIN_VERA_IDS = ['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05'] as const

type VeraRelayResult = { relayId: string; from: string; to: string; ok: boolean; stage: string }

export class VeraBrowserSession extends HTMLElement {
  private readonly relayListener = (event: Event): void => {
    const relay = event as CustomEvent<VeraRelayMessage>
    if (!relay.detail || relay.detail.to !== this.sessionId()) return
    void this.deliverRelayMessage(relay.detail)
  }

  private readonly relayResultListener = (event: Event): void => {
    const result = (event as CustomEvent<VeraRelayResult>).detail
    if (!result || result.from !== this.sessionId()) return
    const target = result.to.replace('vera-', 'VERA')
    this.flashRelayStatus(result.ok ? `${target} ← CLIP PASTED` : `${target} · ${result.stage.toUpperCase()}`)
  }

  private readonly evidenceReturnListener = (event: Event): void => {
    const delivery = event as CustomEvent<VeraEvidenceReturnMessage>
    const message = delivery.detail
    const exactSessionId = this.getAttribute('session-id')
    if (!message || !exactSessionId || message.originSession !== exactSessionId) return
    void this.deliverWorkstationEvidence(message)
  }

  private browserReady = false
  private loading = true
  private failure = ''
  private pageTitle = 'ChatGPT'

  constructor() {
    super()
    this.attachShadow({ mode: 'open' })
  }

  static get observedAttributes(): string[] {
    return [
      'session-id',
      'session-title',
      'session-role',
      'mission-objective',
      'priority'
    ]
  }

  connectedCallback(): void {
    window.addEventListener(VERA_RELAY_EVENT, this.relayListener)
    window.addEventListener(VERA_RELAY_RESULT_EVENT, this.relayResultListener)
    window.addEventListener(VERA_EVIDENCE_RETURN_EVENT, this.evidenceReturnListener)
    this.restoreWidth()
    this.render()
  }

  disconnectedCallback(): void {
    window.removeEventListener(VERA_RELAY_EVENT, this.relayListener)
    window.removeEventListener(VERA_RELAY_RESULT_EVENT, this.relayResultListener)
    window.removeEventListener(VERA_EVIDENCE_RETURN_EVENT, this.evidenceReturnListener)
  }

  attributeChangedCallback(): void {
    if (this.isConnected) this.render()
  }

  private sessionId(): string {
    return this.getAttribute('session-id') ?? 'vera-01'
  }

  private storageKey(): string {
    return `vertex.vera.browser.last-url.${this.sessionId()}`
  }

  private widthStorageKey(): string {
    return `vertex.vera.browser.width.${this.sessionId()}`
  }


  private displayTitleStorageKey(): string {
    return `vertex.vera.display-title.${this.sessionId()}`
  }

  private defaultDisplayTitle(): string {
    return this.getAttribute('session-title') ?? this.sessionId().toUpperCase()
  }

  private displayTitle(): string {
    try {
      const stored = window.localStorage.getItem(this.displayTitleStorageKey())?.trim()
      return stored || this.defaultDisplayTitle()
    } catch {
      return this.defaultDisplayTitle()
    }
  }

  private beginDisplayTitleEdit(): void {
    const label = this.shadowRoot?.querySelector<HTMLElement>('.title')
    const input = this.shadowRoot?.querySelector<HTMLInputElement>('.titleInput')
    if (!label || !input) return
    input.value = this.displayTitle()
    label.hidden = true
    input.hidden = false
    input.focus()
    input.select()
  }

  private commitDisplayTitle(): void {
    const label = this.shadowRoot?.querySelector<HTMLElement>('.title')
    const input = this.shadowRoot?.querySelector<HTMLInputElement>('.titleInput')
    if (!label || !input) return
    const next = input.value.trim().slice(0, 120) || this.defaultDisplayTitle()
    try { window.localStorage.setItem(this.displayTitleStorageKey(), next) } catch { /* preference only */ }
    label.textContent = next
    label.hidden = false
    input.hidden = true
  }

  private cancelDisplayTitleEdit(): void {
    const label = this.shadowRoot?.querySelector<HTMLElement>('.title')
    const input = this.shadowRoot?.querySelector<HTMLInputElement>('.titleInput')
    if (!label || !input) return
    label.hidden = false
    input.hidden = true
  }

  private resetDisplayTitle(): void {
    try { window.localStorage.removeItem(this.displayTitleStorageKey()) } catch { /* preference only */ }
    const label = this.shadowRoot?.querySelector<HTMLElement>('.title')
    if (label) label.textContent = this.defaultDisplayTitle()
    this.cancelDisplayTitleEdit()
  }

  private minimumWidth(): number {
    const raw = getComputedStyle(this).getPropertyValue('--vertex-session-min-width')
    const parsed = Number.parseFloat(raw)
    return Number.isFinite(parsed) ? parsed : 600
  }

  private restoreWidth(): void {
    try {
      const stored = Number.parseFloat(window.localStorage.getItem(this.widthStorageKey()) ?? '')
      if (!Number.isFinite(stored) || stored < this.minimumWidth()) return
      this.setAttribute('manual-size', '')
      this.style.setProperty('--session-user-width', `${Math.round(stored)}px`)
    } catch {
      // Width persistence is a convenience; 600 px remains the canonical base width.
    }
  }

  private persistWidth(width: number): void {
    try {
      window.localStorage.setItem(this.widthStorageKey(), String(Math.round(width)))
    } catch {
      // A failed preference write must never block the browser session.
    }
  }

  private resetWidth(): void {
    this.removeAttribute('manual-size')
    this.style.removeProperty('--session-user-width')
    try {
      window.localStorage.removeItem(this.widthStorageKey())
    } catch {
      // Reset still succeeds for the current view even if storage is unavailable.
    }
  }

  private initialUrl(): string {
    try {
      const stored = window.localStorage.getItem(this.storageKey())
      return stored && this.isPersistableChatGptUrl(stored)
        ? stored
        : CHATGPT_HOME
    } catch {
      return CHATGPT_HOME
    }
  }

  private isPersistableChatGptUrl(value: string): boolean {
    try {
      const url = new URL(value)
      return url.protocol === 'https:' && url.hostname === 'chatgpt.com'
    } catch {
      return false
    }
  }

  private rememberUrl(value?: string): void {
    if (!value || !this.isPersistableChatGptUrl(value)) return
    try {
      window.localStorage.setItem(this.storageKey(), value)
    } catch {
      // Browser URL persistence is helpful, never required for Vera identity.
    }
  }


  private reportThread(value?: string): void {
    if (!value || !this.isPersistableChatGptUrl(value)) return
    void window.vertexPortal.updateVeraSessionThread({
      sessionId: this.sessionId(),
      threadUrl: value
    }).catch(() => {
      // Thread metadata is a Portal memory aid. Browser use must continue if it is unavailable.
    })
  }

  private browser(): ElectronWebviewElement | null {
    return this.shadowRoot?.querySelector('webview') as ElectronWebviewElement | null
  }

  private registerVraDownloadSource(browser: ElectronWebviewElement): void {
    try {
      const webContentsId = browser.getWebContentsId()
      if (!Number.isInteger(webContentsId) || webContentsId <= 0) return
      void window.vertexPortal.registerVraWebviewSource({
        sessionId: this.sessionId(),
        webContentsId
      }).catch(() => {
        // VRA capture metadata must never block the ChatGPT browser session.
      })
    } catch {
      // The webview may not have attached yet. dom-ready will retry.
    }
  }

  private bindResize(handle: HTMLElement): void {
    handle.addEventListener('pointerdown', event => {
      event.preventDefault()
      event.stopPropagation()

      const startX = event.clientX
      const startWidth = this.getBoundingClientRect().width

      this.setAttribute('manual-size', '')
      handle.dataset.dragging = 'true'

      try {
        handle.setPointerCapture(event.pointerId)
      } catch {
        // Pointer capture is only a convenience.
      }

      const move = (moveEvent: PointerEvent): void => {
        const next = Math.max(
          this.minimumWidth(),
          startWidth + (moveEvent.clientX - startX)
        )

        this.style.setProperty(
          '--session-user-width',
          `${Math.round(next)}px`
        )
      }

      const finish = (): void => {
        handle.dataset.dragging = 'false'
        this.persistWidth(this.getBoundingClientRect().width)
        window.removeEventListener('pointermove', move)
        window.removeEventListener('pointerup', finish)
        window.removeEventListener('pointercancel', finish)
      }

      window.addEventListener('pointermove', move)
      window.addEventListener('pointerup', finish)
      window.addEventListener('pointercancel', finish)
    })

    handle.addEventListener('dblclick', event => {
      event.preventDefault()
      event.stopPropagation()
      this.resetWidth()
    })
  }

  private requestPresentationHide(): void {
    const sessionId = this.sessionId()
    if (!MAIN_VERA_IDS.includes(sessionId as (typeof MAIN_VERA_IDS)[number])) return

    this.dispatchEvent(new CustomEvent<string>('vertex-session-hide-request', {
      bubbles: true,
      composed: true,
      detail: sessionId
    }))
  }

  private announceVisualActive(): void {
    this.dispatchEvent(new CustomEvent<string>('vertex-session-visual-active', {
      bubbles: true,
      composed: true,
      detail: this.sessionId()
    }))
  }

  // FINAL_WIRING_B_000054V1: absolute Vera Prompt Relay. Clipboard -> exact session composer, paste only.
  private async pasteClipboardTo(target: string): Promise<void> {
    if (!MAIN_VERA_IDS.includes(target as (typeof MAIN_VERA_IDS)[number]) || target === this.sessionId()) return
    const root = this.getRootNode()
    const targetNode = root instanceof ShadowRoot
      ? root.querySelector(`vera-browser-session[session-id="${target}"]`)
      : null
    if (!targetNode) { this.flashRelayStatus(`${target.replace('vera-', 'VERA')} · UNAVAILABLE`); return }
    let text = ''
    try { text = await window.vertexPortal.readClipboardText() } catch { this.flashRelayStatus('CLIPBOARD UNAVAILABLE'); return }
    if (!text.trim()) { this.flashRelayStatus('CLIPBOARD EMPTY'); return }
    const detail: VeraRelayMessage = {
      relayId: `${Date.now()}-${this.sessionId()}-${target}`,
      from: this.sessionId(),
      to: target,
      text,
      sentAt: Date.now()
    }
    window.dispatchEvent(new CustomEvent<VeraRelayMessage>(VERA_RELAY_EVENT, { detail }))
    this.flashRelayStatus(`${target.replace('vera-', 'VERA')} ← CLIP PASTE`)
  }

  private emitRelayResult(message: VeraRelayMessage, ok: boolean, stage: string): void {
    const detail: VeraRelayResult = { relayId: message.relayId, from: message.from, to: message.to, ok, stage }
    window.dispatchEvent(new CustomEvent<VeraRelayResult>(VERA_RELAY_RESULT_EVENT, { detail }))
  }

  private async deliverRelayMessage(message: VeraRelayMessage): Promise<void> {
    if (message.to !== this.sessionId()) return
    const browser = this.browser()
    if (!browser || !this.browserReady) { this.emitRelayResult(message, false, 'target-unavailable'); return }
    try {
      const result = await injectRelayMessage(browser, message)
      this.emitRelayResult(message, result.ok, result.stage)
    } catch {
      this.emitRelayResult(message, false, 'write-only-injection-failed')
    }
  }

  private bindDisplayTitle(): void {
    this.shadowRoot?.querySelector<HTMLElement>('.title')?.addEventListener('dblclick', () => this.beginDisplayTitleEdit())
    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="title-reset"]')?.addEventListener('click', () => this.resetDisplayTitle())
    const input = this.shadowRoot?.querySelector<HTMLInputElement>('.titleInput')
    input?.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); this.commitDisplayTitle() }
      if (event.key === 'Escape') { event.preventDefault(); this.cancelDisplayTitleEdit() }
    })
    input?.addEventListener('blur', () => this.cancelDisplayTitleEdit())
  }

  // FINAL_WIRING_B_000054V1: exact session write-only Evidence sink.
  private async deliverWorkstationEvidence(message: VeraEvidenceReturnMessage): Promise<void> {
    const sessionId = this.getAttribute('session-id') ?? ''
    const expectedVera = /^vera-0[1-5]$/.test(sessionId) ? `VERA${sessionId.slice(-2)}` : ''
    if (
      !/^vera-0[1-5]$/.test(sessionId) ||
      message.originSession !== sessionId ||
      message.originWindow !== sessionId ||
      message.originVera !== expectedVera
    ) {
      this.emitEvidenceReturnResult({
        deliveryId: message.deliveryId,
        jobId: message.jobId,
        originSession: sessionId,
        ok: false,
        stage: 'origin-mismatch-fail-closed'
      })
      return
    }

    const browser = this.browser()
    if (!browser || !this.browserReady) {
      this.emitEvidenceReturnResult({
        deliveryId: message.deliveryId,
        jobId: message.jobId,
        originSession: sessionId,
        ok: false,
        stage: 'session-not-ready'
      })
      return
    }

    try {
      const result = await injectWorkstationEvidence(browser, message)
      this.emitEvidenceReturnResult(result)
      this.flashRelayStatus(result.ok ? 'EVIDENCE ← WORKSTATION' : 'EVIDENCE WAIT')
    } catch (error) {
      console.error('[WORKSTATION EVIDENCE] write-only delivery failed', error)
      this.emitEvidenceReturnResult({
        deliveryId: message.deliveryId,
        jobId: message.jobId,
        originSession: sessionId,
        ok: false,
        stage: 'write-only-injection-failed'
      })
    }
  }

  private emitEvidenceReturnResult(result: VeraEvidenceReturnResult): void {
    window.dispatchEvent(new CustomEvent<VeraEvidenceReturnResult>(VERA_EVIDENCE_RETURN_RESULT_EVENT, { detail: result }))
  }

  private flashRelayStatus(label: string): void {
    const state = this.shadowRoot?.querySelector<HTMLElement>('.statusText')
    if (!state) return
    state.textContent = label
    window.setTimeout(() => this.updateStatus(), 1300)
  }

  private bindBrowser(): void {
    const browser = this.browser()
    if (!browser) return

    browser.addEventListener('focus', () => this.announceVisualActive())

    const markLoading = (): void => {
      this.loading = true
      this.failure = ''
      this.updateStatus()
    }

    const markReady = (): void => {
      this.loading = false
      this.browserReady = true
      this.failure = ''
      this.registerVraDownloadSource(browser)
      this.reportThread(browser.getURL())
      this.updateStatus()
    }

    const remember = (event: Event): void => {
      const nav = event as WebviewNavigateEvent
      const current = nav.url ?? browser.getURL()
      this.rememberUrl(current)
      this.reportThread(current)
      this.updateAddress(current)
    }

    browser.addEventListener('did-start-loading', markLoading)
    browser.addEventListener('did-stop-loading', markReady)
    browser.addEventListener('dom-ready', markReady)
    browser.addEventListener('did-navigate', remember)
    browser.addEventListener('did-navigate-in-page', remember)
    browser.addEventListener('page-title-updated', event => {
      const title = (event as Event & { title?: string }).title
      if (title) this.pageTitle = title
      this.updateStatus()
    })
    browser.addEventListener('did-fail-load', event => {
      const failure = event as WebviewFailEvent
      this.loading = false
      this.failure = failure.errorDescription || 'ChatGPT browser failed to load.'
      this.updateStatus()
    })

    this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="back"]')
      ?.addEventListener('click', () => {
        if (browser.canGoBack()) browser.goBack()
      })

    this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="forward"]')
      ?.addEventListener('click', () => {
        if (browser.canGoForward()) browser.goForward()
      })

    this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="reload"]')
      ?.addEventListener('click', () => browser.reload())

    this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="home"]')
      ?.addEventListener('click', () => {
        void browser.loadURL(CHATGPT_HOME)
      })

    this.shadowRoot?.querySelectorAll<HTMLButtonElement>('[data-relay-target]').forEach(button => {
      button.addEventListener('click', () => {
        const target = button.dataset.relayTarget
        if (target) void this.pasteClipboardTo(target)
      })
    })
    this.bindDisplayTitle()
    this.shadowRoot
      ?.querySelector<HTMLButtonElement>('[data-action="hide-window"]')
      ?.addEventListener('click', event => {
        event.preventDefault()
        event.stopPropagation()
        this.requestPresentationHide()
      })

  }

  private updateAddress(value?: string): void {
    const target = this.shadowRoot?.querySelector<HTMLElement>('.address')
    if (!target) return

    const current = value || this.browser()?.getURL() || CHATGPT_HOME
    try {
      const url = new URL(current)
      target.textContent = `${url.hostname}${url.pathname === '/' ? '' : url.pathname}`
    } catch {
      target.textContent = 'chatgpt.com'
    }
  }

  private updateStatus(): void {
    const state = this.shadowRoot?.querySelector<HTMLElement>('.statusText')
    const dot = this.shadowRoot?.querySelector<HTMLElement>('.statusDot')
    const error = this.shadowRoot?.querySelector<HTMLElement>('.browserError')
    const title = this.shadowRoot?.querySelector<HTMLElement>('.browserTitle')

    if (title) title.textContent = this.pageTitle

    if (state) {
      state.textContent = this.failure
        ? 'ERROR'
        : this.loading
          ? 'LOADING'
          : this.browserReady
            ? 'CHATGPT READY'
            : 'STARTING'
    }

    if (dot) {
      dot.dataset.state = this.failure
        ? 'error'
        : this.loading
          ? 'loading'
          : 'ready'
    }

    if (error) {
      error.textContent = this.failure
      error.toggleAttribute('data-visible', Boolean(this.failure))
    }
  }

  private render(): void {
    const sessionId = escapeHtml(this.sessionId())
    const title = escapeHtml(this.displayTitle())
    const role = this.getAttribute('session-role')
    const objective = this.getAttribute('mission-objective')
    const initialUrl = escapeHtml(this.initialUrl())

    this.shadowRoot!.innerHTML = `
      <style>${styles}</style>
      <article class="session">
        <div class="chrome">
          <div class="windowDots">
            <button type="button" class="windowDot closeDot" data-action="hide-window" title="Hide Vera window · session preserved" aria-label="Hide Vera window"></button>
            <span class="windowDot minimizeDot"></span>
            <span class="windowDot readyDot"></span>
          </div>
          <div class="address">chatgpt.com</div>
          <div class="chromeState" aria-label="Vera window state"></div>
        </div>

        <header class="header">
          <div>
            <div class="eyebrow">VERA · CHATGPT BROWSER SESSION</div>
            <div class="titleEditor"><div class="title" title="Double-click to edit">${title}</div><input class="titleInput" maxlength="120" hidden aria-label="Vera display title"><button type="button" class="titleReset" data-action="title-reset" title="Reset to Project Name">↺</button></div>
          </div>
          <div class="headerActions">
            <div class="status">
              <span class="statusDot" data-state="loading"></span>
              <span class="statusText">LOADING</span>
            </div>
          </div>
        </header>

        ${role ? `<div class="roleBar">${escapeHtml(role)}${objective ? ` · ${escapeHtml(objective)}` : ''}</div>` : ''}

        <div class="browserToolbar">
          <button type="button" data-action="back" title="Back">←</button>
          <button type="button" data-action="forward" title="Forward">→</button>
          <button type="button" data-action="reload" title="Reload">↻</button>
          <button type="button" data-action="home" title="ChatGPT Home">⌂</button>
          <span class="relayTargets" aria-label="Prompt Relay absolute Vera targets">
            ${MAIN_VERA_IDS.map((id, index) => `<button type="button" class="relayTargetButton" data-relay-target="${id}" title="Paste clipboard to ${id}" ${id === this.sessionId() ? 'disabled' : ''}>${index + 1}</button>`).join('')}
          </span>
          <span class="browserTitle">ChatGPT</span>
          <span class="accountMode">SHARED ACCOUNT · INDEPENDENT THREAD</span>
        </div>


        <section class="browserBody">
          <webview
            class="chatgptView"
            src="${initialUrl}"
            partition="${CHATGPT_PARTITION}"
            allowpopups
          ></webview>
          <div class="browserError"></div>
        </section>

        <footer class="sessionFoot">
          <span>PRIMARY · VERA</span>
          <span>ACCOUNT SESSION · PERSISTENT</span>
          <span>MEMORY SOURCE · CHATGPT ACCOUNT + PORTAL</span>
          <span>THREAD MAP · VCA CLOCK BRIDGE</span>
        </footer>

        <div class="resizeRail" title="Drag to resize · double-click to reset"></div>
      </article>
    `

    this.shadowRoot!.querySelector<HTMLElement>('.session')?.addEventListener('pointerdown', () => {
      this.announceVisualActive()
    }, true)

    const resize = this.shadowRoot!.querySelector<HTMLElement>('.resizeRail')
    if (resize) this.bindResize(resize)
    this.bindBrowser()
    this.updateStatus()
  }
}

customElements.define('vera-browser-session', VeraBrowserSession)
