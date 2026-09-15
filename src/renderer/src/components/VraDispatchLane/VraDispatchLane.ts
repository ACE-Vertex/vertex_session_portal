import type { VraDispatchCard, VraDispatchState, WorkstationServerProcessState } from '../../../../shared/contracts'
import { escapeHtml } from '../../shared/escape'
import styles from './VraDispatchLane.css?inline'
import {
  VERA_EVIDENCE_RETURN_EVENT,
  VERA_EVIDENCE_RETURN_RESULT_EVENT,
  type VeraEvidenceReturnMessage,
  type VeraEvidenceReturnResult
} from '../VeraBrowserSession/VeraEvidenceReturnInjector'

type VraOriginVera = 'VERA01' | 'VERA02' | 'VERA03' | 'VERA04' | 'VERA05' | 'UNKNOWN'
type VraHumanApproval = 'PENDING' | 'APPROVED'
type WorkstationDispatchCard = VraDispatchCard & {
  originVera?: VraOriginVera
  originSession?: string | null
  originWindow?: string | null
  projectName?: string | null
  artifactId?: string | null
  jobTitle?: string | null
  requestedLane?: string | null
  lanePolicy?: 'ANY' | 'PREFER' | null
  jobId?: string | null
  projectId?: string | null
  returnChannel?: string | null
  parallelism?: number | null
  workerConcurrency?: number | null
  correlationId?: string | null
  allocatedLane?: string | null
  humanApproval?: VraHumanApproval
  workstationRegistration?: 'NOT_READY' | 'PENDING' | 'REGISTERING' | 'REGISTERED' | 'BLOCKED'
  workstationJobState?: 'REGISTERED' | 'DISPATCHED' | 'EXECUTING' | 'SUCCEEDED' | 'FAILED' | 'REJECTED' | 'ROLLED_BACK' | null
  workstationEvidenceState?: string | null
  workstationEvidenceReturnState?: string | null
  workstationLastError?: string | null
  evidenceIdentity?: string | null
  evidenceDeliveryPayload?: string | null
  cardKind?: 'TEST' | null
  rerunOfJobId?: string | null
  testRunId?: string | null
}

type EvidenceDeliveryReceipt = {
  schema: 'vertex-session-portal/evidence-delivery-receipt-1'
  state: 'IN_FLIGHT' | 'DELIVERED'
  deliveryId: string
  jobId: string
  originVera: string
  originSession: string
  originWindow: string
  correlationId: string
  returnChannel: string
  deliveredAt: string
}

type ArdAutoAuthorityLease = {
  schema: 'vertex-session-portal/auto-authority-1'
  authority_id: string
  controller_session: string
  allowed_sessions: string[]
  granted_utc: string
  expires_utc: string
  status: 'ACTIVE' | 'REVOKED'
}

type ArdAutoTaskContext = {
  schema: 'vertex-session-portal/ard-task-context-1'
  authority_id: string
  parent_dispatch_id: string
  controller_session: string
  delegated_session: string
  activated_utc: string
}

const EVIDENCE_RECEIPTS_KEY = 'vertex.final-wiring-b.evidence-delivery-receipts.v1'
const AUTO_AUTHORITY_KEY = 'vertex.portal.ard-auto-authority.v1'
const AUTO_TASK_CONTEXT_KEY = 'vertex.portal.ard-auto-task-context.v1'
const AUTO_AUTHORITY_CHANGED_EVENT = 'vertex-ard-auto-authority-changed'
const AUTO_DISPATCH_COMMAND_PREFIX = 'vertex-auto-dispatch:'

// WORKSTATION_DISPATCH_CARD_000052V1H2:
// Renderer only displays Capture-owned immutable provenance. It never infers origin
// from active window state or browser contents.
export class VraDispatchLane extends HTMLElement {
  private state: VraDispatchState | null = null
  private busyCardId = ''
  private busyAction: 'export' | 'dispatch' | 'rerun-test' | '' = ''
  private pendingRemoveCardIds: string[] = []
  private readonly selectedCardIds = new Set<string>()
  private selectionAnchorId = ''
  private removingCards = false
  private workstationProcess: WorkstationServerProcessState | null = null
  private workstationStarting = false
  private workstationStartPoll: ReturnType<typeof setInterval> | null = null
  private refreshInFlight: Promise<void> | null = null
  private notice = ''
  private unsubscribeChanged?: () => void
  private readonly evidenceInFlight = new Set<string>()
  private readonly evidenceCardResolveAttempts = new Map<string, number>()
  private readonly evidenceAckInFlight = new Set<string>()
  private readonly autoDispatchInFlight = new Set<string>()
  private autoDispatchCycleInFlight: Promise<void> | null = null
  private readonly autoAuthorityChangedListener = (): void => {
    void this.routeAutoAuthorizedCards()
  }
  private readonly laneFocusListener = (event: Event): void => {
    const lane = (event as CustomEvent<string>).detail
    if (!lane) return
    const card = this.shadowRoot?.querySelector<HTMLElement>(`[data-allocated-lane="${CSS.escape(lane)}"]`)
    if (!card) return
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
    card.setAttribute('data-focus-pulse', '')
    window.setTimeout(() => card.removeAttribute('data-focus-pulse'), 1400)
  }
  private readonly evidenceResultListener = (event: Event): void => {
    const result = (event as CustomEvent<VeraEvidenceReturnResult>).detail
    if (!result || !this.evidenceInFlight.has(result.deliveryId)) return
    const card = ((this.state?.cards ?? []) as WorkstationDispatchCard[])
      .find(candidate => candidate.evidenceIdentity === result.deliveryId && candidate.jobId === result.jobId)
    if (!card) {
      const resolveAttempt = this.evidenceCardResolveAttempts.get(result.deliveryId) ?? 0
      if (resolveAttempt >= 8) return

      this.evidenceCardResolveAttempts.set(result.deliveryId, resolveAttempt + 1)
      window.setTimeout(() => {
        this.evidenceResultListener(event)
      }, Math.min(1000, 250 * (resolveAttempt + 1)))
      return
    }

    this.evidenceCardResolveAttempts.delete(result.deliveryId)
    const returnedAt = new Date().toISOString()
    const acknowledge = (attempt: number): void => {
      void window.vertexPortal.acknowledgeVraEvidenceDelivery({
        cardId: card.id,
        evidenceId: result.deliveryId,
        artifactId: card.artifactId || card.filename || card.id,
        returnedAt
      }).then(ack => {
        if (
          ack.acknowledged ||
          ack.idempotent ||
          ack.evidenceReturnState === 'RETURNED'
        ) {
          this.evidenceInFlight.delete(result.deliveryId)
          return
        }

        if (attempt < 3) {
          window.setTimeout(() => acknowledge(attempt + 1), 500 * attempt)
        }
      }).catch(() => {
        if (attempt < 3) {
          window.setTimeout(() => acknowledge(attempt + 1), 500 * attempt)
        }
      })
    }

    acknowledge(1)
    if (!result.ok || result.originSession !== card.originSession) {
      if (['session-not-ready', 'composer-not-found', 'send-button-not-ready', 'origin-mismatch-fail-closed'].includes(result.stage)) {
        this.clearDeliveryAttempt(card)
        this.notice = `EVIDENCE DELIVERY RETRY · ${result.stage}`
      } else {
        this.notice = `EVIDENCE DELIVERY UNCERTAIN · ${result.stage}`
      }
      this.render()
      return
    }
    if (!this.exactOriginRoute(card)) {
      this.notice = 'EVIDENCE ROUTE FAIL-CLOSED'
      this.render()
      return
    }
    this.writeDeliveryReceipt(card)
    this.notice = 'EVIDENCE DELIVERED · ACK PENDING'
    this.render()
    void this.ackDeliveredEvidence(card)
  }

  constructor() {
    super()
    this.attachShadow({ mode: 'open' })
  }

  connectedCallback(): void {
    // VERTEX_CARD_ERROR_COPY_000033V2: one delegated listener; card dimensions remain untouched.
    if (!this.errorCopyListenerInstalled) {
      this.addEventListener('click', this.handleErrorCopyClick)
      this.errorCopyListenerInstalled = true
    }

    this.render()
    window.addEventListener(VERA_EVIDENCE_RETURN_RESULT_EVENT, this.evidenceResultListener)
    window.addEventListener('vertex-vra-focus-lane', this.laneFocusListener)
    window.addEventListener(AUTO_AUTHORITY_CHANGED_EVENT, this.autoAuthorityChangedListener)
    this.unsubscribeChanged = window.vertexPortal.onVraDispatchChanged(() => {
      void this.refresh()
    })

    // 000079V5: one poll owner only.
    // VraDispatchService owns Workstation reconciliation and emits only on
    // material state changes. The renderer must not run a second 2.5s poll.

    void this.refresh()
  }

  disconnectedCallback(): void {
    window.removeEventListener(VERA_EVIDENCE_RETURN_RESULT_EVENT, this.evidenceResultListener)
    window.removeEventListener('vertex-vra-focus-lane', this.laneFocusListener)
    window.removeEventListener(AUTO_AUTHORITY_CHANGED_EVENT, this.autoAuthorityChangedListener)
    this.unsubscribeChanged?.()
    this.unsubscribeChanged = undefined
    if (this.workstationStartPoll) {
      clearInterval(this.workstationStartPoll)
      this.workstationStartPoll = null
    }
  }

