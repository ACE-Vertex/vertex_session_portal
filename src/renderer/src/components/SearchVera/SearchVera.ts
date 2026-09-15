import type { RetrievalHit, SessionChatMessage } from '../../../../shared/contracts'
import { escapeHtml } from '../../shared/escape'
import styles from './SearchVera.css?inline'

export class SearchVera extends HTMLElement {
  static get observedAttributes(): string[] { return ['session-id', 'priority'] }

  private history: SessionChatMessage[] = []
  private retrieval: RetrievalHit[] = []
  private busy = false

  constructor() {
    super()
    this.attachShadow({ mode: 'open' })
  }

  connectedCallback(): void {
    this.render()
    void this.loadState()
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

  private async loadState(): Promise<void> {
    const id = this.getAttribute('session-id')
    if (!id) return

    const [history, retrieval] = await Promise.all([
      window.vertexPortal.getSessionConversation(id).catch(() => []),
      window.vertexPortal.getSessionRetrieval(id).catch(() => [])
    ])

    this.history = history
    this.retrieval = retrieval
    this.render()
  }

  private async send(body: string): Promise<void> {
    const id = this.getAttribute('session-id')
    if (!id || this.busy) return
    const query = body.trim()
    if (!query) return

    this.busy = true
    this.render()

    try {
      const turn = await window.vertexPortal.sendSessionMessage({ sessionId: id, body: query })
      this.retrieval = turn.retrieval
      await this.loadState()
    } finally {
      this.busy = false
      this.render()
    }
  }

  private autoGrow(textarea: HTMLTextAreaElement): void {
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(Math.max(textarea.scrollHeight, 38), 72)}px`
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
    const sessionId = escapeHtml(this.getAttribute('session-id') ?? 'vera-search')
    const priority = this.hasAttribute('priority')

    const messages = this.history.length > 0
      ? this.history.map(message => `
          <div class="message ${message.role.toLowerCase()}">
            <div class="messageRole">${message.role}</div>
            <div class="messageBody">${escapeHtml(message.body)}</div>
          </div>
        `).join('')
      : `
        <div class="empty">
          <div class="scanRing"></div>
          <strong>Search Vera</strong>
          <span>Local information desk for Project / Evidence.</span>
        </div>
      `

    const hits = this.retrieval.length > 0
      ? this.retrieval.map(hit => `
          <article class="hit">
            <div class="hitMeta">
              <strong>${escapeHtml(hit.source)}</strong>
              <span>${escapeHtml(hit.relativePath)}:${hit.lineStart}-${hit.lineEnd}</span>
            </div>
            <pre>${escapeHtml(hit.snippet)}</pre>
          </article>
        `).join('')
      : `<div class="noHits">No retrieval Evidence yet.</div>`

    this.shadowRoot!.innerHTML = `
      <style>${styles}</style>
      <article class="search">
        <div class="chrome">
          <div class="windowDots"><span></span><span></span><span></span></div>
          <div class="address">vertex://search/${sessionId}</div>
          <div class="chromeState">${priority ? 'EXPANDED' : 'TILE'}</div>
        </div>

        <header class="header">
          <div><div class="eyebrow">SEARCH VERA</div><div class="title">Information Desk / Retrieval</div></div>
          <div class="status"><span class="statusDot"></span>${this.busy ? 'SEARCHING' : 'READY'}</div>
        </header>

        <section class="capabilities">
          <span class="live">PROJECT · LIVE</span>
          <span class="live">EVIDENCE · LIVE</span>
          <span class="live">VCR · SQLITE</span>
          <span class="live">VCA · SQLITE</span>
        </section>

        <div class="workspace">
          <section class="conversation">${messages}</section>
          <section class="evidence"><div class="sectionTitle">RETRIEVAL EVIDENCE</div>${hits}</section>
        </div>

        <form class="composer">
          <div class="composerTop">
            <button class="utility" type="button" title="Filters">⌘</button>
            <textarea rows="1" placeholder="Search Project / Evidence…" ${this.busy ? 'disabled' : ''}></textarea>
            <button class="iconButton sendButton" type="submit" title="Search" ${this.busy ? 'disabled' : ''}>➤</button>
            <button class="iconButton expandButton" type="button" title="Expand Search Vera">⛶</button>
          </div>
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
    const resizeRail = this.shadowRoot!.querySelector<HTMLElement>('.resizeRail')

    if (resizeRail) this.bindResize(resizeRail)

    textarea?.addEventListener('input', () => this.autoGrow(textarea))
    textarea?.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        form?.requestSubmit()
      }
    })

    expand?.addEventListener('click', event => {
      event.preventDefault()
      event.stopPropagation()
      this.requestPriority()
    })

    form?.addEventListener('submit', event => {
      event.preventDefault()
      event.stopPropagation()
      const body = textarea?.value ?? ''
      if (textarea) {
        textarea.value = ''
        textarea.style.height = 'auto'
      }
      void this.send(body)
    })
  }
}

customElements.define('search-vera', SearchVera)
