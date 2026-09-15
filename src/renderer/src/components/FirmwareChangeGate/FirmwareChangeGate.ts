import { escapeHtml } from '../../shared/escape'
import styles from './FirmwareChangeGate.css?inline'

// 000151V3R2: exactOptionalPropertyTypes-safe approval packet model.

const REQUEST_EVENT = 'vertex:firmware-change-request'
const CLEAR_EVENT = 'vertex:firmware-change-clear'
const DECISION_EVENT = 'vertex:firmware-change-decision'
const INSPECT_EVENT = 'vertex:firmware-change-inspect'
const CACHE_KEY = 'vertex.firmware-change-gate.pending.v1'

type FirmwareRisk = 'GREEN' | 'AMBER' | 'RED'
type FirmwareDecision = 'APPROVE' | 'REJECT'

type FirmwareFieldChange = {
  op?: string
  name?: string
  type?: string
  default?: unknown
  required?: boolean
  detail?: string
}

type FirmwareValidation = {
  label?: string
  status?: 'PASS' | 'WARN' | 'FAIL'
  detail?: string
}

type FirmwareImpact = {
  surface?: string
  level?: 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH'
  detail?: string
}

type FirmwareSource = {
  actor?: string | undefined
  model?: string | undefined
  session?: string | undefined
  reason?: string | undefined
}

export type FirmwareChangeRequest = {
  requestId: string
  source?: FirmwareSource | undefined
  target: string
  currentVersion?: string | undefined
  proposedVersion: string
  risk?: FirmwareRisk
  compatibility?: string | undefined
  migration?: string | undefined
  changeSummary?: string | undefined
  changes?: FirmwareFieldChange[] | undefined
  validation?: FirmwareValidation[] | undefined
  impact?: FirmwareImpact[] | undefined
  submittedAt?: string | undefined
}

type FirmwareDecisionDetail = {
  requestId: string
  decision: FirmwareDecision
  decisionId: string
  decidedAt: string
  target: string
  currentVersion?: string | undefined
  proposedVersion: string
  source?: FirmwareSource | undefined
  risk: FirmwareRisk
  compatibility?: string | undefined
  migration?: string | undefined
  changes?: FirmwareFieldChange[] | undefined
  validation?: FirmwareValidation[] | undefined
  impact?: FirmwareImpact[] | undefined
  redConfirmed: boolean
}

function normalizeRisk(value: unknown): FirmwareRisk {
  const upper = String(value ?? '').toUpperCase()
  if (upper === 'RED' || upper === 'AMBER') return upper
  return 'GREEN'
}

function safeArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

function normalizeRequest(value: unknown): FirmwareChangeRequest | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  const requestId = String(raw.requestId ?? raw.request_id ?? '').trim()
  const target = String(raw.target ?? raw.namespace ?? '').trim()
  const proposedVersion = String(raw.proposedVersion ?? raw.proposed_version ?? '').trim()
  if (!requestId || !target || !proposedVersion) return null

  const sourceRaw = raw.source && typeof raw.source === 'object'
    ? raw.source as Record<string, unknown>
    : {}

  return {
    requestId,
    target,
    proposedVersion,
    currentVersion: String(raw.currentVersion ?? raw.current_version ?? '').trim() || undefined,
    risk: normalizeRisk(raw.risk),
    compatibility: String(raw.compatibility ?? '').trim() || undefined,
    migration: String(raw.migration ?? '').trim() || undefined,
    changeSummary: String(raw.changeSummary ?? raw.change_summary ?? '').trim() || undefined,
    submittedAt: String(raw.submittedAt ?? raw.submitted_at ?? '').trim() || undefined,
    source: {
      actor: String(sourceRaw.actor ?? '').trim() || undefined,
      model: String(sourceRaw.model ?? '').trim() || undefined,
      session: String(sourceRaw.session ?? '').trim() || undefined,
      reason: String(sourceRaw.reason ?? '').trim() || undefined
    },
    changes: safeArray<FirmwareFieldChange>(raw.changes),
    validation: safeArray<FirmwareValidation>(raw.validation),
    impact: safeArray<FirmwareImpact>(raw.impact)
  }
}