  private refresh(): Promise<void> {
    if (this.refreshInFlight) return this.refreshInFlight
    this.refreshInFlight = this.refreshOnce().finally(() => {
      this.refreshInFlight = null
    })
    return this.refreshInFlight
  }

  private async refreshOnce(): Promise<void> {
    try {
      const [state, processState] = await Promise.all([
        window.vertexPortal.getVraDispatchState(),
        window.vertexPortal.getWorkstationServerProcessState()
      ])
      this.state = state
      this.workstationProcess = processState
    } catch {
      try {
        this.state = await window.vertexPortal.getVraDispatchState()
      } catch {
        this.state = null
      }
    }
    this.render()
    void this.routeAutoAuthorizedCards()
    this.routePendingEvidence()
    this.retryPendingAcks()
  }

  private workstationOnline(): boolean {
    // Direct process controller state is authoritative when available.
    // Do not let the older DispatchService health bit make a legacy server look compatible.
    if (this.workstationProcess) {
      return this.workstationProcess.online === true && this.workstationProcess.compatible === true
    }
    return this.state?.workstationOnline === true
  }

  private workstationRuntimeMismatch(): boolean {
    return Boolean(
      this.workstationProcess?.serverReachable === true &&
      this.workstationProcess?.compatible !== true
    )
  }

  private workstationGenerationLabel(): string {
    return this.workstationProcess?.runtimeGeneration ?? 'LEGACY'
  }

  private workstationRootMigrationNeeded(): boolean {
    return Boolean(
      this.workstationOnline() &&
      this.workstationProcess?.rootReleaseReady !== true
    )
  }

  private async startWorkstationServer(): Promise<void> {
    if (this.workstationStarting) return
    if (this.workstationOnline() && !this.workstationRootMigrationNeeded()) return

    this.workstationStarting = true
    this.notice = ''
    this.patchWorkstationServerControl()

    try {
      this.workstationProcess = await window.vertexPortal.startWorkstationServer()

      if (this.workstationProcess.online) {
        this.workstationStarting = false
        this.notice = ''
        await this.refresh()
        return
      }

      if (this.workstationProcess.phase === 'INCOMPATIBLE') {
        this.workstationStarting = false
        this.notice = `WORKSTATION RUNTIME MISMATCH · ${this.workstationProcess.lastError ?? 'RESTART REQUIRED'}`
        this.render()
        return
      }

      if (this.workstationProcess.phase === 'ERROR') {
        this.workstationStarting = false
        this.notice = `WORKSTATION START FAILED · ${this.workstationProcess.lastError ?? 'UNKNOWN'}`
        this.render()
        return
      }

      this.beginWorkstationStartPoll()
    } catch (error) {
      this.workstationStarting = false
      this.notice = `WORKSTATION START FAILED · ${error instanceof Error ? error.message : String(error)}`
      this.render()
    }
  }

  private beginWorkstationStartPoll(): void {
    if (this.workstationStartPoll) clearInterval(this.workstationStartPoll)

    let attempts = 0
    this.workstationStartPoll = setInterval(() => {
      attempts += 1
      void this.refreshWorkstationStartState(attempts)
    }, 500)
  }

  private async refreshWorkstationStartState(attempt: number): Promise<void> {
    try {
      const processState = await window.vertexPortal.getWorkstationServerProcessState()
      this.workstationProcess = processState

      if (processState.online) {
        this.workstationStarting = false
        if (this.workstationStartPoll) clearInterval(this.workstationStartPoll)
        this.workstationStartPoll = null
        await this.refresh()
        return
      }

      if (processState.phase === 'INCOMPATIBLE') {
        this.workstationStarting = false
        if (this.workstationStartPoll) clearInterval(this.workstationStartPoll)
        this.workstationStartPoll = null
        this.notice = `WORKSTATION RUNTIME MISMATCH · ${processState.lastError ?? 'RESTART REQUIRED'}`
        this.render()
        return
      }

      if (processState.phase === 'ERROR') {
        this.workstationStarting = false
        if (this.workstationStartPoll) clearInterval(this.workstationStartPoll)
        this.workstationStartPoll = null
        this.notice = `WORKSTATION START FAILED · ${processState.lastError ?? 'UNKNOWN'}`
        this.render()
        return
      }

      if (attempt >= 40) {
        this.workstationStarting = false
        if (this.workstationStartPoll) clearInterval(this.workstationStartPoll)
        this.workstationStartPoll = null
      }
    } catch {
      if (attempt >= 40) {
        this.workstationStarting = false
        if (this.workstationStartPoll) clearInterval(this.workstationStartPoll)
        this.workstationStartPoll = null
      }
    }

    this.patchWorkstationServerControl()
  }

  private patchWorkstationServerControl(): void {
    const online = this.workstationOnline()
    const mismatch = this.workstationRuntimeMismatch()
    const migrationNeeded = this.workstationRootMigrationNeeded()
    const state = this.workstationProcess
    const status = this.shadowRoot?.querySelector<HTMLElement>('[data-role="workstation-server-status"]')
    const button = this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="start-workstation"]')

    if (status) {
      const phase = online
        ? 'ONLINE'
        : mismatch
          ? 'INCOMPATIBLE'
          : this.workstationStarting
            ? 'STARTING'
            : (state?.phase ?? 'OFFLINE')

      status.dataset.online = online ? 'true' : 'false'
      status.dataset.phase = phase
      status.innerHTML = online
        ? `<span class="serverDot" aria-hidden="true"></span><span>WORKSTATION ONLINE · ${escapeHtml(this.workstationGenerationLabel())}</span>`
        : mismatch
          ? '<span class="serverDot" aria-hidden="true"></span><span>WORKSTATION LEGACY · RESTART REQUIRED</span>'
          : this.workstationStarting
            ? '<span class="serverDot" aria-hidden="true"></span><span>WORKSTATION STARTING</span>'
            : '<span class="serverDot" aria-hidden="true"></span><span>WORKSTATION OFFLINE</span>'

      status.title = online
        ? `${state?.runtime ?? 'EXTERNAL'} · ${state?.runtimeContract ?? ''} · ${state?.recoveryContract ?? ''} · ${state?.bind ?? '127.0.0.1:47832'}`
        : (state?.lastError ?? 'Workstation Server is not responding')
    }

