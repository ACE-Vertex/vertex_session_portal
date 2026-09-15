import type {
  SessionChatMessage,
  SessionContextAttachment,
  SessionContextScope
} from '../../../../shared/contracts'
import { escapeHtml } from '../../shared/escape'
import styles from './VeraSession.css?inline'

export class VeraSession extends HTMLElement {
  static get observedAttributes(): string[] {
    return ['session-id', 'session-title', 'session-role', 'mission-objective', 'priority']
  }

  private history: SessionChatMessage[] = []
  private busy = false
  private draft = ''
  private attachments: SessionContextAttachment[] = []
  private contextScope: SessionContextScope = 'SESSION'
  private targetMenuOpen = false

  constructor() {
    super()
    this.attachShadow({ mode: 'open' })
  }

  connectedCallback(): void {
    this.render()
    void this.loadHistory()
  }

  attributeChangedCallback(): void {
    if (this.isConnected) this.render()
  }

  private requestPriority(): void {
    const id = this.getAttribute('session-id')
    if (!id) return

    this.dispatchEvent(new CustomEvent<string>('vertex-session-priority', {
      bubbles: true,
      composed: true,
      detail: id
    }))
  }

  private async loadHistory(renderAfter = true): Promise<void> {
    const id = this.getAttribute('session-id')
    if (!id) return

    try {
      this.history = await window.vertexPortal.getSessionConversation(id)
    } catch {
      this.history = []
    }

    if (renderAfter) this.render()
  }

  private focusComposer(): void {
    requestAnimationFrame(() => {
      const textarea = this.shadowRoot?.querySelector<HTMLTextAreaElement>('.composer textarea')
      if (!textarea || textarea.disabled) return
      textarea.focus({ preventScroll: true })
      const end = textarea.value.length
      textarea.setSelectionRange(end, end)
    })
  }

  private async send(
    body: string,
    attachments: SessionContextAttachment[],
    contextScope: SessionContextScope
  ): Promise<void> {
    const id = this.getAttribute('session-id')
    if (!id || this.busy) return
    const normalized = body.trim()
    if (!normalized) return

    this.busy = true
    this.render()
    this.focusComposer()

    try {
      await window.vertexPortal.sendSessionMessage({
        sessionId: id,
        body: normalized,
        contextScope,
        attachments
      })
      await this.loadHistory(false)
      this.attachments = []
      this.contextScope = 'SESSION'
      this.targetMenuOpen = false
    } finally {
      this.busy = false
      this.render()
      this.focusComposer()
    }
  }

  private scopeLabel(scope: SessionContextScope): string {
    if (scope === 'PROJECT') return 'PROJECT'
    if (scope === 'EVIDENCE') return 'EVIDENCE'
    if (scope === 'PROJECT_EVIDENCE') return 'PROJECT + EVIDENCE'
    return 'SESSION'
  }

  private scopeMenu(): string {
    if (!this.targetMenuOpen) return ''

    const scopes: Array<{ value: SessionContextScope; label: string; note: string }> = [
      { value: 'SESSION', label: 'SESSION ONLY', note: 'Conversation history only' },
      { value: 'PROJECT', label: 'PROJECT', note: 'Project retrieval context' },
      { value: 'EVIDENCE', label: 'EVIDENCE', note: 'Evidence retrieval context' },
      { value: 'PROJECT_EVIDENCE', label: 'PROJECT + EVIDENCE', note: 'Both local retrieval sources' }
    ]

    return `
      <div class="targetMenu" role="menu" aria-label="Context target">
        ${scopes.map(item => `
          <button class="targetOption" type="button" data-scope="${item.value}" data-active="${item.value === this.contextScope}">
            <strong>${item.label}</strong>
            <span>${item.note}</span>
          </button>
        `).join('')}
      </div>
    `
  }

  private contextStrip(): string {
    if (this.attachments.length === 0 && this.contextScope === 'SESSION') return ''

    return `
      <div class="contextStrip">
        <span class="scopeChip">TARGET · ${this.scopeLabel(this.contextScope)}</span>
        ${this.attachments.map((attachment, index) => `
          <span class="attachmentChip" title="${escapeHtml(attachment.path)}">
            ${escapeHtml(attachment.name)}
            <button type="button" data-remove-attachment="${index}" aria-label="Remove ${escapeHtml(attachment.name)}">×</button>
          </span>
        `).join('')}
      </div>
    `
  }

