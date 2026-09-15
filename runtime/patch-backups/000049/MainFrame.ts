import type {
  PortalBootstrapState,
  SessionState,
  StorageStatus,
  SidebarTab,
  VirtualArdProjection,
  VraDispatchState,
  WorkstationSafetyAction,
  WorkstationSafetyObservation
} from '../../../../shared/contracts'
import { portalControl, type PortalControlCommand } from '../../control/control-channel'
import { escapeHtml } from '../../shared/escape'
import '../Explorer/Explorer'
import type { VertexExplorer } from '../Explorer/Explorer'
import '../VeraSession/VeraSession'
import '../VeraBrowserSession/VeraBrowserSession'
import '../VraDispatchLane/VraDispatchLane'
import styles from './MainFrame.css?inline'


const MAX_LOGICAL_LANES = 32
const MAIN_VERA_IDS = ['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05'] as const
const HIDDEN_VERA_WINDOWS_KEY = 'vertex.session-portal.hidden-vera-windows.v1'
const SAFETY_PENDING_KEY = 'vertex.workstation.safety.pending.v1'
const HEADER_WORDMARK_URL = new URL(
  '../../assets/vertex-session-portal-wordmark.svg',
  import.meta.url
).href
const WINDOW_FIT_SETTLE_MS = 90

type PendingSafetyAction = {
  schema: 'vertex-session-portal/safety-pending-1'
  action: WorkstationSafetyAction
  requestId: string
  reason: string
}

const FINAL_WIRING_B_HEADER_CSS = `
.commandSearch{display:flex;align-items:center;gap:6px;justify-self:end;width:32px;min-width:32px;max-width:360px;overflow:hidden;transition:width 140ms ease;padding:0 7px;cursor:pointer}
.commandSearch[data-expanded="true"]{width:min(360px,28vw);cursor:default}
.commandSearch .searchText,.commandSearch .searchHint{display:none}
.commandSearch[data-expanded="true"] .searchInput,.commandSearch[data-expanded="true"] .searchHint{display:block}
.searchInput{display:none;width:100%;min-width:0;border:0;outline:0;background:transparent;color:var(--vertex-text);font:inherit;font-size:11px}
.searchGlyphButton{display:grid;place-items:center;flex:0 0 20px;width:20px;height:20px;padding:0;border:0;background:transparent;color:var(--vertex-text-soft);cursor:pointer}
.workstationPulse{display:grid;grid-template-columns:auto auto;align-items:center;gap:5px 8px;padding:2px 7px;border:1px solid var(--vertex-line);border-radius:6px;background:rgba(4,12,27,.48);min-width:196px}
.workstationPulseText{grid-column:1;color:var(--vertex-text-muted);font-size:8px;letter-spacing:.07em;white-space:nowrap}
.workstationPulseText strong{color:var(--vertex-text-soft);font-weight:800}
.lanePulseGrid{grid-column:2;grid-row:1 / span 2;display:grid;grid-template-columns:repeat(8,7px);grid-template-rows:repeat(4,5px);gap:1px 2px;align-items:center}
.lanePulse{width:7px;height:5px;padding:0;border:0;border-radius:2px;background:rgba(113,129,149,.18);cursor:default}
.lanePulse[data-state="BUSY"]{background:var(--vertex-cyan-hot);box-shadow:0 0 5px rgba(58,184,255,.42);cursor:pointer}
.lanePulse[data-state="RESERVED"]{background:var(--vertex-warning);cursor:pointer}
.lanePulse[data-state="FAILED"]{background:var(--vertex-danger);cursor:pointer}
.lanePulse:focus-visible{outline:1px solid var(--vertex-cyan-hot);outline-offset:1px}
.workstationSafety{display:flex;align-items:center;gap:5px;padding:2px 5px;border:1px solid var(--vertex-line);border-radius:6px;background:rgba(4,12,27,.48);min-height:27px;white-space:nowrap}
.safetyState{display:flex;align-items:center;gap:4px;padding:0 5px;font-size:8px;font-weight:800;letter-spacing:.07em;color:var(--vertex-text-muted)}
.safetyState::before{content:'';width:6px;height:6px;border-radius:50%;background:var(--vertex-text-muted)}
.safetyState[data-state="RUNNING"]{color:var(--vertex-success)}.safetyState[data-state="RUNNING"]::before{background:var(--vertex-success)}
.safetyState[data-state="DRAINING"],.safetyState[data-state="RESET_READY"]{color:var(--vertex-warning)}.safetyState[data-state="DRAINING"]::before,.safetyState[data-state="RESET_READY"]::before{background:var(--vertex-warning)}
.safetyState[data-state="ESTOP_LATCHED"]{color:var(--vertex-danger);text-shadow:0 0 6px rgba(255,111,124,.38)}.safetyState[data-state="ESTOP_LATCHED"]::before{background:var(--vertex-danger);box-shadow:0 0 7px rgba(255,111,124,.68)}
.safetyActions{display:flex;align-items:center;gap:3px}.safetyAction{height:20px;padding:0 6px;border:1px solid var(--vertex-line);border-radius:4px;background:rgba(17,25,35,.72);color:var(--vertex-text-soft);font:inherit;font-size:7px;font-weight:800;letter-spacing:.04em;cursor:pointer}.safetyAction:hover:not(:disabled){border-color:var(--vertex-cyan-hot);color:var(--vertex-text)}.safetyAction:disabled{opacity:.38;cursor:default}.safetyAction.estop{border-color:rgba(255,111,124,.62);color:var(--vertex-danger);background:rgba(77,16,25,.34)}.safetyAction.estop:hover:not(:disabled){border-color:var(--vertex-danger);box-shadow:0 0 7px rgba(255,111,124,.24)}
.safetyNotice{max-width:130px;overflow:hidden;text-overflow:ellipsis;color:var(--vertex-text-muted);font-size:7px}
@media (max-width:1500px){.safetyNotice{display:none}.safetyAction{padding:0 4px}.workstationSafety{gap:2px}}
@media (max-width:1300px){.workstationPulse{min-width:150px}.workstationPulseText{font-size:7px}.lanePulseGrid{grid-template-columns:repeat(8,5px)}.lanePulse{width:5px}.telemetry{display:none}}
.addVeraButton{height:27px;padding:0 10px;border:1px solid rgba(58,184,255,.38);border-radius:6px;background:rgba(16,44,68,.62);color:var(--vertex-cyan-hot);font:inherit;font-size:8px;font-weight:900;letter-spacing:.09em;cursor:pointer;white-space:nowrap}
.addVeraButton:hover:not(:disabled){border-color:var(--vertex-cyan-hot);background:rgba(22,140,255,.13);box-shadow:0 0 10px rgba(22,140,255,.12)}
.addVeraButton:disabled{opacity:.34;cursor:default;box-shadow:none}
`