    if (button) {
      button.hidden = online && !migrationNeeded
      button.disabled = this.workstationStarting
      button.dataset.mode = migrationNeeded
        ? 'activate-release-exe'
        : mismatch
          ? 'replace-legacy'
          : 'start'
      button.textContent = this.workstationStarting
        ? (migrationNeeded ? 'ACTIVATING…' : mismatch ? 'REPLACING…' : 'STARTING…')
        : migrationNeeded
          ? 'ACTIVATE RELEASE EXE'
          : mismatch
            ? 'REPLACE LEGACY'
            : 'START WORKSTATION'
      button.title = migrationNeeded
        ? `Human action: build/publish ${state?.rootReleasePath ?? 'vertex-workstation.exe'} and replace the current validated Workstation listener`
        : mismatch
          ? 'Human action: validate and replace the legacy Workstation listener on 127.0.0.1:47832'
          : 'Start Vertex Workstation Server as a separate process'
    }
  }

  private async exportCard(cardId: string): Promise<void> {
    if (this.busyCardId) return
    this.busyCardId = cardId
    this.busyAction = 'export'
    this.notice = ''
    this.render()

    try {
      await window.vertexPortal.exportVraCard(cardId)
      this.notice = ''
    } catch (error) {
      this.notice = `EXPORT FAILED · ${error instanceof Error ? error.message : String(error)}`
    } finally {
      this.busyCardId = ''
      this.busyAction = ''
      await this.refresh()
    }
  }

  private explicitTestCard(card: WorkstationDispatchCard): boolean {
    return card.cardKind === 'TEST'
  }

  private testRerunEligible(card: WorkstationDispatchCard): boolean {
    return Boolean(
      this.explicitTestCard(card) &&
      card.status === 'DISPATCHED' &&
      card.humanApproval === 'APPROVED' &&
      ['SUCCEEDED', 'FAILED', 'REJECTED', 'ROLLED_BACK'].includes(card.workstationJobState ?? '') &&
      card.workstationEvidenceReturnState === 'RETURNED'
    )
  }

  private testRerunButton(card: WorkstationDispatchCard, busy: boolean): string {
    // Absolute UI contract: production/unmarked cards receive no RE-RUN DOM.
    if (!this.explicitTestCard(card)) return ''

    const eligible = this.testRerunEligible(card)
    const rerunning = busy && this.busyAction === 'rerun-test'
    return `
      <button
        type="button"
        class="export"
        data-action="rerun-test"
        data-card-id="${escapeHtml(card.id)}"
        ${eligible ? '' : 'hidden'}
        ${busy || !eligible ? 'disabled' : ''}
        title="Create a new TEST run with new artifact/job/correlation IDs; Human Approval resets to PENDING"
      >${rerunning ? 'STAGING…' : 'RE-RUN'}</button>
    `
  }

  private async rerunTestCard(cardId: string): Promise<void> {
    if (this.busyCardId) return
    const card = ((this.state?.cards ?? []) as WorkstationDispatchCard[])
      .find(candidate => candidate.id === cardId)
    if (!card || !this.testRerunEligible(card)) return

    this.busyCardId = cardId
    this.busyAction = 'rerun-test'
    this.notice = ''
    this.render()

    try {
      await window.vertexPortal.exportVraCard(`vertex-test-rerun:${cardId}`)
      this.notice = 'TEST RE-RUN STAGED · HUMAN APPROVAL REQUIRED'
    } catch (error) {
      this.notice = `TEST RE-RUN FAILED · ${error instanceof Error ? error.message : String(error)}`
    } finally {
      this.busyCardId = ''
      this.busyAction = ''
      await this.refresh()
    }
  }

  private loadAutoAuthorities(): ArdAutoAuthorityLease[] {
    try {
      const parsed = JSON.parse(localStorage.getItem(AUTO_AUTHORITY_KEY) ?? '[]') as unknown
      if (!Array.isArray(parsed)) return []
      const now = Date.now()
      return parsed.filter((row): row is ArdAutoAuthorityLease => {
        if (!row || typeof row !== 'object') return false
        const lease = row as Partial<ArdAutoAuthorityLease>
        return lease.schema === 'vertex-session-portal/auto-authority-1'
          && typeof lease.authority_id === 'string'
          && typeof lease.controller_session === 'string'
          && Array.isArray(lease.allowed_sessions)
          && typeof lease.granted_utc === 'string'
          && typeof lease.expires_utc === 'string'
          && lease.status === 'ACTIVE'
          && Number.isFinite(Date.parse(lease.expires_utc))
          && Date.parse(lease.expires_utc) > now
      })
    } catch {
      return []
    }
  }

  private loadAutoTaskContexts(): Record<string, ArdAutoTaskContext> {
    try {
      const parsed = JSON.parse(localStorage.getItem(AUTO_TASK_CONTEXT_KEY) ?? '{}') as unknown
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? parsed as Record<string, ArdAutoTaskContext>
        : {}
    } catch {
      return {}
    }
  }

  private autoAuthorityForCard(
    card: WorkstationDispatchCard
  ): { lease: ArdAutoAuthorityLease; parentTaskId: string | null } | null {
    const originSession = card.originSession?.trim().toLowerCase()
    if (!originSession || card.originVera === 'UNKNOWN') return null
    if (card.status !== 'STAGED' || card.humanApproval !== 'PENDING') return null

    const captured = Date.parse(card.capturedUtc)
    if (!Number.isFinite(captured)) return null

    const candidates = this.loadAutoAuthorities().filter(lease => {
      const granted = Date.parse(lease.granted_utc)
      return Number.isFinite(granted)
        && captured >= granted
        && lease.allowed_sessions.map(value => value.toLowerCase()).includes(originSession)
    })
    if (!candidates.length) return null

    const context = this.loadAutoTaskContexts()[originSession]
    if (context) {
      const contextual = candidates.find(lease => lease.authority_id === context.authority_id)
      if (contextual) {
        return { lease: contextual, parentTaskId: context.parent_dispatch_id }
      }
    }

    const self = candidates.filter(lease => lease.controller_session.toLowerCase() === originSession)
    if (self.length === 1) return { lease: self[0], parentTaskId: null }
    if (candidates.length === 1) return { lease: candidates[0], parentTaskId: null }

    // Multiple controllers with overlapping scope and no exact TASK context are ambiguous.
    // Fail closed rather than silently choosing an authority.
    return null
  }

  private routeAutoAuthorizedCards(): Promise<void> {
    if (this.autoDispatchCycleInFlight) return this.autoDispatchCycleInFlight

    const blocked = this.workstationDispatchBlockReason()
    if (blocked) return Promise.resolve()

    const cards = ((this.state?.cards ?? []) as WorkstationDispatchCard[])
      .filter(card => !this.autoDispatchInFlight.has(card.id))
      .map(card => ({ card, authority: this.autoAuthorityForCard(card) }))
      .filter((row): row is {
        card: WorkstationDispatchCard
        authority: { lease: ArdAutoAuthorityLease; parentTaskId: string | null }
      } => Boolean(row.authority))
      .sort((a, b) => Date.parse(a.card.capturedUtc) - Date.parse(b.card.capturedUtc))

    if (!cards.length) return Promise.resolve()

    const cycle = (async (): Promise<void> => {
      for (const row of cards) {
        if (this.autoDispatchInFlight.has(row.card.id)) continue
        this.autoDispatchInFlight.add(row.card.id)
        try {
          const payload = encodeURIComponent(JSON.stringify({
            authority_id: row.authority.lease.authority_id,
            card_id: row.card.id,
            parent_task_id: row.authority.parentTaskId,
          }))
          await window.vertexPortal.exportVraCard(`${AUTO_DISPATCH_COMMAND_PREFIX}${payload}`)
        } catch (error) {
          const raw = error instanceof Error ? error.message : String(error)
          this.notice = `AUTO DISPATCH FAIL-CLOSED · ${raw}`
          this.render()
        } finally {
          this.autoDispatchInFlight.delete(row.card.id)
        }
      }
    })()

    const tracked = cycle.finally(() => {
      if (this.autoDispatchCycleInFlight === tracked) {
        this.autoDispatchCycleInFlight = null
      }
    })
    this.autoDispatchCycleInFlight = tracked
    return tracked
  }

  private requestDispatch(cardId: string): void {
    if (this.autoDispatchInFlight.has(cardId)) return
    // 000104V5: the physical click on "工場へ発注" is the Human Gate.
    // No second confirmation dialog. Existing safety/block/busy checks still run
    // inside dispatch() before the durable approval/publish transaction begins.
    if (this.busyCardId) return
    void this.dispatch(cardId)
  }

  private async dispatch(cardId: string): Promise<void> {
    if (this.busyCardId) return

    const blocked = this.workstationDispatchBlockReason()
    if (blocked) {
      this.notice = blocked
      this.render()
      return
    }

    this.busyCardId = cardId
    this.busyAction = 'dispatch'
    this.notice = ''
    this.render()

    try {
      await window.vertexPortal.dispatchVraCard(cardId)
      this.notice = 'DISPATCHED · WORKSTATION INTAKE'
    } catch (error) {
      const raw = error instanceof Error ? error.message : String(error)
      this.notice = this.humanFacingError(raw)?.message ?? '新工場へ送れません'
    } finally {
      this.busyCardId = ''
      this.busyAction = ''
      await this.refresh()
    }
  }

  private orderedCards(): WorkstationDispatchCard[] {
    const cards = (this.state?.cards ?? []) as WorkstationDispatchCard[]
    const staged = cards.filter(card => card.status !== 'DISPATCHED')
    const dispatched = cards.filter(card => card.status === 'DISPATCHED')
    return [...staged, ...dispatched]
  }

  private selectCard(cardId: string, shiftKey: boolean): void {
    const ordered = this.orderedCards()
    const targetIndex = ordered.findIndex(card => card.id === cardId)
    if (targetIndex < 0) return

    if (shiftKey && this.selectionAnchorId) {
      const anchorIndex = ordered.findIndex(card => card.id === this.selectionAnchorId)
      if (anchorIndex >= 0) {
        const from = Math.min(anchorIndex, targetIndex)
        const to = Math.max(anchorIndex, targetIndex)
        this.selectedCardIds.clear()
        for (let index = from; index <= to; index += 1) {
          this.selectedCardIds.add(ordered[index].id)
        }
        this.patchSelectionState()
        return
      }
    }

    this.selectedCardIds.clear()
    this.selectedCardIds.add(cardId)
    this.selectionAnchorId = cardId
    this.patchSelectionState()
  }

  private clearSelection(): void {
    this.selectedCardIds.clear()
    this.selectionAnchorId = ''
    this.patchSelectionState()
  }

  private requestRemove(cardId: string): void {
    if (this.busyCardId || this.removingCards) return

    const ids = this.selectedCardIds.has(cardId) && this.selectedCardIds.size > 1
      ? this.orderedCards()
          .filter(card => this.selectedCardIds.has(card.id))
          .map(card => card.id)
      : [cardId]

    if (ids.length === 0) return
    this.pendingRemoveCardIds = ids

    const dialog = this.shadowRoot?.querySelector<HTMLDialogElement>('[data-role="remove-dialog"]')
    const heading = this.shadowRoot?.querySelector<HTMLElement>('[data-role="remove-dialog-heading"]')
    const title = this.shadowRoot?.querySelector<HTMLElement>('[data-role="remove-dialog-title"]')
    const confirm = this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="remove-confirm"]')

    if (heading) {
      heading.textContent = ids.length > 1
        ? `${ids.length}枚のカードを削除しますか？`
        : '発注カードを削除しますか？'
    }

    if (title) {
      if (ids.length > 1) {
        title.textContent = `選択範囲 · ${ids.length} CARDS`
      } else {
        const card = this.orderedCards().find(candidate => candidate.id === cardId)
        title.textContent = card?.jobTitle ?? card?.filename ?? 'VRA'
      }
    }

    if (confirm) confirm.textContent = ids.length > 1 ? `${ids.length}枚を削除` : '削除する'
    if (dialog && !dialog.open) dialog.showModal()
  }

  private closeRemoveDialog(): void {
    this.pendingRemoveCardIds = []
    const dialog = this.shadowRoot?.querySelector<HTMLDialogElement>('[data-role="remove-dialog"]')
    if (dialog?.open) dialog.close()
  }

  private confirmRemove(): void {
    const ids = [...this.pendingRemoveCardIds]
    this.closeRemoveDialog()
    if (ids.length > 0) void this.removeCards(ids)
  }

  private async removeCards(cardIds: string[]): Promise<void> {
    if (this.busyCardId || this.removingCards || cardIds.length === 0) return
    this.removingCards = true
    this.notice = ''
    this.render()

    try {
      for (const cardId of cardIds) {
        await window.vertexPortal.removeVraCard(cardId)
      }
      this.selectedCardIds.clear()
      this.selectionAnchorId = ''
      this.notice = ''
    } catch (error) {
      this.notice = `CARD REMOVE FAILED · ${error instanceof Error ? error.message : String(error)}`
    } finally {
      this.removingCards = false
      await this.refresh()
    }
  }

  private patchSelectionState(): void {
    const selectedCount = this.selectedCardIds.size
    const queue = this.shadowRoot?.querySelector<HTMLElement>('.queue')

    for (const root of queue?.querySelectorAll<HTMLElement>('.vraCard') ?? []) {
      const cardId = root.dataset.cardId ?? ''
      const selected = this.selectedCardIds.has(cardId)
      root.dataset.selected = selected ? 'true' : 'false'
      root.setAttribute('aria-selected', selected ? 'true' : 'false')

      const removeButton = root.querySelector<HTMLButtonElement>('[data-action="remove"]')
      if (removeButton) {
        const batch = selected && selectedCount > 1
        removeButton.textContent = batch ? `× ${selectedCount}` : '×'
        removeButton.setAttribute(
          'aria-label',
          batch ? `選択した${selectedCount}枚の発注カードを削除` : '発注カードを削除'
        )
        removeButton.title = batch ? `選択した${selectedCount}枚を削除` : '発注カードを削除'
      }
    }

    const selectionCount = this.shadowRoot?.querySelector<HTMLElement>('[data-role="selection-count"]')
    if (selectionCount) {
      selectionCount.hidden = selectedCount === 0
      selectionCount.textContent = `選択 ${selectedCount}`
    }
  }

  // FINAL_WIRING_B_000054V1: exact origin Evidence routing; never active-window inference.
  private exactOriginRoute(card: WorkstationDispatchCard): boolean {
    const session = card.originSession ?? ''
    const expectedVera = /^vera-0[1-5]$/.test(session) ? `VERA${session.slice(-2)}` : ''
    return Boolean(
      card.jobId && card.evidenceIdentity && card.evidenceDeliveryPayload &&
      expectedVera && card.originVera === expectedVera &&
      card.originWindow === session &&
      card.correlationId && card.returnChannel
    )
  }

  private routePendingEvidence(): void {
    const cards = (this.state?.cards ?? []) as WorkstationDispatchCard[]
    for (const card of cards) {
      const deliveryId = card.evidenceIdentity ?? ''
      if (!deliveryId || this.evidenceInFlight.has(deliveryId) || this.hasDeliveryLedgerEntry(card)) continue
      if (card.workstationEvidenceState !== 'AVAILABLE' || !this.exactOriginRoute(card)) continue
      this.writeDeliveryAttempt(card)
      const detail: VeraEvidenceReturnMessage = {
        deliveryId,
        jobId: card.jobId!,
        originVera: card.originVera!,
        originSession: card.originSession!,
        originWindow: card.originWindow!,
        correlationId: card.correlationId!,
        returnChannel: card.returnChannel!,
        text: card.evidenceDeliveryPayload!
      }
      this.evidenceInFlight.add(deliveryId)
      window.dispatchEvent(new CustomEvent<VeraEvidenceReturnMessage>(VERA_EVIDENCE_RETURN_EVENT, { detail }))
    }
  }

  private retryPendingAcks(): void {
    const cards = (this.state?.cards ?? []) as WorkstationDispatchCard[]
    for (const card of cards) {
      const receipt = card.evidenceIdentity ? this.readDeliveryReceipts()[card.evidenceIdentity] : undefined
      if (!receipt || receipt.state !== 'DELIVERED' || card.workstationEvidenceReturnState === 'RETURNED') continue
      if (card.workstationEvidenceReturnState !== 'RETURN_QUEUED') continue
      void this.ackDeliveredEvidence(card)
    }
  }

  private async ackDeliveredEvidence(card: WorkstationDispatchCard): Promise<void> {
    const evidenceId = card.evidenceIdentity ?? ''
    const artifactId = card.artifactId ?? ''
    const jobId = card.jobId ?? ''
    if (!evidenceId || !artifactId || !jobId || this.evidenceAckInFlight.has(evidenceId)) return
    const receipt = this.readDeliveryReceipts()[evidenceId]
    // ACK can only follow a durable DELIVERED receipt. IN_FLIGHT / DELIVERY_UNCERTAIN never ACKs.
    if (!receipt || receipt.state !== 'DELIVERED' || !this.hasDeliveryReceipt(card)) return
    if (card.workstationEvidenceReturnState !== 'RETURN_QUEUED' && card.workstationEvidenceReturnState !== 'RETURNED') return
    if (card.workstationEvidenceReturnState === 'RETURNED') return

    this.evidenceAckInFlight.add(evidenceId)
    try {
      const result = await window.vertexPortal.acknowledgeVraEvidenceDelivery({
        cardId: card.id,
        evidenceId,
        artifactId,
        returnedAt: receipt.deliveredAt
      })
      if (!result.acknowledged || result.jobId !== jobId || result.evidenceId !== evidenceId ||
          result.artifactId !== artifactId || result.evidenceReturnState !== 'RETURNED' ||
          result.returnedAt !== receipt.deliveredAt) {
        throw new Error('EVIDENCE_ACK_RESULT_MISMATCH')
      }
      this.notice = result.idempotent ? 'RETURNED · ACK RETRY SAFE' : 'RETURNED · ACKNOWLEDGED'
    } catch (error) {
      // Durable DELIVERED remains authoritative. Exact same returnedAt will be retried; no Vera reinjection.
      this.notice = `ACK RETRY PENDING · ${error instanceof Error ? error.message : String(error)}`
    } finally {
      this.evidenceAckInFlight.delete(evidenceId)
      this.render()
    }
  }

  private readDeliveryReceipts(): Record<string, EvidenceDeliveryReceipt> {
    try {
      const raw = window.localStorage.getItem(EVIDENCE_RECEIPTS_KEY)
      if (!raw) return {}
      const value = JSON.parse(raw) as unknown
      return value && typeof value === 'object' && !Array.isArray(value)
        ? value as Record<string, EvidenceDeliveryReceipt>
        : {}
    } catch {
      return {}
    }
  }

  private hasDeliveryLedgerEntry(card: WorkstationDispatchCard): boolean {
    if (!card.evidenceIdentity || !card.jobId) return false
    const entry = this.readDeliveryReceipts()[card.evidenceIdentity]
    return Boolean(entry && entry.jobId === card.jobId)
  }

  private hasDeliveryReceipt(card: WorkstationDispatchCard): boolean {
    if (!card.evidenceIdentity || !card.jobId) return false
    const receipt = this.readDeliveryReceipts()[card.evidenceIdentity]
    return Boolean(
      receipt && receipt.jobId === card.jobId &&
      receipt.originVera === card.originVera &&
      receipt.originSession === card.originSession &&
      receipt.originWindow === card.originWindow &&
      receipt.correlationId === card.correlationId &&
      receipt.returnChannel === card.returnChannel
    )
  }

  private writeDeliveryAttempt(card: WorkstationDispatchCard): void {
    this.writeDeliveryLedger(card, 'IN_FLIGHT')
  }

  private clearDeliveryAttempt(card: WorkstationDispatchCard): void {
    if (!card.evidenceIdentity) return
    const receipts = this.readDeliveryReceipts()
    delete receipts[card.evidenceIdentity]
    window.localStorage.setItem(EVIDENCE_RECEIPTS_KEY, JSON.stringify(receipts))
  }

  private writeDeliveryReceipt(card: WorkstationDispatchCard): void {
    this.writeDeliveryLedger(card, 'DELIVERED')
  }

  private writeDeliveryLedger(card: WorkstationDispatchCard, state: 'IN_FLIGHT' | 'DELIVERED'): void {
    if (!this.exactOriginRoute(card)) throw new Error('EVIDENCE_RECEIPT_ORIGIN_FAIL_CLOSED')
    const receipts = this.readDeliveryReceipts()
    receipts[card.evidenceIdentity!] = {
      schema: 'vertex-session-portal/evidence-delivery-receipt-1',
      state,
      deliveryId: card.evidenceIdentity!,
      jobId: card.jobId!,
      originVera: card.originVera!,
      originSession: card.originSession!,
      originWindow: card.originWindow!,
      correlationId: card.correlationId!,
      returnChannel: card.returnChannel!,
      deliveredAt: new Date().toISOString()
    }
    const entries = Object.entries(receipts)
      .sort((a, b) => b[1].deliveredAt.localeCompare(a[1].deliveredAt))
      .slice(0, 256)
    window.localStorage.setItem(EVIDENCE_RECEIPTS_KEY, JSON.stringify(Object.fromEntries(entries)))
  }

  private workstationDispatchBlockReason(): string | null {
    // Use the same authoritative health aggregation as the header/process control.
    // 000067V5 added a direct process-health path, but this dispatch gate still
    // consulted the older VraDispatchState.workstationOnline flag, which could
    // leave cards disabled while the server was already visibly ONLINE.
    if (this.workstationRuntimeMismatch()) {
      return `WORKSTATION RUNTIME MISMATCH · ${this.workstationGenerationLabel()} · 000069V5対応Serverへ再起動してください`
    }
    if (!this.workstationOnline()) return 'WORKSTATION OFFLINE'

    const safety = this.state?.workstationSafety
    if (!safety || safety.online !== true) return 'WORKSTATION SAFETY UNKNOWN'
    return safety.state === 'RUNNING' ? null : `SAFETY HOLD · ${safety.state}`
  }

  private safetyHoldState(): string | null {
    const reason = this.workstationDispatchBlockReason()
    return reason?.startsWith('SAFETY HOLD · ')
      ? reason.slice('SAFETY HOLD · '.length)
      : null
  }

  private displayStatus(card: WorkstationDispatchCard): string {
    if (card.workstationEvidenceReturnState === 'RETURNED') return 'RETURNED'
    const delivery = card.evidenceIdentity ? this.readDeliveryReceipts()[card.evidenceIdentity] : undefined
    if (delivery?.state === 'IN_FLIGHT') return 'DELIVERY_UNCERTAIN'
    if (this.hasDeliveryReceipt(card) && this.evidenceLifecycleReturnText(card) !== 'RETURNED') return 'ACK_PENDING'
    if (this.evidenceLifecycleEvidenceText(card) === 'AVAILABLE') return 'EVIDENCE_AVAILABLE'
    if (card.workstationRegistration === 'REGISTERING') return 'REGISTERING'
    if (card.workstationRegistration === 'PENDING' && card.status === 'DISPATCHED') return 'REGISTRATION_PENDING'
    if (card.workstationRegistration === 'BLOCKED') return 'FAILED'
    return card.workstationJobState ?? (card.status === 'DISPATCHED' ? 'PUBLISHED' : card.status)
  }

  private factoryStage(card: WorkstationDispatchCard): string {
    const systemStatus = this.displayStatus(card)

    if (card.workstationEvidenceReturnState === 'RETURNED') return '清算済み'
    if (['FAILED', 'ERROR', 'REJECTED', 'ROLLED_BACK', 'DELIVERY_UNCERTAIN'].includes(systemStatus)) return '要確認'
    if (systemStatus === 'ACK_PENDING') return '返却中'
    if (systemStatus === 'EVIDENCE_AVAILABLE' || systemStatus === 'SUCCEEDED') return '検証済み'
    if (systemStatus === 'EXECUTING') return '作業中'
    if (card.status === 'DISPATCHED' || ['REGISTRATION_PENDING', 'REGISTERING', 'REGISTERED', 'DISPATCHED', 'PUBLISHED'].includes(systemStatus)) {
      return '発注済み'
    }
    return '未発注'
  }

  private formatBytes(value: number): string {
    if (value < 1024) return `${value} B`
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
    return `${(value / (1024 * 1024)).toFixed(1)} MB`
  }

  private originSessionWindow(card: WorkstationDispatchCard): string {
    const values = [card.originSession, card.originWindow]
      .filter((value): value is string => typeof value === 'string' && value.length > 0)
    return [...new Set(values)].join(' / ') || 'UNKNOWN'
  }

  private field(label: string, value: string, wide = false): string {
    return `
      <div class="field${wide ? ' wide' : ''}">
        <span>${escapeHtml(label)}</span>
        <strong title="${escapeHtml(value)}">${escapeHtml(value)}</strong>
      </div>
    `
  }

  private stableCardKey(card: WorkstationDispatchCard): string {
    return card.jobId?.trim() || card.artifactId?.trim() || card.id
  }

  private humanFacingError(raw: string | null | undefined): { message: string; detail: string } | null {
    const detail = raw?.trim() ?? ''
    if (!detail) return null

    if (detail.includes('ROUTING_REQUIRED_FOR_HTTP_JOB_REGISTRATION') ||
        detail.includes('VRA_ROUTING_') ||
        detail.includes('APPROVAL_SIDECAR_ORIGIN_')) {
      return {
        message: '新工場へ送れません · 発行元情報の登録が不完全です',
        detail
      }
    }

    return {
      message: '新工場の処理で問題が発生しました · DETAILSを確認してください',
      detail
    }
  }

  private cardTemplate(card: WorkstationDispatchCard): string {
    const busy = this.removingCards || this.busyCardId === card.id
    const exporting = busy && this.busyAction === 'export'
    const dispatching = busy && this.busyAction === 'dispatch'
    const dispatched = card.status === 'DISPATCHED'
    const error = card.status === 'ERROR'
    const originVera = card.originVera ?? 'UNKNOWN'
    const projectName = card.projectName ?? 'UNAVAILABLE'
    const artifactId = card.artifactId ?? 'UNAVAILABLE'
    const jobTitle = card.jobTitle ?? card.filename
    const requestedLane = card.requestedLane ?? 'AUTO'
    const lanePolicy = card.lanePolicy ?? 'ANY'
    const humanApproval = card.humanApproval ?? 'PENDING'
    const allocatedLane = card.allocatedLane ?? null
    const displayStatus = this.displayStatus(card)
    const factoryStage = this.factoryStage(card)
    const blocked = this.workstationDispatchBlockReason()
    const safetyHold = this.safetyHoldState()
    const dispatchDisabled = dispatched || busy || blocked !== null
    const stableKey = this.stableCardKey(card)
    const humanError = this.humanFacingError(card.workstationLastError ?? card.error)

    return `
      <article class="vraCard" role="option" tabindex="0" aria-selected="${this.selectedCardIds.has(card.id) ? 'true' : 'false'}" data-selected="${this.selectedCardIds.has(card.id) ? 'true' : 'false'}" draggable="${dispatched ? 'false' : 'true'}" data-interaction-lock="false" data-card-id="${escapeHtml(card.id)}" data-stable-key="${escapeHtml(stableKey)}" data-allocated-lane="${escapeHtml(allocatedLane ?? '')}">
        <div class="cardTop">
          <div class="cardIdentity">
            <span class="source" data-role="origin-vera">${escapeHtml(originVera)}</span>
            <span class="project" data-role="project-name">${escapeHtml(projectName)}</span>
          </div>
          <div class="cardTopActions">
            <span class="state" data-role="status" data-state="${escapeHtml(displayStatus)}" data-factory-stage="${escapeHtml(factoryStage)}" title="SYSTEM STATUS · ${escapeHtml(displayStatus)}">${escapeHtml(factoryStage)}</span>
            <button type="button" class="cardRemove" data-action="remove" data-card-id="${escapeHtml(card.id)}" ${busy ? 'disabled' : ''} aria-label="発注カードを削除" title="発注カードを削除">×</button>
              <!-- VERTEX_CARD_ERROR_COPY_000033V2 -->
              <button
                class="cardErrorCopy"
                type="button"
                data-error-copy-card="${escapeHtml(card.id)}"
                title="Copy card error for VERA"
                aria-label="Copy card error for VERA"
                ${this.hasCopyableCardError(card) ? '' : 'hidden'}
              >COPY</button>

          </div>
        </div>

        <div class="jobTitle" data-role="job-title" title="${escapeHtml(jobTitle)}">${escapeHtml(jobTitle)}</div>

        <div class="cardSummary">
          <span class="lanePill" data-role="lane-policy">${escapeHtml(lanePolicy)}</span>
          <span data-role="requested-lane">REQUEST ${escapeHtml(requestedLane)}</span>
          <span data-role="allocated-lane">LANE ${escapeHtml(allocatedLane ?? '--')}</span>
          <span class="approval" data-role="human-approval" data-approval="${escapeHtml(humanApproval)}">APPROVAL ${escapeHtml(humanApproval)}</span>
        </div>

        <div class="error" data-role="human-error" ${humanError ? '' : 'hidden'} title="${escapeHtml(humanError?.detail ?? '')}">${escapeHtml(humanError?.message ?? '')}</div>
        <div class="workstationOffline" data-role="workstation-block" ${blocked && !dispatched ? '' : 'hidden'}>${escapeHtml(blocked ?? '')}</div>

        <div class="cardBottom">
          <details class="cardDetails">
            <summary>DETAILS</summary>
            <div class="detailGrid">
              ${this.field('ORIGIN VERA', originVera)}
              ${this.field('ORIGIN SESSION / WINDOW', this.originSessionWindow(card))}
              ${this.field('PROJECT NAME', projectName)}
              ${this.field('ARTIFACT ID', artifactId)}
              ${this.field('TITLE / JOB SUMMARY', jobTitle, true)}
              ${this.field('REQUESTED LANE', requestedLane)}
              ${this.field('LANE POLICY', lanePolicy)}
              ${this.field('ALLOCATED LANE · WORKSTATION', allocatedLane ?? 'NOT ALLOCATED')}
              ${this.field('FACTORY STATE', factoryStage)}
              ${this.field('SYSTEM STATUS', displayStatus)}
              ${this.field('HUMAN APPROVAL', humanApproval)}
              ${this.field('JOB ID', card.jobId ?? 'UNAVAILABLE')}
              ${this.field('CORRELATION ID', card.correlationId ?? 'UNAVAILABLE')}
              ${humanError ? this.field('TECHNICAL ERROR', humanError.detail, true) : ''}
            </div>
          </details>

          <div class="cardActions">
            ${!dispatched ? `
              <button type="button" class="dispatchPrimary" data-action="dispatch" data-human-gate="APPROVE + DISPATCH" data-card-id="${escapeHtml(card.id)}" ${safetyHold ? 'disabled' : ''} ${dispatchDisabled ? 'disabled' : ''} ${blocked ? `title="${escapeHtml(blocked)}"` : ''}>
                ${dispatching ? '発注中…' : '工場へ発注'}
              </button>
            ` : ''}
            ${this.testRerunButton(card, busy)}
            <button type="button" class="export" data-action="export" data-card-id="${escapeHtml(card.id)}" ${busy ? 'disabled' : ''} title="Export VRA for Old Vertex Works / manual route">
              ${exporting ? 'EXPORTING…' : 'EXPORT'}
            </button>
          </div>
        </div>
      </article>
    `
  }

  private bind(): void {
    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="start-workstation"]')
      ?.addEventListener('click', () => void this.startWorkstationServer())

    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="refresh"]')
      ?.addEventListener('click', () => void this.refresh())

    const queue = this.shadowRoot?.querySelector<HTMLElement>('.queue')

    // 000107V5: Chromium starts native text-range selection on mousedown,
    // before the later click handler can process Shift-range card selection.
    // Suppress only Shift + primary-button mousedown on the selectable card body.
    // Normal text selection remains available without Shift, and interactive
    // Details/Actions controls keep their native behavior.
    queue?.addEventListener('mousedown', event => {
      const mouse = event as MouseEvent
      if (!mouse.shiftKey || mouse.button !== 0) return

      const target = event.target as HTMLElement | null
      if (target?.closest('button, summary, details, .cardDetails, .cardActions')) return

      const card = target?.closest<HTMLElement>('.vraCard')
      if (!card?.dataset.cardId) return

      mouse.preventDefault()
      window.getSelection()?.removeAllRanges()
    })

    queue?.addEventListener('click', event => {
      const target = event.target as HTMLElement | null
      const button = target?.closest<HTMLButtonElement>('button[data-action][data-card-id]')

      if (button) {
        event.preventDefault()
        event.stopPropagation()

        const cardId = button.dataset.cardId
        if (!cardId) return

        switch (button.dataset.action) {
          case 'export':
            void this.exportCard(cardId)
            break
          case 'dispatch':
            this.requestDispatch(cardId)
            break
          case 'rerun-test':
            void this.rerunTestCard(cardId)
            break
          case 'remove':
            this.requestRemove(cardId)
            break
        }
        return
      }

      // Card body click selects one. Shift+click selects the contiguous visible range.
      // Details/actions stay interactive and do not accidentally change selection.
      if (target?.closest('.cardDetails, .cardActions')) return
      const card = target?.closest<HTMLElement>('.vraCard')
      const cardId = card?.dataset.cardId
      if (card && cardId) {
        const mouse = event as MouseEvent
        if (mouse.shiftKey) mouse.preventDefault()
        card.focus({ preventScroll: true })
        this.selectCard(cardId, mouse.shiftKey)
        return
      }

      if (target === queue) this.clearSelection()
    })

    queue?.addEventListener('keydown', event => {
      const key = event as KeyboardEvent
      const target = event.target as HTMLElement | null
      const card = target?.closest<HTMLElement>('.vraCard')
      const cardId = card?.dataset.cardId
      if (!card || !cardId) return
      if (target?.closest('button, summary, details')) return

      if (key.key === 'Enter' || key.key === ' ') {
        key.preventDefault()
        this.selectCard(cardId, key.shiftKey)
        return
      }

      if (key.key === 'Delete') {
        key.preventDefault()
        this.requestRemove(cardId)
      }
    })

    // Native draggable cards can steal pointer gestures from their own buttons.
    // Lock dragging for the lifetime of an interactive pointer gesture.
    const restoreInteractiveDrag = (event: Event): void => {
      const target = event.target as HTMLElement | null
      const card = target?.closest<HTMLElement>('.vraCard')
      if (!card) return
      card.dataset.interactionLock = 'false'
      const cardId = card.dataset.cardId ?? ''
      const current = this.orderedCards().find(candidate => candidate.id === cardId)
      card.draggable = Boolean(current && current.status !== 'DISPATCHED')
    }

    queue?.addEventListener('pointerdown', event => {
      const target = event.target as HTMLElement | null
      const interactive = target?.closest<HTMLElement>('button, summary, details')
      const card = interactive?.closest<HTMLElement>('.vraCard')
      if (!interactive || !card) return
      card.dataset.interactionLock = 'true'
      card.draggable = false
    })
    queue?.addEventListener('pointerup', restoreInteractiveDrag)
    queue?.addEventListener('pointercancel', restoreInteractiveDrag)

    const removeDialog = this.shadowRoot?.querySelector<HTMLDialogElement>('[data-role="remove-dialog"]')
    removeDialog?.addEventListener('cancel', event => {
      event.preventDefault()
      this.closeRemoveDialog()
    })
    removeDialog?.addEventListener('click', event => {
      if (event.target === removeDialog) this.closeRemoveDialog()
    })
    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="remove-cancel"]')
      ?.addEventListener('click', () => this.closeRemoveDialog())
    this.shadowRoot?.querySelector<HTMLButtonElement>('[data-action="remove-confirm"]')
      ?.addEventListener('click', () => this.confirmRemove())

    queue?.addEventListener('dragstart', event => {
      const drag = event as DragEvent
      const card = (event.target as HTMLElement | null)?.closest<HTMLElement>('.vraCard[draggable="true"]')
      const cardId = card?.dataset.cardId
      if (!card || !cardId || !drag.dataTransfer) return
      drag.dataTransfer.effectAllowed = 'move'
      drag.dataTransfer.setData('application/x-vertex-vra-card', cardId)
      card.dataset.dragging = 'true'
    })

    queue?.addEventListener('dragend', event => {
      const card = (event.target as HTMLElement | null)?.closest<HTMLElement>('.vraCard')
      if (card) card.dataset.dragging = 'false'
    })

    const drop = this.shadowRoot?.querySelector<HTMLElement>('.worksDrop')
    drop?.addEventListener('dragover', event => {
      event.preventDefault()
      drop.dataset.over = 'true'
    })
    drop?.addEventListener('dragleave', () => {
      drop.dataset.over = 'false'
    })
    drop?.addEventListener('drop', event => {
      event.preventDefault()
      drop.dataset.over = 'false'
      const drag = event as DragEvent
      const cardId = drag.dataTransfer?.getData('application/x-vertex-vra-card')
      if (cardId) this.requestDispatch(cardId)
    })
  }

  private setText(root: HTMLElement, selector: string, value: string): void {
    const node = root.querySelector<HTMLElement>(selector)
    if (node && node.textContent !== value) node.textContent = value
  }

  private setDetail(root: HTMLElement, label: string, value: string): void {
    const fields = [...root.querySelectorAll<HTMLElement>('.field')]
    const field = fields.find(candidate =>
      candidate.querySelector('span')?.textContent === label
    )
    const strong = field?.querySelector<HTMLElement>('strong')
    if (!strong) return
    if (strong.textContent !== value) strong.textContent = value
    if (strong.title !== value) strong.title = value
  }

  private patchCard(root: HTMLElement, card: WorkstationDispatchCard): void {
    const busy = this.removingCards || this.busyCardId === card.id
    const exporting = busy && this.busyAction === 'export'
    const dispatching = busy && this.busyAction === 'dispatch'
    const dispatched = card.status === 'DISPATCHED'
    const originVera = card.originVera ?? 'UNKNOWN'
    const projectName = card.projectName ?? 'UNAVAILABLE'
    const artifactId = card.artifactId ?? 'UNAVAILABLE'
    const jobTitle = card.jobTitle ?? card.filename
    const requestedLane = card.requestedLane ?? 'AUTO'
    const lanePolicy = card.lanePolicy ?? 'ANY'
    const humanApproval = card.humanApproval ?? 'PENDING'
    const allocatedLane = card.allocatedLane ?? null
    const displayStatus = this.displayStatus(card)
    const factoryStage = this.factoryStage(card)
    const blocked = this.workstationDispatchBlockReason()
    const safetyHold = this.safetyHoldState()
    const humanError = this.humanFacingError(card.workstationLastError ?? card.error)

    root.dataset.cardId = card.id
    root.dataset.allocatedLane = allocatedLane ?? ''
    root.dataset.selected = this.selectedCardIds.has(card.id) ? 'true' : 'false'
    root.setAttribute('aria-selected', this.selectedCardIds.has(card.id) ? 'true' : 'false')
    root.draggable = !dispatched && root.dataset.interactionLock !== 'true'

    this.setText(root, '[data-role="origin-vera"]', originVera)
    this.setText(root, '[data-role="project-name"]', projectName)
    this.setText(root, '[data-role="job-title"]', jobTitle)
    this.setText(root, '[data-role="lane-policy"]', lanePolicy)
    this.setText(root, '[data-role="requested-lane"]', `REQUEST ${requestedLane}`)
    this.setText(root, '[data-role="allocated-lane"]', `LANE ${allocatedLane ?? '--'}`)
    this.setText(root, '[data-role="human-approval"]', `APPROVAL ${humanApproval}`)

    const title = root.querySelector<HTMLElement>('[data-role="job-title"]')
    if (title) title.title = jobTitle

    const status = root.querySelector<HTMLElement>('[data-role="status"]')
    if (status) {
      if (status.textContent !== factoryStage) status.textContent = factoryStage
      status.dataset.state = displayStatus
      status.dataset.factoryStage = factoryStage
      status.title = `SYSTEM STATUS · ${displayStatus}`
    }

    const approval = root.querySelector<HTMLElement>('[data-role="human-approval"]')
    if (approval) approval.dataset.approval = humanApproval

    const errorNode = root.querySelector<HTMLElement>('[data-role="human-error"]')
    if (errorNode) {
      errorNode.hidden = !humanError
      errorNode.textContent = humanError?.message ?? ''
      errorNode.title = humanError?.detail ?? ''
    }

    const blockNode = root.querySelector<HTMLElement>('[data-role="workstation-block"]')
    if (blockNode) {
      blockNode.hidden = !(blocked && !dispatched)
      blockNode.textContent = blocked ?? ''
    }

    const dispatchButton = root.querySelector<HTMLButtonElement>('[data-action="dispatch"]')
    if (dispatchButton) {
      dispatchButton.disabled = dispatched || busy || blocked !== null || safetyHold !== null
      dispatchButton.textContent = dispatching ? '発注中…' : '工場へ発注'
      dispatchButton.title = blocked ?? ''
      dispatchButton.hidden = dispatched
    }

    const rerunButton = root.querySelector<HTMLButtonElement>('[data-action="rerun-test"]')
    if (rerunButton) {
      const eligible = this.testRerunEligible(card)
      rerunButton.hidden = !eligible
      rerunButton.disabled = busy || !eligible
      rerunButton.textContent = busy && this.busyAction === 'rerun-test' ? 'STAGING…' : 'RE-RUN'
    }

    const exportButton = root.querySelector<HTMLButtonElement>('[data-action="export"]')
    if (exportButton) {
      exportButton.disabled = busy
      exportButton.textContent = exporting ? 'EXPORTING…' : 'EXPORT'
    }

    const removeButton = root.querySelector<HTMLButtonElement>('[data-action="remove"]')
    if (removeButton) removeButton.disabled = busy

    this.setDetail(root, 'ORIGIN VERA', originVera)
    this.setDetail(root, 'ORIGIN SESSION / WINDOW', this.originSessionWindow(card))
    this.setDetail(root, 'PROJECT NAME', projectName)
    this.setDetail(root, 'ARTIFACT ID', artifactId)
    this.setDetail(root, 'TITLE / JOB SUMMARY', jobTitle)
    this.setDetail(root, 'REQUESTED LANE', requestedLane)
    this.setDetail(root, 'LANE POLICY', lanePolicy)
    this.setDetail(root, 'ALLOCATED LANE · WORKSTATION', allocatedLane ?? 'NOT ALLOCATED')
    this.setDetail(root, 'FACTORY STATE', factoryStage)
    this.setDetail(root, 'SYSTEM STATUS', displayStatus)
    this.setDetail(root, 'HUMAN APPROVAL', humanApproval)
    this.setDetail(root, 'JOB ID', card.jobId ?? 'UNAVAILABLE')
    this.setDetail(root, 'CORRELATION ID', card.correlationId ?? 'UNAVAILABLE')
    if (humanError) this.setDetail(root, 'TECHNICAL ERROR', humanError.detail)
  }

  private reconcileCards(): void {
    const queue = this.shadowRoot?.querySelector<HTMLElement>('.queue')
    if (!queue) return

    const scrollTop = queue.scrollTop
    const activeElement = this.shadowRoot?.activeElement as HTMLElement | null
    const focusStableKey = activeElement?.closest<HTMLElement>('.vraCard')?.dataset.stableKey ?? null

    const cards = (this.state?.cards ?? []) as WorkstationDispatchCard[]
    const staged = cards.filter(card => card.status !== 'DISPATCHED')
    const dispatched = cards.filter(card => card.status === 'DISPATCHED')
    const settled = cards.filter(card => this.factoryStage(card) === '清算済み')
    const ordered = [...staged, ...dispatched]
    const liveIds = new Set(ordered.map(card => card.id))
    for (const selectedId of [...this.selectedCardIds]) {
      if (!liveIds.has(selectedId)) this.selectedCardIds.delete(selectedId)
    }
    if (this.selectionAnchorId && !liveIds.has(this.selectionAnchorId)) this.selectionAnchorId = ''

    const worksDrop = this.shadowRoot?.querySelector<HTMLElement>('.worksDrop')
    if (worksDrop) worksDrop.hidden = ordered.length === 0

    const existing = new Map(
      [...queue.querySelectorAll<HTMLElement>('.vraCard')]
        .map(node => [node.dataset.stableKey ?? '', node] as const)
        .filter(([key]) => key.length > 0)
    )

    const desiredKeys = new Set<string>()

    if (ordered.length === 0) {
      for (const node of existing.values()) node.remove()
      if (!queue.querySelector('.empty')) {
        queue.innerHTML = `
          <div class="empty">
            <div class="emptyMark" aria-hidden="true">◇</div>
            <strong>BAY READY</strong>
            <span>VRA待機中 · 受信した発注カードはここに表示されます。</span>
          </div>
        `
      }
    } else {
      queue.querySelector('.empty')?.remove()

      // 000078V5:
      // Keep existing DOM nodes physically stationary when order did not change.
      // The old unconditional appendChild(existingNode) moved every card on each
      // 2.5s Workstation poll, which could break pointer hover/active/focus and
      // suppress button click completion between pointerdown and pointerup.
      let expectedNode = queue.firstElementChild

      for (const card of ordered) {
        const key = this.stableCardKey(card)
        desiredKeys.add(key)
        let node = existing.get(key)

        if (!node) {
          const template = document.createElement('template')
          template.innerHTML = this.cardTemplate(card).trim()
          node = template.content.firstElementChild as HTMLElement | null ?? undefined
          if (!node) continue
          queue.insertBefore(node, expectedNode)
        } else if (node !== expectedNode) {
          // Reorder only when the logical order actually changed.
          queue.insertBefore(node, expectedNode)
        }

        this.patchCard(node, card)
        expectedNode = node.nextElementSibling
      }

      for (const [key, node] of existing) {
        if (!desiredKeys.has(key)) node.remove()
      }
    }

    queue.scrollTop = scrollTop

    // Focus remains on the unchanged DOM node. This guard only restores it if a browser
    // transiently dropped activeElement while an existing keyed node was moved.
    if (focusStableKey && !this.shadowRoot?.activeElement) {
      const focusCard = queue.querySelector<HTMLElement>(
        `.vraCard[data-stable-key="${CSS.escape(focusStableKey)}"]`
      )
      const fallback = focusCard?.querySelector<HTMLElement>('summary, button:not(:disabled)')
      fallback?.focus({ preventScroll: true })
      queue.scrollTop = scrollTop
    }

    const notice = this.shadowRoot?.querySelector<HTMLElement>('[data-role="notice"]')
    if (notice) {
      notice.hidden = !this.notice
      notice.textContent = this.notice
      notice.title = this.notice
    }

    const stagedCount = this.shadowRoot?.querySelector<HTMLElement>('[data-role="staged-count"]')
    const dispatchedCount = this.shadowRoot?.querySelector<HTMLElement>('[data-role="dispatched-count"]')
    const settledCount = this.shadowRoot?.querySelector<HTMLElement>('[data-role="settled-count"]')
    if (stagedCount) stagedCount.textContent = String(staged.length)
    if (dispatchedCount) dispatchedCount.textContent = String(dispatched.length)
    if (settledCount) settledCount.textContent = String(settled.length)
    this.patchSelectionState()
    this.patchWorkstationServerControl()
  }

  private render(): void {
    // Polling/status refreshes must never remount the card list.
    // Once the shell exists, update only keyed card state.
    if (this.shadowRoot?.querySelector('.lane')) {
      this.reconcileCards()
      return
    }

    const cards = (this.state?.cards ?? []) as WorkstationDispatchCard[]
    const staged = cards.filter(card => card.status !== 'DISPATCHED')
    const dispatched = cards.filter(card => card.status === 'DISPATCHED')
    const settled = cards.filter(card => this.factoryStage(card) === '清算済み')

    this.shadowRoot!.innerHTML = `
      <style>${styles}</style>
      <aside class="lane">
        <header class="header">
          <div>
            <div class="eyebrow">VRA / WORKSTATION LOGISTICS</div>
            <div class="title">DISPATCH BAY</div>
          </div>
          <div class="serverControl">
            <div
              class="serverStatus"
              data-role="workstation-server-status"
              data-online="${this.workstationOnline() ? 'true' : 'false'}"
              data-phase="${this.workstationOnline() ? 'ONLINE' : (this.workstationRuntimeMismatch() ? 'INCOMPATIBLE' : (this.workstationStarting ? 'STARTING' : (this.workstationProcess?.phase ?? 'OFFLINE')))}"
              title="${escapeHtml(this.workstationProcess?.lastError ?? this.workstationProcess?.bind ?? '127.0.0.1:47832')}"
            >
              <span class="serverDot" aria-hidden="true"></span>
              <span>${
                this.workstationOnline()
                  ? `WORKSTATION ONLINE · ${escapeHtml(this.workstationGenerationLabel())}`
                  : this.workstationRuntimeMismatch()
                    ? 'WORKSTATION LEGACY · RESTART REQUIRED'
                    : this.workstationStarting
                      ? 'WORKSTATION STARTING'
                      : 'WORKSTATION OFFLINE'
              }</span>
            </div>
            <button
              type="button"
              class="startWorkstation"
              data-action="start-workstation"
              data-mode="${this.workstationRuntimeMismatch() ? 'replace-legacy' : 'start'}"
              ${this.workstationOnline() ? 'hidden' : ''}
              ${this.workstationStarting ? 'disabled' : ''}
              title="${
                this.workstationRuntimeMismatch()
                  ? 'Human action: validate and replace the legacy Workstation listener on 127.0.0.1:47832'
                  : 'Start Vertex Workstation Server as a separate process'
              }"
            >${
              this.workstationStarting
                ? (this.workstationRuntimeMismatch() ? 'REPLACING…' : 'STARTING…')
                : this.workstationRuntimeMismatch()
                  ? 'REPLACE LEGACY'
                  : 'START WORKSTATION'
            }</button>
            <button type="button" class="refresh" data-action="refresh" title="Refresh">↻</button>
          </div>
        </header>
        <div class="notice" data-role="notice" ${this.notice ? '' : 'hidden'} title="${escapeHtml(this.notice)}">${escapeHtml(this.notice)}</div>

        <section class="queue" role="listbox" aria-label="VRA dispatch cards" aria-multiselectable="true">
          ${cards.length === 0 ? `
            <div class="empty">
              <div class="emptyMark" aria-hidden="true">◇</div>
              <strong>BAY READY</strong>
              <span>VRA待機中 · 受信した発注カードはここに表示されます。</span>
            </div>
          ` : `
            ${staged.map(card => this.cardTemplate(card)).join('')}
            ${dispatched.map(card => this.cardTemplate(card)).join('')}
          `}
        </section>

        <section class="worksDrop" data-over="false" ${cards.length === 0 ? 'hidden' : ''}>
          <div class="dropGlyph">⇣</div>
          <strong>NEW WORKSTATION · HUMAN DISPATCH</strong>
          <span>Human Approval → atomic publish → Workstation registration</span>
        </section>

        <footer class="footer">
          <span>未発注 <strong data-role="staged-count">${staged.length}</strong></span>
          <span>発注済み <strong data-role="dispatched-count">${dispatched.length}</strong></span>
          <span>清算済み <strong data-role="settled-count">${settled.length}</strong></span>
          <span class="selectionCount" data-role="selection-count" ${this.selectedCardIds.size === 0 ? 'hidden' : ''}>選択 ${this.selectedCardIds.size}</span>
        </footer>

        <dialog class="removeDialog" data-role="remove-dialog">
          <div class="removeDialogPanel">
            <div class="removeDialogEyebrow">HUMAN GATE · DISPATCH BAY</div>
            <div class="removeDialogHeading" data-role="remove-dialog-heading">発注カードを削除しますか？</div>
            <div class="removeDialogTitle" data-role="remove-dialog-title">VRA</div>
            <div class="removeDialogNote">Dispatch Bayのカード表示だけを削除します。WorkstationのJobや実行は取り消されません。</div>
            <div class="removeDialogActions">
              <button type="button" class="dialogCancel" data-action="remove-cancel">キャンセル</button>
              <button type="button" class="removeConfirm" data-action="remove-confirm">削除する</button>
            </div>
          </div>
        </dialog>
      </aside>
    `
    this.bind()
  }

  // VERTEX_CARD_ERROR_COPY_000033V2
  private errorCopyListenerInstalled = false

  private hasCopyableCardError(card: VraDispatchCard): boolean {
    const raw = card as unknown as Record<string, unknown>
    const jobState = String(raw.workstationJobState ?? '')
    const registration = String(raw.workstationRegistration ?? '')
    return Boolean(
      raw.error ||
      raw.workstationLastError ||
      raw.status === 'ERROR' ||
      registration === 'BLOCKED' ||
      jobState === 'FAILED' ||
      jobState === 'REJECTED' ||
      jobState === 'ROLLED_BACK'
    )
  }

  private readonly handleErrorCopyClick = (event: Event): void => {
    const origin = event.target instanceof Element ? event.target : null
    const button = origin?.closest<HTMLButtonElement>('[data-error-copy-card]')
    if (!button || !this.contains(button)) return

    event.preventDefault()
    event.stopPropagation()

    const cardId = button.dataset.errorCopyCard ?? ''
    const card = this.state?.cards.find(candidate => candidate.id === cardId)
    if (!card) return

    void this.copyCardErrorForVera(card, button)
  }

  private cardErrorTextForVera(card: VraDispatchCard): string {
    const raw = card as unknown as Record<string, unknown>
    const value = (key: string): string => {
      const current = raw[key]
      return current === null || current === undefined || current === '' ? '-' : String(current)
    }

    return [
      '[VERTEX VRA CARD ERROR]',
      `artifact_id=${value('artifactId')}`,
      `job_id=${value('jobId')}`,
      `correlation_id=${value('correlationId')}`,
      `origin_vera=${value('originVera')}`,
      `origin_session=${value('originSession')}`,
      `origin_window=${value('originWindow')}`,
      `project_id=${value('projectId')}`,
      `project_name=${value('projectName')}`,
      '',
      `card_status=${value('status')}`,
      `dispatch_phase=${value('dispatchPhase')}`,
      `human_approval=${value('humanApproval')}`,
      `workstation_registration=${value('workstationRegistration')}`,
      `workstation_job_state=${value('workstationJobState')}`,
      `workstation_evidence_state=${value('workstationEvidenceState')}`,
      `workstation_evidence_return_state=${value('workstationEvidenceReturnState')}`,
      `allocated_lane=${value('allocatedLane')}`,
      `evidence_id=${value('evidenceIdentity')}`,
      '',
      `error=${value('error')}`,
      `workstation_last_error=${value('workstationLastError')}`
    ].join('\n')
  }

  private async copyCardErrorForVera(card: VraDispatchCard, button: HTMLButtonElement): Promise<void> {
    const text = this.cardErrorTextForVera(card)
    let copied = false

    try {
      await navigator.clipboard.writeText(text)
      copied = true
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.left = '-10000px'
      textarea.style.top = '0'
      document.body.appendChild(textarea)
      textarea.select()
      copied = document.execCommand('copy')
      textarea.remove()
    }

    const previous = button.textContent
    button.textContent = copied ? 'OK' : 'ERR'
    button.dataset.copyState = copied ? 'COPIED' : 'FAILED'
    window.setTimeout(() => {
      if (!button.isConnected) return
      button.textContent = previous || 'COPY'
      delete button.dataset.copyState
    }, 1200)
  }

  // VERTEX_EVIDENCE_LIFECYCLE_CARD_000043V2
  // Compact semantic projection only: no card/container dimensions are changed.
  private evidenceLifecycleEvidenceText(card: VraDispatchCard): string {
    const raw = card as unknown as Record<string, unknown>
    const state = String(raw.workstationEvidenceState ?? '').trim().toUpperCase()

    if (state === 'AVAILABLE') return '● AVAILABLE'
    if (!state || state === 'NONE' || state === 'UNKNOWN') return '○ WAITING'
    return `◉ ${state}`
  }

  private evidenceLifecycleReturnText(card: VraDispatchCard): string {
    const raw = card as unknown as Record<string, unknown>
    const state = String(raw.workstationEvidenceReturnState ?? '').trim().toUpperCase()

    // Contract semantics:
    // RETURN_QUEUED = transport/ack workflow still open; chat may already be visible.
    // RETURNED = configured return workflow completion/ack, not proof a human read it.
    if (state === 'RETURNED') return '● PORTAL ACK'
    if (state === 'RETURN_QUEUED') return '◉ RETURN QUEUE'
    if (!state || state === 'NONE' || state === 'UNKNOWN') return '○ RETURN'
    return `◉ ${state}`
  }

}

customElements.define('vertex-vra-dispatch-lane', VraDispatchLane)