  private autoGrow(textarea: HTMLTextAreaElement): void {
    const compactHeight = 38
    const expansionTrigger = 150
    const expandedMinimum = 238
    const maximum = 850
    const composer = textarea.closest<HTMLFormElement>('.composer')

    textarea.style.height = `${compactHeight}px`
    const contentHeight = textarea.scrollHeight
    const expanded = contentHeight > expansionTrigger

    if (composer) {
      composer.dataset.expanded = expanded ? 'true' : 'false'
    }

    if (!expanded) {
      textarea.style.height = `${compactHeight}px`
      return
    }

    const next = Math.min(Math.max(contentHeight, expandedMinimum), maximum)
    textarea.style.height = `${next}px`
  }


  private bindResize(
    handle: HTMLElement
  ): void {
    const readMinimum =
      (): number => {
        const style =
          getComputedStyle(this)

        const token =
          this.hasAttribute('priority')
            ? '--vertex-session-priority-width'
            : '--vertex-session-min-width'

        const fallback =
          this.hasAttribute('priority')
            ? 1200
            : 600

        return (
          Number.parseFloat(
            style.getPropertyValue(token)
          ) || fallback
        )
      }

    handle.addEventListener(
      'pointerdown',
      (event) => {
        event.preventDefault()
        event.stopPropagation()

        const startX =
          event.clientX

        const startWidth =
          this.getBoundingClientRect()
            .width

        this.setAttribute(
          'manual-size',
          ''
        )

        handle.dataset.dragging =
          'true'

        try {
          handle.setPointerCapture(
            event.pointerId
          )
        } catch {
          // Pointer capture is a convenience, not a sizing requirement.
        }

        const move =
          (moveEvent:
            PointerEvent): void => {
            const minimum =
              readMinimum()

            const next =
              Math.max(
                minimum,
                startWidth +
                  (
                    moveEvent.clientX -
                    startX
                  )
              )

            this.style.setProperty(
              '--session-user-width',
              `${Math.round(next)}px`
            )
          }

        const finish =
          (): void => {
            handle.dataset.dragging =
              'false'

            window.removeEventListener(
              'pointermove',
              move
            )

            window.removeEventListener(
              'pointerup',
              finish
            )

            window.removeEventListener(
              'pointercancel',
              finish
            )
          }

        window.addEventListener(
          'pointermove',
          move
        )

        window.addEventListener(
          'pointerup',
          finish
        )

        window.addEventListener(
          'pointercancel',
          finish
        )
      }
    )

    handle.addEventListener(
      'dblclick',
      (event) => {
        event.preventDefault()
        event.stopPropagation()

        this.removeAttribute(
          'manual-size'
        )

        this.style.removeProperty(
          '--session-user-width'
        )
      }
    )
  }