const PORTAL_FINAL_UX_CSS = `
/* 000073V5: header geometry is untouched; only the old tiny text brand is replaced. */
/* 000083V5: keep the fitted horizontal layout, but retire Chromium's overlay
   horizontal scrollbar.  Horizontal overflow mechanics remain available; only the
   scrollbar chrome is hidden so pointer crossing cannot trigger overlay flicker. */
:host{
  display:block;
  width:100%;
  max-width:100%;
  overflow-x:hidden;
}
.shell,
.main,
.sessionViewport{
  scrollbar-width:none;
  -ms-overflow-style:none;
}
.shell::-webkit-scrollbar,
.main::-webkit-scrollbar,
.sessionViewport::-webkit-scrollbar{
  width:0!important;
  height:0!important;
  display:none!important;
}
.sessionViewport::-webkit-scrollbar:horizontal{
  height:0!important;
  display:none!important;
}
.brand{
  display:flex;
  align-items:center;
  justify-content:flex-start;
  flex:0 0 158px;
  width:158px;
  min-width:158px;
  height:100%;
  padding:0 0 0 1px;
  overflow:visible;
}
.portalWordmark{
  display:block;
  width:154px;
  height:26px;
  max-height:calc(100% - 2px);
  object-fit:contain;
  object-position:left center;
  pointer-events:none;
  user-select:none;
  filter:drop-shadow(0 0 5px rgba(58,184,255,.06));
}
`

