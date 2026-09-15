import styles from './VeraWindowScaler.css?inline'

const STORAGE_KEY = 'vertex.portal.active-vera-count'
const MIN_COUNT = 3
const MAX_COUNT = 5
const DYNAMIC_IDS = ['vera-04', 'vera-05'] as const

export class VeraWindowScaler extends HTMLElement {
  constructor() {
    super()
    this.attachShadow({ mode: 'open' })
  }

  connectedCallback(): void {
    this.render()
    requestAnimationFrame(() => this.applyCount(this.readCount()))
  }

  private readCount(): number {
    try {
      const raw = Number.parseInt(window.localStorage.getItem(STORAGE_KEY) ?? '', 10)
      if (Number.isFinite(raw)) return Math.min(MAX_COUNT, Math.max(MIN_COUNT, raw))
    } catch {
      // Preference persistence is optional. Canonical default remains three windows.
    }
    return MIN_COUNT
  }

  private writeCount(count: number): void {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(count))
    } catch {
      // Current-session switching must still work if localStorage is unavailable.
    }
  }

  private mainFrameRoot(): ShadowRoot | null {
    const root = this.getRootNode()
    return root instanceof ShadowRoot ? root : null
  }

  private buildDynamicPane(sessionId: (typeof DYNAMIC_IDS)[number]): HTMLElement {
    const index = sessionId === 'vera-04' ? '04' : '05'
    const pane = document.createElement('vera-browser-session')
    pane.setAttribute('session-id', sessionId)
    pane.setAttribute('session-title', `VERA ${index}`)
    pane.setAttribute('session-role', 'INDEPENDENT VERA')
    pane.setAttribute('mission-objective', 'Human assigned session')
    pane.setAttribute('data-dynamic-vera-window', '')
    return pane
  }

  private applyCount(count: number): void {
    const clamped = Math.min(MAX_COUNT, Math.max(MIN_COUNT, count))
    const root = this.mainFrameRoot()
    const track = root?.querySelector<HTMLElement>('.sessionTrack')
    if (!track) return

    const dispatchLane = track.querySelector('vertex-vra-dispatch-lane')
    const wanted = new Set(DYNAMIC_IDS.slice(0, clamped - MIN_COUNT))

    for (const id of DYNAMIC_IDS) {
      const existing = track.querySelector<HTMLElement>(
        `vera-browser-session[session-id="${id}"]`
      )

      if (wanted.has(id)) {
        if (!existing) {
          const pane = this.buildDynamicPane(id)
          track.insertBefore(pane, dispatchLane)
        }
      } else if (existing?.hasAttribute('data-dynamic-vera-window')) {
        existing.remove()
      }
    }

    this.writeCount(clamped)
    this.updateButtons(clamped)
    this.dispatchEvent(new CustomEvent<number>('vertex-vera-window-count-changed', {
      bubbles: true,
      composed: true,
      detail: clamped
    }))
  }

  private updateButtons(count: number): void {
    for (const button of this.shadowRoot?.querySelectorAll<HTMLButtonElement>('button[data-count]') ?? []) {
      const active = Number(button.dataset.count) === count
      button.toggleAttribute('data-active', active)
      button.setAttribute('aria-pressed', active ? 'true' : 'false')
    }

    const value = this.shadowRoot?.querySelector<HTMLElement>('.value')
    if (value) value.textContent = String(count)
  }

  private render(): void {
    const count = this.readCount()
    this.shadowRoot!.innerHTML = `
      <style>${styles}</style>
      <div class="scaler" role="group" aria-label="Vera window count">
        <span class="label">VERA WINDOWS</span>
        <span class="value">${count}</span>
        <div class="buttons">
          ${[3, 4, 5].map(value => `
            <button
              type="button"
              data-count="${value}"
              aria-label="Show ${value} Vera windows"
              aria-pressed="${value === count ? 'true' : 'false'}"
              ${value === count ? 'data-active' : ''}
            >${value}</button>
          `).join('')}
        </div>
      </div>
    `

    for (const button of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('button[data-count]')) {
      button.addEventListener('click', () => {
        const next = Number(button.dataset.count)
        if (!Number.isFinite(next)) return
        this.applyCount(next)
      })
    }
  }
}

if (!customElements.get('vertex-vera-window-scaler')) {
  customElements.define('vertex-vera-window-scaler', VeraWindowScaler)
}