function makeDecisionId(): string {
  const random = Math.random().toString(36).slice(2, 10)
  return `fw-decision-${Date.now().toString(36)}-${random}`
}

/**
 * Human-facing approval surface only.
 *
 * This component MUST NOT write Firmware Registry state directly.
 * It emits deterministic DOM events that a separately-authorized registrar
 * may consume after policy validation.
 */
export class FirmwareChangeGate extends HTMLElement {
  private queue: FirmwareChangeRequest[] = []
  private index = 0
  private redArmedRequestId = ''

  connectedCallback(): void {
    if (!this.shadowRoot) this.attachShadow({ mode: 'open' })
    this.queue = this.loadCache()
    this.render()
    window.addEventListener(REQUEST_EVENT, this.handleRequest as EventListener)
    window.addEventListener(CLEAR_EVENT, this.handleClear as EventListener)
  }

  disconnectedCallback(): void {
    window.removeEventListener(REQUEST_EVENT, this.handleRequest as EventListener)
    window.removeEventListener(CLEAR_EVENT, this.handleClear as EventListener)
  }

  private handleRequest = (event: Event): void => {
    const request = normalizeRequest((event as CustomEvent<unknown>).detail)
    if (!request) return

    const existing = this.queue.findIndex(item => item.requestId === request.requestId)
    if (existing >= 0) {
      this.queue[existing] = request
      this.index = existing
    } else {
      this.queue.push(request)
      this.index = this.queue.length - 1
    }
    this.redArmedRequestId = ''
    this.persistCache()
    this.render()
  }

  private handleClear = (event: Event): void => {
    const detail = (event as CustomEvent<unknown>).detail
    const requestId = typeof detail === 'string'
      ? detail
      : detail && typeof detail === 'object'
        ? String((detail as Record<string, unknown>).requestId ?? '')
        : ''

    if (!requestId) {
      this.queue = []
      this.index = 0
    } else {
      this.queue = this.queue.filter(item => item.requestId !== requestId)
      this.index = Math.max(0, Math.min(this.index, this.queue.length - 1))
    }
    this.redArmedRequestId = ''
    this.persistCache()
    this.render()
  }

  private loadCache(): FirmwareChangeRequest[] {
    try {
      const raw = localStorage.getItem(CACHE_KEY)
      if (!raw) return []
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return []
      return parsed.map(normalizeRequest).filter((item): item is FirmwareChangeRequest => Boolean(item))
    } catch {
      return []
    }
  }