export class VertexMainFrame extends HTMLElement {
  private state: PortalBootstrapState = { sidebarTab: 'PROJECT', sessions: [], virtualArd: null }
  private unsubscribeControl?: () => void
  private storage: StorageStatus | null = null
  private vraState: VraDispatchState | null = null
  private safety: WorkstationSafetyObservation | null = null
  private safetyBusy = false
  private safetyNotice = ''
  private unsubscribeVra?: () => void
  private searchExpanded = false
  private windowFitTimer: number | null = null
  private readonly hiddenMainSessions = this.loadHiddenMainSessions()
  private readonly searchKeyListener = (event: KeyboardEvent): void => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      this.searchExpanded = true
      this.applySearchState(true)
    }
  }

  constructor() {
    super()
    this.attachShadow({ mode: 'open' })
  }

  connectedCallback(): void {
    this.shadowRoot!.addEventListener('vertex-session-priority', this.onSessionPriority)
    this.shadowRoot!.addEventListener('vertex-sidebar-tab', this.onSidebarTab)
    this.shadowRoot!.addEventListener('vertex-provider-settings-changed', this.onProviderSettingsChanged)
    this.shadowRoot!.addEventListener('vertex-lanes-changed', this.onLanesChanged)
    this.shadowRoot!.addEventListener('vertex-session-hide-request', this.onSessionHideRequest)
    this.unsubscribeControl = portalControl.subscribe(command => void this.handleControl(command))
    this.unsubscribeVra = window.vertexPortal.onVraDispatchChanged(() => void this.refreshVraState())
    window.addEventListener('keydown', this.searchKeyListener)
    this.render()
    void this.bootstrap()
  }

  disconnectedCallback(): void {
    this.shadowRoot!.removeEventListener('vertex-session-priority', this.onSessionPriority)
    this.shadowRoot!.removeEventListener('vertex-sidebar-tab', this.onSidebarTab)
    this.shadowRoot!.removeEventListener('vertex-provider-settings-changed', this.onProviderSettingsChanged)
    this.shadowRoot!.removeEventListener('vertex-lanes-changed', this.onLanesChanged)
    this.shadowRoot!.removeEventListener('vertex-session-hide-request', this.onSessionHideRequest)
    this.unsubscribeControl?.()
    this.unsubscribeVra?.()
    window.removeEventListener('keydown', this.searchKeyListener)
    if (this.windowFitTimer !== null) {
      window.clearTimeout(this.windowFitTimer)
      this.windowFitTimer = null
    }
  }

  private readonly onSessionPriority = (event: Event): void => {
    void this.setPriority((event as CustomEvent<string>).detail)
  }

  private readonly onSidebarTab = (event: Event): void => {
    void this.setSidebar((event as CustomEvent<SidebarTab>).detail)
  }

  private readonly onProviderSettingsChanged = (): void => {
    void this.refreshStatus()
  }

  private readonly onLanesChanged = (event: Event): void => {
    this.state = (event as CustomEvent<PortalBootstrapState>).detail
    this.render()
    this.scheduleMainWindowFit('VERA_LAYOUT')
  }

  private loadHiddenMainSessions(): Set<string> {
    try {
      const raw = window.localStorage.getItem(HIDDEN_VERA_WINDOWS_KEY)
      if (!raw) return new Set()
      const parsed = JSON.parse(raw) as unknown
      if (!Array.isArray(parsed)) return new Set()
      return new Set(parsed.filter((value): value is string =>
        typeof value === 'string' &&
        MAIN_VERA_IDS.includes(value as (typeof MAIN_VERA_IDS)[number])
      ))
    } catch {
      return new Set()
    }
  }

  private persistHiddenMainSessions(): void {
    try {
      const values = MAIN_VERA_IDS.filter(id => this.hiddenMainSessions.has(id))
      window.localStorage.setItem(HIDDEN_VERA_WINDOWS_KEY, JSON.stringify(values))
    } catch {
      // Presentation preference only. Canonical session state is not affected.
    }
  }

  private readonly onSessionHideRequest = (event: Event): void => {
    const sessionId = (event as CustomEvent<string>).detail
    if (!MAIN_VERA_IDS.includes(sessionId as (typeof MAIN_VERA_IDS)[number])) return

    const session = this.state.sessions.find(candidate =>
      candidate.id === sessionId &&
      candidate.kind === 'MAIN' &&
      candidate.active
    )
    if (!session) return

    this.hiddenMainSessions.add(sessionId)
    this.persistHiddenMainSessions()

    // Presentation-only close: keep the VeraBrowserSession mounted so its exact-origin
    // Evidence sink, immutable identity and browser state remain alive.
    const node = this.shadowRoot?.querySelector<HTMLElement>(
      `vera-browser-session[session-id="${sessionId}"]`
    )
    node?.setAttribute('presentation-hidden', '')
    this.syncVeraWindowControlsDom()
    this.scheduleMainWindowFit('VERA_LAYOUT')
  }

  private activeMainSessions(): SessionState[] {
    return this.state.sessions
      .filter(session =>
        session.kind === 'MAIN' &&
        session.active &&
        MAIN_VERA_IDS.includes(session.id as (typeof MAIN_VERA_IDS)[number])
      )
      .sort((a, b) => a.position - b.position)
  }

  private visibleMainSessions(): SessionState[] {
    return this.activeMainSessions()
      .filter(session => !this.hiddenMainSessions.has(session.id))
  }

  private canHideAnotherVera(): boolean {
    return this.visibleMainSessions().length > 3
  }

  private hideLastVisibleVera(): void {
    const visible = this.visibleMainSessions()
    if (visible.length <= 3) {
      this.syncVeraWindowControlsDom()
      return
    }

    // Presentation-only shrink: hide the right-most/highest-position visible Vera.
    // Keep the canonical session mounted so browser state, routing identity and
    // exact-origin Evidence delivery remain alive.
    const target = visible[visible.length - 1]
    this.hiddenMainSessions.add(target.id)
    this.persistHiddenMainSessions()

    const node = this.shadowRoot?.querySelector<HTMLElement>(
      `vera-browser-session[session-id="${target.id}"]`
    )
    node?.setAttribute('presentation-hidden', '')
    this.syncVeraWindowControlsDom()
    this.scheduleMainWindowFit('VERA_LAYOUT')
  }

  private canShowAnotherVera(): boolean {
    const active = this.activeMainSessions()
    return active.some(session => this.hiddenMainSessions.has(session.id)) ||
      active.length < MAIN_VERA_IDS.length
  }

  private async showNextVera(): Promise<void> {
    const active = this.activeMainSessions()

    // Re-open a presentation-hidden canonical session first.
    const hidden = active.find(session => this.hiddenMainSessions.has(session.id))
    if (hidden) {
      this.hiddenMainSessions.delete(hidden.id)
      this.persistHiddenMainSessions()
      const node = this.shadowRoot?.querySelector<HTMLElement>(
        `vera-browser-session[session-id="${hidden.id}"]`
      )
      node?.removeAttribute('presentation-hidden')
      this.syncVeraWindowControlsDom()
      this.scheduleMainWindowFit('VERA_LAYOUT')
      return
    }

    if (active.length >= MAIN_VERA_IDS.length) {
      this.syncVeraWindowControlsDom()
      return
    }

    // Existing Portal API activates the next canonical MAIN lane.
    // No new session ID is generated here.
    this.state = await window.vertexPortal.activateNextMainLane()

    const activated = this.activeMainSessions()
    for (const session of activated) {
      this.hiddenMainSessions.delete(session.id)
    }
    this.persistHiddenMainSessions()
    this.render()
    this.scheduleMainWindowFit('VERA_LAYOUT')
  }

  private syncVeraWindowControlsDom(): void {
    const visible = this.visibleMainSessions().length
    const add = this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="add-vera"]')
    if (add) {
      add.disabled = !this.canShowAnotherVera()
      add.title = add.disabled
        ? 'VERA01–VERA05 are already visible'
        : 'Show the next canonical Vera window'
    }

    const remove = this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="remove-vera"]')
    if (remove) {
      remove.disabled = !this.canHideAnotherVera()
      remove.title = remove.disabled
        ? 'Minimum 3 Vera windows are kept visible'
        : 'Hide the right-most Vera window without destroying its session'
    }

    const count = this.shadowRoot?.querySelector<HTMLElement>('[data-vera-visible-count]')
    if (count) count.textContent = `${visible}/5`
  }

  private scheduleMainWindowFit(reason: 'BOOTSTRAP' | 'VERA_LAYOUT'): void {
    if (this.windowFitTimer !== null) {
      window.clearTimeout(this.windowFitTimer)
    }

    this.windowFitTimer = window.setTimeout(() => {
      this.windowFitTimer = null
      void this.fitMainWindowToVisibleLayout(reason)
    }, WINDOW_FIT_SETTLE_MS)
  }

  private async fitMainWindowToVisibleLayout(
    reason: 'BOOTSTRAP' | 'VERA_LAYOUT'
  ): Promise<void> {
    const shell = this.shadowRoot?.querySelector<HTMLElement>('.shell')
    const main = this.shadowRoot?.querySelector<HTMLElement>('.main')
    const explorer = this.shadowRoot?.querySelector<HTMLElement>('vertex-explorer')
    const viewport = this.shadowRoot?.querySelector<HTMLElement>('.sessionViewport')
    const track = this.shadowRoot?.querySelector<HTMLElement>('.sessionTrack')
    const topbar = this.shadowRoot?.querySelector<HTMLElement>('.topbar')
    const statusbar = this.shadowRoot?.querySelector<HTMLElement>('.statusbar')

    if (!shell || !main || !viewport || !track) return

    const mainStyle = window.getComputedStyle(main)
    const gap = Number.parseFloat(mainStyle.columnGap || mainStyle.gap || '0') || 0
    const paddingLeft = Number.parseFloat(mainStyle.paddingLeft || '0') || 0
    const paddingRight = Number.parseFloat(mainStyle.paddingRight || '0') || 0
    const explorerWidth = explorer?.getBoundingClientRect().width ?? 0

    // presentation-hidden Vera sessions are display:none, so scrollWidth represents
    // exactly the visible session matrix + Dispatch Bay natural horizontal footprint.
    const naturalMainWidth = Math.ceil(
      paddingLeft +
      explorerWidth +
      (explorerWidth > 0 ? gap : 0) +
      track.scrollWidth +
      paddingRight
    )

    const chromeWidth = Math.ceil(Math.max(
      topbar?.scrollWidth ?? 0,
      statusbar?.scrollWidth ?? 0
    ))

    const desiredContentWidth = Math.max(naturalMainWidth, chromeWidth, 1)

    // Vera windows share one vertical lane. Preserve the user's current vertical
    // working height; this avoids a resize feedback loop while horizontal lane count
    // grows/shrinks with +VERA / -VERA.
    const desiredContentHeight = Math.max(
      Math.ceil(shell.getBoundingClientRect().height),
      Math.ceil(window.innerHeight),
      1
    )

    try {
      await window.vertexPortal.fitMainWindow({
        contentWidth: desiredContentWidth,
        contentHeight: desiredContentHeight,
        reason
      })
    } catch {
      // UX-only fit must never disturb session/routing/runtime authority.
    }
  }

  private async bootstrap(): Promise<void> {
    this.state = await window.vertexPortal.bootstrap()
    await this.refreshStatus(false)
    await this.refreshVraState(false)
    await this.refreshSafety(false)
    this.render()
    this.scheduleMainWindowFit('BOOTSTRAP')
  }