  private render(): void {
    const sessionId = escapeHtml(this.getAttribute('session-id') ?? 'vera')
    const title = escapeHtml(this.getAttribute('session-title') ?? 'Vera')
    const role = this.getAttribute('session-role')
    const objective = this.getAttribute('mission-objective')
    const priority = this.hasAttribute('priority')
    const label = priority ? 'PRIORITY SESSION' : 'VERA SESSION'

    const messages = this.history.length > 0
      ? this.history.map(message => `
          <div class="message ${message.role.toLowerCase()}">
            <div class="messageRole">${message.role}</div>
            <div class="messageBody">${escapeHtml(message.body)}</div>
          </div>
        `).join('')
      : `
        <div class="empty">
          <div class="orb"></div>
          <strong>${title}</strong>
          <span>${objective ? `Mission: ${escapeHtml(objective)}` : 'Independent Vera session. Ready for mission context.'}</span>
        </div>
      `

    this.shadowRoot!.innerHTML = `
      <style>${styles}</style>
      <article class="session">
        <div class="chrome">
          <div class="windowDots"><span></span><span></span><span></span></div>
          <div class="address">vertex://session/${sessionId}</div>
          <div class="chromeState">${priority ? 'EXPANDED' : 'TILE'}</div>
        </div>

        <header class="header">
          <div><div class="eyebrow">${label}</div><div class="title">${title}</div></div>
          <div class="status"><span class="statusDot"></span>${this.busy ? 'THINKING' : 'READY'}</div>
        </header>

        ${role ? `<div class="roleBar">${escapeHtml(role)}</div>` : ''}

        <section class="body"><div class="history">${messages}</div></section>

        <form class="composer">
          ${this.contextStrip()}
          <div class="composerTop">
            <button class="utility attachButton" type="button" data-action="attach-context" title="Attach local text context">＋</button>
            <button class="utility targetButton" type="button" data-action="target-context" data-active="${this.contextScope !== 'SESSION'}" title="Choose context target: ${this.scopeLabel(this.contextScope)}">◎</button>
            <textarea name="prompt" rows="1" placeholder="Message Vera…"></textarea>
            <button class="iconButton sendButton" type="submit" title="Send" ${this.busy ? 'disabled' : ''}>➤</button>
            <button class="iconButton expandButton" type="button" title="Expand this session">⛶</button>
          </div>
          ${this.scopeMenu()}
        </form>
        <div
          class="resizeRail"
          title="Drag to resize · double-click to reset"
        ></div>
      </article>
    `

    const form = this.shadowRoot!.querySelector<HTMLFormElement>('.composer')
    const textarea = form?.querySelector<HTMLTextAreaElement>('textarea')
    const expand = form?.querySelector<HTMLButtonElement>('.expandButton')
    const attach = form?.querySelector<HTMLButtonElement>('[data-action="attach-context"]')
    const target = form?.querySelector<HTMLButtonElement>('[data-action="target-context"]')

    if (textarea) {
      textarea.value = this.draft
      this.autoGrow(textarea)
    }
    const resizeRail = this.shadowRoot!.querySelector<HTMLElement>('.resizeRail')

    if (resizeRail) this.bindResize(resizeRail)

    textarea?.addEventListener('input', () => {
      this.draft = textarea.value
      this.autoGrow(textarea)
    })
    textarea?.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        if (this.busy) {
          this.focusComposer()
          return
        }
        form?.requestSubmit()
      }
    })

    attach?.addEventListener('click', event => {
      event.preventDefault()
      event.stopPropagation()
      void window.vertexPortal.browseSessionContextFile().then(attachment => {
        if (!attachment) {
          this.focusComposer()
          return
        }

        const exists = this.attachments.some(item => item.path === attachment.path)
        if (!exists && this.attachments.length < 5) this.attachments.push(attachment)
        this.render()
        this.focusComposer()
      }).catch(() => {
        this.focusComposer()
      })
    })

    target?.addEventListener('click', event => {
      event.preventDefault()
      event.stopPropagation()
      this.targetMenuOpen = !this.targetMenuOpen
      this.render()
      this.focusComposer()
    })

    for (const option of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('[data-scope]')) {
      option.addEventListener('click', event => {
        event.preventDefault()
        event.stopPropagation()
        this.contextScope = option.dataset.scope as SessionContextScope
        this.targetMenuOpen = false
        this.render()
        this.focusComposer()
      })
    }

    for (const remove of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('[data-remove-attachment]')) {
      remove.addEventListener('click', event => {
        event.preventDefault()
        event.stopPropagation()
        const index = Number.parseInt(remove.dataset.removeAttachment ?? '-1', 10)
        if (index >= 0 && index < this.attachments.length) this.attachments.splice(index, 1)
        this.render()
        this.focusComposer()
      })
    }

    expand?.addEventListener('click', event => {
      event.preventDefault()
      event.stopPropagation()
      this.requestPriority()
    })

    form?.addEventListener('submit', event => {
      event.preventDefault()
      event.stopPropagation()
      if (this.busy) {
        this.focusComposer()
        return
      }

      const body = textarea?.value ?? this.draft
      if (!body.trim()) {
        this.focusComposer()
        return
      }

      this.draft = ''
      if (textarea) {
        textarea.value = ''
        textarea.style.height = '38px'
        if (form) form.dataset.expanded = 'false'
      }
      const attachments = [...this.attachments]
      const contextScope = this.contextScope
      void this.send(body, attachments, contextScope)
    })
  }
}

customElements.define('vera-session', VeraSession)