  private persistCache(): void {
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(this.queue))
    } catch {
      // Display cache failure must never grant or deny authority.
    }
  }

  private emitDecision(request: FirmwareChangeRequest, decision: FirmwareDecision): void {
    const detail: FirmwareDecisionDetail = {
      requestId: request.requestId,
      decision,
      decisionId: makeDecisionId(),
      decidedAt: new Date().toISOString(),
      target: request.target,
      currentVersion: request.currentVersion,
      proposedVersion: request.proposedVersion,
      source: request.source,
      risk: normalizeRisk(request.risk),
      compatibility: request.compatibility,
      migration: request.migration,
      changes: request.changes,
      validation: request.validation,
      impact: request.impact,
      redConfirmed: normalizeRisk(request.risk) !== 'RED'
        || this.redArmedRequestId === request.requestId
    }

    window.dispatchEvent(new CustomEvent<FirmwareDecisionDetail>(DECISION_EVENT, { detail }))
    this.queue = this.queue.filter(item => item.requestId !== request.requestId)
    this.index = Math.max(0, Math.min(this.index, this.queue.length - 1))
    this.redArmedRequestId = ''
    this.persistCache()
    this.render()
  }

  private emitInspect(request: FirmwareChangeRequest): void {
    window.dispatchEvent(new CustomEvent(INSPECT_EVENT, {
      detail: {
        requestId: request.requestId,
        target: request.target,
        currentVersion: request.currentVersion,
        proposedVersion: request.proposedVersion
      }
    }))
    void (window as unknown as { vertexPortal: { submitSystemPolicyDecision: (decision: unknown) => Promise<unknown> } }).vertexPortal.submitSystemPolicyDecision({
        requestId: request.requestId,
        target: request.target,
        currentVersion: request.currentVersion,
        proposedVersion: request.proposedVersion
      })
  }

  private bindActions(request?: FirmwareChangeRequest): void {
    const root = this.shadowRoot
    if (!root) return

    root.querySelector('[data-action="prev"]')?.addEventListener('click', () => {
      if (!this.queue.length) return
      this.index = (this.index - 1 + this.queue.length) % this.queue.length
      this.redArmedRequestId = ''
      this.render()
    })

    root.querySelector('[data-action="next"]')?.addEventListener('click', () => {
      if (!this.queue.length) return
      this.index = (this.index + 1) % this.queue.length
      this.redArmedRequestId = ''
      this.render()
    })

    if (!request) return

    root.querySelector('[data-action="inspect"]')?.addEventListener('click', () => {
      this.emitInspect(request)
    })

    root.querySelector('[data-action="reject"]')?.addEventListener('click', () => {
      this.emitDecision(request, 'REJECT')
    })

    root.querySelector('[data-action="approve"]')?.addEventListener('click', () => {
      if (request.risk === 'RED' && this.redArmedRequestId !== request.requestId) {
        this.redArmedRequestId = request.requestId
        this.render()
        return
      }
      this.emitDecision(request, 'APPROVE')
    })
  }

  private renderChanges(request: FirmwareChangeRequest): string {
    const rows = request.changes ?? []
    if (!rows.length) {
      return `<div class="emptyLine">${escapeHtml(request.changeSummary ?? 'No structured change rows supplied.')}</div>`
    }

    return rows.map(change => {
      const op = escapeHtml(String(change.op ?? 'CHANGE').toUpperCase())
      const name = escapeHtml(String(change.name ?? 'unnamed'))
      const type = change.type ? ` : ${escapeHtml(change.type)}` : ''
      const required = change.required === undefined ? '' : ` · required=${change.required ? 'true' : 'false'}`
      const detail = change.detail ? `<div class="rowDetail">${escapeHtml(change.detail)}</div>` : ''
      return `
        <div class="changeRow">
          <span class="op">${op}</span>
          <span class="changeName">${name}${type}${required}</span>
          ${detail}
        </div>
      `
    }).join('')
  }

  private renderValidation(request: FirmwareChangeRequest): string {
    const rows = request.validation ?? []
    if (!rows.length) {
      return `<div class="emptyLine">Awaiting deterministic validator evidence.</div>`
    }

    return rows.map(item => {
      const status = String(item.status ?? 'WARN').toUpperCase()
      const statusClass = status === 'PASS' ? 'pass' : status === 'FAIL' ? 'fail' : 'warn'
      return `
        <div class="statusRow">
          <span class="statusMark ${statusClass}">${status === 'PASS' ? '✓' : status === 'FAIL' ? '×' : '!'}</span>
          <span>${escapeHtml(item.label ?? 'Validation')}</span>
          <span class="statusValue">${escapeHtml(status)}</span>
        </div>
      `
    }).join('')
  }

  private renderImpact(request: FirmwareChangeRequest): string {
    const rows = request.impact ?? []
    if (!rows.length) {
      return `<div class="emptyLine">Impact analysis not attached.</div>`
    }

    return rows.map(item => `
      <div class="impactRow">
        <span>${escapeHtml(item.surface ?? 'Unknown')}</span>
        <span class="impactLevel level-${escapeHtml(String(item.level ?? 'LOW').toLowerCase())}">
          ${escapeHtml(String(item.level ?? 'LOW').toUpperCase())}
        </span>
      </div>
    `).join('')
  }

  private render(): void {
    const root = this.shadowRoot
    if (!root) return

    const request = this.queue[this.index]
    const countText = this.queue.length ? `${this.index + 1}/${this.queue.length}` : '0 PENDING'

    if (!request) {
      root.innerHTML = `
        <style>${styles}</style>
        <section class="gate ready">
          <header class="titlebar">
            <div>
              <div class="eyebrow">SYSTEM AUTHORITY / HUMAN GATE</div>
              <h2>FIRMWARE CHANGE GATE</h2>
            </div>
            <span class="readyBadge">FW READY</span>
          </header>
          <div class="readyBody">
            <div class="readyGlyph">✓</div>
            <div class="readyTitle">NO PENDING CHANGE REQUESTS</div>
            <div class="readyCopy">Firmware proposals will appear here only after machine validation prepares a Human review packet.</div>
            <div class="boundary">GUI = approval surface · Registry writes = external authorized registrar only</div>
          </div>
        </section>
      `
      this.bindActions()
      return
    }

    const risk = normalizeRisk(request.risk)
    const source = request.source ?? {}
    const redArmed = risk === 'RED' && this.redArmedRequestId === request.requestId
    const approveText = redArmed ? 'FINAL COMMIT' : risk === 'RED' ? 'ARM RED APPROVAL' : 'APPROVE'

    root.innerHTML = `
      <style>${styles}</style>
      <section class="gate">
        <header class="titlebar">
          <div>
            <div class="eyebrow">SYSTEM AUTHORITY / HUMAN GATE</div>
            <h2>FIRMWARE CHANGE GATE</h2>
          </div>
          <span class="risk risk-${risk.toLowerCase()}">${risk}</span>
        </header>

        <div class="queuebar">
          <button class="nav" data-action="prev" ${this.queue.length < 2 ? 'disabled' : ''}>‹</button>
          <span>${escapeHtml(countText)}</span>
          <span class="requestId">${escapeHtml(request.requestId)}</span>
          <button class="nav" data-action="next" ${this.queue.length < 2 ? 'disabled' : ''}>›</button>
        </div>

        <div class="scroll">
          <section class="section">
            <div class="sectionTitle">SOURCE</div>
            <div class="kv"><span>ACTOR</span><strong>${escapeHtml(source.actor ?? 'UNRESOLVED')}</strong></div>
            <div class="kv"><span>MODEL</span><strong>${escapeHtml(source.model ?? 'UNRESOLVED')}</strong></div>
            <div class="kv"><span>SESSION</span><strong>${escapeHtml(source.session ?? 'UNRESOLVED')}</strong></div>
            ${source.reason ? `<div class="reason">${escapeHtml(source.reason)}</div>` : ''}
          </section>

          <section class="section">
            <div class="sectionTitle">TARGET</div>
            <div class="target">${escapeHtml(request.target)}</div>
            <div class="versionFlow">
              <span>${escapeHtml(request.currentVersion ?? 'NEW')}</span>
              <span class="arrow">→</span>
              <strong>${escapeHtml(request.proposedVersion)}</strong>
            </div>
            ${request.compatibility ? `<div class="metaLine">COMPATIBILITY · ${escapeHtml(request.compatibility)}</div>` : ''}
            ${request.migration ? `<div class="metaLine">MIGRATION · ${escapeHtml(request.migration)}</div>` : ''}
          </section>

          <section class="section">
            <div class="sectionTitle">CHANGE</div>
            ${this.renderChanges(request)}
          </section>

          <section class="section">
            <div class="sectionTitle">DETERMINISTIC VALIDATION</div>
            ${this.renderValidation(request)}
          </section>

          <section class="section">
            <div class="sectionTitle">IMPACT</div>
            ${this.renderImpact(request)}
          </section>

          ${redArmed ? `
            <section class="redConfirm">
              <strong>RED CHANGE ARMED</strong>
              <span>Second Human action is required. FINAL COMMIT emits approval; it still does not write the Firmware Registry directly.</span>
            </section>
          ` : ''}
        </div>

        <footer class="actions">
          <button class="button reject" data-action="reject">REJECT</button>
          <button class="button inspect" data-action="inspect">DEEP RAY</button>
          <button class="button approve risk-${risk.toLowerCase()}" data-action="approve">${approveText}</button>
        </footer>
      </section>
    `
    this.bindActions(request)
  }
}

if (!customElements.get('vertex-firmware-change-gate')) {
  customElements.define('vertex-firmware-change-gate', FirmwareChangeGate)
}