private async refreshStatus(renderAfter = true): Promise<void> {
  try {
    this.storage = await window.vertexPortal.storageStatus()
  } catch {
    this.storage = null
  }

  if (renderAfter) this.render()
}

  private async refreshVraState(updateAfter = true): Promise<void> {
    try {
      this.vraState = await window.vertexPortal.getVraDispatchState()
      if (this.vraState.workstationSafety) {
        this.safety = this.vraState.workstationSafety
        this.reconcilePendingSafety(this.safety)
      }
    } catch {
      this.vraState = null
    }
    if (updateAfter) {
      this.updateWorkstationPulseDom()
      this.updateSafetyDom()
    }
  }

  private allocatedLaneNumber(value: unknown): number | null {
    if (typeof value !== 'string') return null
    const match = /^(?:lane[-_ ]?)?(\d{1,2})$/i.exec(value.trim())
    if (!match) return null
    const lane = Number(match[1])
    return Number.isInteger(lane) && lane >= 1 && lane <= MAX_LOGICAL_LANES ? lane : null
  }

  private workstationPulse(): { online: boolean; active: number; queue: number; lanes: Map<number, string> } {
    const cards = (this.vraState?.cards ?? []) as unknown as Array<Record<string, unknown>>
    const lanes = new Map<number, string>()
    let queue = 0
    for (const card of cards) {
      const lane = this.allocatedLaneNumber(card.allocatedLane)
      const jobState = typeof card.workstationJobState === 'string' ? card.workstationJobState : ''
      const registration = typeof card.workstationRegistration === 'string' ? card.workstationRegistration : ''
      if (!lane && ['PENDING','REGISTERING','REGISTERED'].includes(registration) && !['SUCCEEDED','FAILED','REJECTED','ROLLED_BACK'].includes(jobState)) queue += 1
      if (!lane) continue
      let normalized = 'FREE'
      if (jobState === 'EXECUTING') normalized = 'BUSY'
      else if (jobState === 'DISPATCHED' || jobState === 'REGISTERED') normalized = 'RESERVED'
      else if (jobState === 'FAILED' || jobState === 'REJECTED') normalized = 'FAILED'
      if (normalized !== 'FREE') lanes.set(lane, normalized)
    }
    const active = [...lanes.values()].filter(state => state === 'BUSY' || state === 'RESERVED').length
    return { online: this.vraState?.workstationOnline === true, active, queue, lanes }
  }

  private renderWorkstationPulse(): string {
    const pulse = this.workstationPulse()
    const status = pulse.online ? `${String(pulse.active).padStart(2, '0')}/${MAX_LOGICAL_LANES} ACTIVE` : `OFFLINE / --/${MAX_LOGICAL_LANES}`
    const laneButtons = Array.from({ length: MAX_LOGICAL_LANES }, (_, index) => {
      const lane = index + 1
      const state = pulse.online ? (pulse.lanes.get(lane) ?? 'FREE') : 'FREE'
      const allocated = pulse.lanes.has(lane)
      return `<button type="button" class="lanePulse" data-state="${state}" ${allocated ? `data-lane-focus="${lane}"` : ''} title="LANE ${String(lane).padStart(2,'0')} · ${state}" aria-label="Lane ${lane} ${state}"></button>`
    }).join('')
    return `<div class="workstationPulse" title="Workstation loopback pulse · 32 logical lanes"><span class="workstationPulseText"><strong>WORKSTATION</strong> ${status}</span><span class="workstationPulseText">QUEUE ${String(pulse.queue).padStart(2,'0')}</span><span class="lanePulseGrid">${laneButtons}</span></div>`
  }

  private async refreshSafety(updateAfter = true): Promise<void> {
    try {
      this.safety = await window.vertexPortal.getWorkstationSafety()
      this.reconcilePendingSafety(this.safety)
    } catch (error) {
      this.safety = {
        schema: null,
        online: false,
        state: 'UNKNOWN',
        generation: null,
        latched: null,
        newWorkAllowed: null,
        activeContinuationAllowed: null,
        autoReset: null,
        autoResume: null,
        lastTransition: null,
        metrics: null,
        executionPlane: 'UNKNOWN',
        observationPlane: 'UNKNOWN',
        evidenceReturnPlane: 'UNKNOWN',
        observedUtc: new Date().toISOString(),
        lastError: error instanceof Error ? error.message : String(error)
      }
    }
    if (updateAfter) this.updateSafetyDom()
  }

  private safetyDisplayLabel(): string {
    if (!this.safety?.online) return 'UNKNOWN / OFFLINE'
    switch (this.safety.state) {
      case 'RUNNING': return 'RUNNING'
      case 'DRAINING': return 'DRAINING'
      case 'ESTOP_LATCHED': return 'E-STOP'
      case 'RESET_READY': return 'RESET READY'
      default: return 'UNKNOWN'
    }
  }

  private safetyActionAvailable(action: WorkstationSafetyAction): boolean {
    if (!this.safety?.online || this.safetyBusy) return false
    switch (this.safety.state) {
      case 'RUNNING': return action === 'DRAIN' || action === 'ESTOP'
      case 'DRAINING': return action === 'RESUME' || action === 'ESTOP'
      case 'ESTOP_LATCHED': return action === 'RESET'
      case 'RESET_READY': return action === 'RESUME'
      default: return false
    }
  }

  private renderSafetyControl(): string {
    const state = this.safety?.state ?? 'UNKNOWN'
    const display = this.safetyDisplayLabel()
    const metrics = this.safety?.metrics
    const detail = this.safety?.online
      ? `${metrics ? `A${metrics.activeJobs} Q${metrics.queuedJobs}` : ''}${this.safety?.generation !== null && this.safety?.generation !== undefined ? ` · G${this.safety.generation}` : ''}`
      : 'NO AUTHORITY STATE'
    const button = (action: WorkstationSafetyAction, label: string, danger = false): string =>
      `<button type="button" class="safetyAction${danger ? ' estop' : ''}" data-safety-action="${action}" ${this.safetyActionAvailable(action) ? '' : 'disabled'}>${label}</button>`
    const actions: string[] = []
    if (state === 'RUNNING') actions.push(button('DRAIN', 'DRAIN'), button('ESTOP', 'EMERGENCY STOP', true))
    else if (state === 'DRAINING') actions.push(button('RESUME', 'RESUME'), button('ESTOP', 'EMERGENCY STOP', true))
    else if (state === 'ESTOP_LATCHED') actions.push(button('RESET', 'RESET'))
    else if (state === 'RESET_READY') actions.push(button('RESUME', 'RESUME'))
    return `<div class="workstationSafety" title="Workstation Safety Authority · ${escapeHtml(this.safety?.state ?? 'UNKNOWN')}"><span class="safetyState" data-state="${escapeHtml(state)}">${escapeHtml(display)}</span><span class="safetyNotice">${escapeHtml(this.safetyNotice || detail)}</span><span class="safetyActions">${actions.join('')}</span></div>`
  }

  private safetyConfirmation(action: WorkstationSafetyAction): string {
    switch (action) {
      case 'DRAIN': return 'DRAIN Workstation? New work will stop while admitted active work is allowed to finish safely.'
      case 'ESTOP': return 'EMERGENCY STOP Workstation? This latches E-STOP and blocks new/next execution phases until Human RESET then Human RESUME.'
      case 'RESET': return 'RESET E-STOP recovery state? This does NOT resume jobs. Workstation must pass recovery inspection before RESET_READY.'
      case 'RESUME': return 'RESUME Workstation? This is an explicit Human safety action and may allow normal scheduling again if Workstation recovery checks pass.'
    }
  }

  private safetyReason(action: WorkstationSafetyAction): string {
    const name = action === 'ESTOP' ? 'EMERGENCY STOP' : action
    return `Session Portal Human requested ${name}.`
  }

  private readPendingSafety(): PendingSafetyAction | null {
    try {
      const raw = window.localStorage.getItem(SAFETY_PENDING_KEY)
      if (!raw) return null
      const value = JSON.parse(raw) as PendingSafetyAction
      if (value?.schema !== 'vertex-session-portal/safety-pending-1') return null
      if (!['DRAIN','ESTOP','RESET','RESUME'].includes(value.action)) return null
      if (!value.requestId || !value.reason) return null
      return value
    } catch { return null }
  }

  private pendingSafety(action: WorkstationSafetyAction): PendingSafetyAction {
    const existing = this.readPendingSafety()
    if (existing?.action === action) return existing
    const next: PendingSafetyAction = {
      schema: 'vertex-session-portal/safety-pending-1',
      action,
      requestId: `portal-safety-${action.toLowerCase()}-${crypto.randomUUID()}`,
      reason: this.safetyReason(action)
    }
    window.localStorage.setItem(SAFETY_PENDING_KEY, JSON.stringify(next))
    return next
  }

  private clearPendingSafety(): void {
    window.localStorage.removeItem(SAFETY_PENDING_KEY)
  }

  private expectedSafetyState(action: WorkstationSafetyAction): string {
    switch (action) {
      case 'DRAIN': return 'DRAINING'
      case 'ESTOP': return 'ESTOP_LATCHED'
      case 'RESET': return 'RESET_READY'
      case 'RESUME': return 'RUNNING'
    }
  }

  private reconcilePendingSafety(observation: WorkstationSafetyObservation): void {
    const pending = this.readPendingSafety()
    if (!pending || !observation.online) return
    const transition = observation.lastTransition
    if (transition?.requestId === pending.requestId && transition.action === pending.action && observation.state === this.expectedSafetyState(pending.action)) {
      this.clearPendingSafety()
      this.safetyNotice = `${this.safetyDisplayLabel()} · CONFIRMED`
    }
  }

  private async performSafetyAction(action: WorkstationSafetyAction): Promise<void> {
    if (!this.safetyActionAvailable(action)) return
    if (!window.confirm(this.safetyConfirmation(action))) return

    const pending = this.pendingSafety(action)
    this.safetyBusy = true
    this.safetyNotice = `${action} · REQUESTING`
    this.updateSafetyDom()
    try {
      const result = await window.vertexPortal.performWorkstationSafetyAction({
        action,
        requestId: pending.requestId,
        reason: pending.reason
      })
      this.safety = result.observation
      this.clearPendingSafety()
      this.safetyNotice = `${this.safetyDisplayLabel()} · ${result.idempotent ? 'IDEMPOTENT' : 'CONFIRMED'}`
    } catch (error) {
      // Response loss is recovered by GET only. No automatic POST retry and no optimistic state.
      this.safetyNotice = `SAFETY RECHECK · ${error instanceof Error ? error.message : String(error)}`
      await this.refreshSafety(false)
      this.reconcilePendingSafety(this.safety!)
    } finally {
      this.safetyBusy = false
      this.updateSafetyDom()
    }
  }

  private bindSafetyControls(): void {
    this.shadowRoot?.querySelectorAll<HTMLButtonElement>('[data-safety-action]').forEach(button => {
      button.addEventListener('click', () => {
        const action = button.dataset.safetyAction
        if (action === 'DRAIN' || action === 'ESTOP' || action === 'RESET' || action === 'RESUME') {
          void this.performSafetyAction(action)
        }
      })
    })
  }

  private updateSafetyDom(): void {
    const current = this.shadowRoot?.querySelector<HTMLElement>('.workstationSafety')
    if (!current) return
    const host = document.createElement('div')
    host.innerHTML = this.renderSafetyControl()
    const next = host.firstElementChild
    if (!next) return
    current.replaceWith(next)
    this.bindSafetyControls()
  }

  private applySearchState(focus = false): void {
    const search = this.shadowRoot?.querySelector<HTMLElement>('.commandSearch')
    if (!search) return
    search.dataset.expanded = this.searchExpanded ? 'true' : 'false'
    const input = search.querySelector<HTMLInputElement>('.searchInput')
    if (focus && this.searchExpanded) window.setTimeout(() => input?.focus(), 0)
  }

  private bindLanePulseButtons(): void {
    this.shadowRoot?.querySelectorAll<HTMLButtonElement>('[data-lane-focus]').forEach(button => {
      button.addEventListener('click', () => {
        const lane = button.dataset.laneFocus
        if (!lane) return
        const matching = ((this.vraState?.cards ?? []) as unknown as Array<Record<string, unknown>>).find(card => this.allocatedLaneNumber(card.allocatedLane) === Number(lane))
        const token = matching && typeof matching.allocatedLane === 'string' ? matching.allocatedLane : `lane-${String(lane).padStart(2,'0')}`
        window.dispatchEvent(new CustomEvent<string>('vertex-vra-focus-lane', { detail: token }))
      })
    })
  }

  private updateWorkstationPulseDom(): void {
    const current = this.shadowRoot?.querySelector<HTMLElement>('.workstationPulse')
    if (!current) return
    const host = document.createElement('div')
    host.innerHTML = this.renderWorkstationPulse()
    const next = host.firstElementChild
    if (!next) return
    current.replaceWith(next)
    this.bindLanePulseButtons()
  }

  private bindHeaderControls(): void {
    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="remove-vera"]')?.addEventListener('click', () => {
      this.hideLastVisibleVera()
    })
    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="add-vera"]')?.addEventListener('click', () => {
      void this.showNextVera()
    })
    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="search-toggle"]')?.addEventListener('click', () => {
      this.searchExpanded = !this.searchExpanded
      this.applySearchState(this.searchExpanded)
    })
    this.shadowRoot?.querySelector<HTMLInputElement>('.searchInput')?.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); this.searchExpanded = false; this.applySearchState(false) }
    })
    this.bindLanePulseButtons()
    this.bindSafetyControls()
  }

  private async setPriority(sessionId: string): Promise<void> {
    this.state = await window.vertexPortal.setPrioritySession(sessionId)
    this.render()
  }

  private async setSidebar(tab: SidebarTab): Promise<void> {
    this.state.sidebarTab = tab
    await window.vertexPortal.setSidebarTab(tab)
    this.shadowRoot?.querySelector<VertexExplorer>('vertex-explorer')?.setTab(tab)
  }

  private async handleControl(command: PortalControlCommand): Promise<void> {
    const explorer = this.shadowRoot?.querySelector<VertexExplorer>('vertex-explorer')
    switch (command.type) {
      case 'SIDEBAR_SWITCH':
        await this.setSidebar(command.tab)
        break
      case 'SESSION_FOCUS':
      case 'SESSION_EXPAND':
        await this.setPriority(command.sessionId)
        break
      case 'VCR_OPEN':
        this.state.sidebarTab = 'VCR'
        await window.vertexPortal.setSidebarTab('VCR')
        explorer?.showVcrEntry(command.key)
        break
      case 'VCA_SEARCH':
        this.state.sidebarTab = 'VCA'
        await window.vertexPortal.setSidebarTab('VCA')
        explorer?.showVcaSearch(command.query)
        break
      case 'PROJECT_REVEAL':
        this.state.sidebarTab = 'PROJECT'
        await window.vertexPortal.setSidebarTab('PROJECT')
        explorer?.revealProject(command.path)
        break
    }
  }

  private projectionFor(sessionId: string): VirtualArdProjection | undefined {
    return this.state.virtualArd?.projections.find(projection => projection.sessionId === sessionId)
  }

  private renderSession(session: SessionState): string {
    if (!session.active) return ''
    const priority = session.priority ? 'priority' : ''
    const presentationHidden = this.hiddenMainSessions.has(session.id) ? 'presentation-hidden' : ''
    const id = escapeHtml(session.id)

    if (session.kind !== 'MAIN') return ''

    const projection = this.projectionFor(session.id)
    const role = projection ? `session-role="${escapeHtml(projection.role)}"` : ''
    const objective = this.state.virtualArd
      ? `mission-objective="${escapeHtml(this.state.virtualArd.mission.objective)}"`
      : ''

    return `
      <vera-browser-session
        session-id="${id}"
        session-title="${escapeHtml(session.title)}"
        ${role}
        ${objective}
        ${priority}
        ${presentationHidden}
      ></vera-browser-session>
    `
  }

  private render(): void {
    const active = this.activeMainSessions()
    const visible = this.visibleMainSessions()
    const priority = visible.find(session => session.priority)
    const ardLabel = this.state.virtualArd ? 'ARD · ACTIVE' : 'ARD · READY'
    const activeVeraCount = visible.length
    const canHideAnotherVera = this.canHideAnotherVera()
    const canShowAnotherVera = this.canShowAnotherVera()

    this.shadowRoot!.innerHTML = `
      <style>${styles}${FINAL_WIRING_B_HEADER_CSS}${PORTAL_FINAL_UX_CSS}</style>
      <div class="shell">
        <header class="topbar">
          <div class="brand" aria-label="VERTEX SESSION PORTAL">
            <img
              class="portalWordmark"
              src="${HEADER_WORDMARK_URL}"
              alt="VERTEX SESSION PORTAL"
              draggable="false"
            >
          </div>
          <div class="commandSearch" data-expanded="${this.searchExpanded ? 'true' : 'false'}">
            <button type="button" class="searchGlyphButton" data-action="search-toggle" title="Search · Ctrl+K">⌕</button>
            <input class="searchInput" type="search" placeholder="Search sessions, project, VCR / VCA…" aria-label="Portal search">
            <span class="searchHint">CTRL K</span>
          </div>
          <div class="system">
            <button type="button" class="addVeraButton" data-action="remove-vera" ${canHideAnotherVera ? '' : 'disabled'} title="${canHideAnotherVera ? 'Hide the right-most Vera window without destroying its session' : 'Minimum 3 Vera windows are kept visible'}">− VERA</button>
            <button type="button" class="addVeraButton" data-action="add-vera" ${canShowAnotherVera ? '' : 'disabled'} title="${canShowAnotherVera ? 'Show the next canonical Vera window' : 'VERA01–VERA05 are already visible'}">+ VERA</button>
            ${this.renderWorkstationPulse()}
            ${this.renderSafetyControl()}
            <span class="telemetry">CPU <strong>—</strong></span>
            <span class="telemetry">RAM <strong>—</strong></span>
            <span class="telemetry">NET <strong>LOCAL</strong></span>
            <span>${ardLabel}</span>
            <span class="avatar">V</span>
          </div>
        </header>

        <main class="main">
          <vertex-explorer></vertex-explorer>
          <section class="sessionViewport">
            <div class="sessionTrack">
              ${active.map(session => this.renderSession(session)).join('')}
              <vertex-vra-dispatch-lane></vertex-vra-dispatch-lane>
            </div>
          </section>
        </main>

        <footer class="statusbar">
          <span>VERA SESSION MATRIX · <strong data-vera-visible-count>${activeVeraCount}/5</strong></span>
          <span class="statusCenter">
            ${priority ? `PRIORITY · ${escapeHtml(priority.title)}` : 'TILED SESSION MODE'}
          </span>
          <span class="statusRight">
            CHATGPT BROWSER · PERSISTENT ACCOUNT SESSION · SQLITE ${this.storage?.sqliteConnected ? 'READY' : '—'} · VCR ${this.storage?.vcrReady ? this.storage.vcrCount : '—'} · VCA ${this.storage?.vcaReady ? this.storage.vcaCount : '—'}
          </span>
        </footer>
      </div>
    `

    this.shadowRoot!.querySelector<VertexExplorer>('vertex-explorer')?.setTab(this.state.sidebarTab)
    this.bindHeaderControls()
  }
}

customElements.define('vertex-main-frame', VertexMainFrame)
