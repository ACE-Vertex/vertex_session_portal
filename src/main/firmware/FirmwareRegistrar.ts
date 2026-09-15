import { createHash, createHmac, randomBytes } from 'node:crypto'
import {
  appendFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  writeFileSync
} from 'node:fs'
import { join } from 'node:path'
import { app } from 'electron'

export type FirmwareRisk = 'GREEN' | 'AMBER' | 'RED'
export type FirmwareDecision = 'APPROVE' | 'REJECT'

export type FirmwareDecisionRequest = {
  requestId: string
  decision: FirmwareDecision
  decisionId: string
  decidedAt: string
  target: string
  currentVersion?: string
  proposedVersion: string
  source?: {
    actor?: string
    model?: string
    session?: string
    reason?: string
  }
  risk: FirmwareRisk
  compatibility?: string
  migration?: string
  changes?: unknown[]
  validation?: Array<{
    label?: string
    status?: 'PASS' | 'WARN' | 'FAIL'
    detail?: string
  }>
  impact?: unknown[]
  redConfirmed: boolean
}

export type FirmwareRegistrarResult = {
  accepted: boolean
  committed: boolean
  idempotent: boolean
  decisionId: string
  requestId: string
  target: string
  proposedVersion: string
  registryState: 'APPROVED' | 'REJECTED' | 'UNCHANGED'
  approvalRecordHash: string
  journalEntryHash: string
}

type FirmwareRegistryEntry = {
  target: string
  version: string
  requestId: string
  decisionId: string
  approvedAt: string
  approvalRecordHash: string
}

type FirmwareRegistryState = {
  schema: 'vertex-firmware/registry-1'
  updatedAt: string
  entries: Record<string, FirmwareRegistryEntry>
}

type SignedApprovalRecord = {
  schema: 'vertex-firmware/signed-approval-record-1'
  authority: 'HUMAN_GATE'
  requestId: string
  decision: FirmwareDecision
  decisionId: string
  decidedAt: string
  recordedAt: string
  target: string
  currentVersion?: string
  proposedVersion: string
  source?: FirmwareDecisionRequest['source']
  risk: FirmwareRisk
  compatibility?: string
  migration?: string
  changes?: unknown[]
  validation?: FirmwareDecisionRequest['validation']
  impact?: unknown[]
  redConfirmed: boolean
  signatureAlgorithm: 'HMAC-SHA256'
  signature: string
  recordHash: string
}

type JournalEntry = {
  schema: 'vertex-firmware/registry-journal-1'
  event: 'REGISTRY_COMMIT' | 'DECISION_REJECTED'
  recordedAt: string
  requestId: string
  decisionId: string
  target: string
  proposedVersion: string
  approvalRecordHash: string
  previousHash: string | null
  entryHash: string
}

function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([, item]) => item !== undefined)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, stable(item)])
    )
  }
  return value
}

function canonicalJson(value: unknown): string {
  return JSON.stringify(stable(value))
}

function sha256(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex')
}

function cleanString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

function normalizeDecision(value: unknown): FirmwareDecisionRequest {
  if (!value || typeof value !== 'object') {
    throw new Error('Firmware decision payload must be an object.')
  }

  const raw = value as Record<string, unknown>
  const decision = cleanString(raw.decision).toUpperCase()
  const risk = cleanString(raw.risk).toUpperCase()

  if (decision !== 'APPROVE' && decision !== 'REJECT') {
    throw new Error('Firmware decision must be APPROVE or REJECT.')
  }
  if (risk !== 'GREEN' && risk !== 'AMBER' && risk !== 'RED') {
    throw new Error('Firmware risk must be GREEN, AMBER, or RED.')
  }

  const requestId = cleanString(raw.requestId)
  const decisionId = cleanString(raw.decisionId)
  const decidedAt = cleanString(raw.decidedAt)
  const target = cleanString(raw.target)
  const proposedVersion = cleanString(raw.proposedVersion)
  const currentVersion = cleanString(raw.currentVersion) || undefined

  if (!requestId || !decisionId || !decidedAt || !target || !proposedVersion) {
    throw new Error('Firmware decision identity/version fields are incomplete.')
  }

  const sourceRaw = raw.source && typeof raw.source === 'object'
    ? raw.source as Record<string, unknown>
    : undefined

  const source = sourceRaw
    ? {
        actor: cleanString(sourceRaw.actor) || undefined,
        model: cleanString(sourceRaw.model) || undefined,
        session: cleanString(sourceRaw.session) || undefined,
        reason: cleanString(sourceRaw.reason) || undefined
      }
    : undefined

  const validation = Array.isArray(raw.validation)
    ? raw.validation.map(item => {
        const row = item && typeof item === 'object' ? item as Record<string, unknown> : {}
        const statusRaw = cleanString(row.status).toUpperCase()
        const status: 'PASS' | 'WARN' | 'FAIL' | undefined =
          statusRaw === 'PASS' || statusRaw === 'WARN' || statusRaw === 'FAIL'
            ? statusRaw
            : undefined
        return {
          label: cleanString(row.label) || undefined,
          status,
          detail: cleanString(row.detail) || undefined
        }
      })
    : undefined

  return {
    requestId,
    decision: decision as FirmwareDecision,
    decisionId,
    decidedAt,
    target,
    currentVersion,
    proposedVersion,
    source,
    risk: risk as FirmwareRisk,
    compatibility: cleanString(raw.compatibility) || undefined,
    migration: cleanString(raw.migration) || undefined,
    changes: Array.isArray(raw.changes) ? raw.changes : undefined,
    validation,
    impact: Array.isArray(raw.impact) ? raw.impact : undefined,
    redConfirmed: raw.redConfirmed === true
  }
}

export class FirmwareRegistrar {
  private root(): string {
    return join(app.getPath('userData'), 'vra-registry', 'firmware')
  }

  private ensureRoot(): string {
    const root = this.root()
    mkdirSync(root, { recursive: true })
    return root
  }

  private key(): Buffer {
    const root = this.ensureRoot()
    const keyPath = join(root, 'firmware-registrar.key')
    if (!existsSync(keyPath)) {
      try {
        writeFileSync(keyPath, randomBytes(32), { flag: 'wx' })
      } catch (error) {
        if (!existsSync(keyPath)) throw error
      }
    }
    return readFileSync(keyPath)
  }

  private registryPath(): string {
    return join(this.ensureRoot(), 'firmware-registry.json')
  }

  private approvalPath(): string {
    return join(this.ensureRoot(), 'signed-approval-records.jsonl')
  }

  private journalPath(): string {
    return join(this.ensureRoot(), 'firmware-registry-journal.jsonl')
  }

  private loadRegistry(): FirmwareRegistryState {
    const path = this.registryPath()
    if (!existsSync(path)) {
      return {
        schema: 'vertex-firmware/registry-1',
        updatedAt: new Date(0).toISOString(),
        entries: {}
      }
    }
    const parsed = JSON.parse(readFileSync(path, 'utf8')) as FirmwareRegistryState
    if (parsed.schema !== 'vertex-firmware/registry-1' || !parsed.entries) {
      throw new Error('Firmware Registry schema is invalid.')
    }
    return parsed
  }

  private atomicWriteRegistry(state: FirmwareRegistryState): void {
    const path = this.registryPath()
    const temp = `${path}.tmp-${process.pid}-${Date.now()}`
    writeFileSync(temp, `${JSON.stringify(state, null, 2)}\n`, 'utf8')
    renameSync(temp, path)
  }

  private previousJournalHash(): string | null {
    const path = this.journalPath()
    if (!existsSync(path)) return null
    const lines = readFileSync(path, 'utf8').split(/\r?\n/).filter(Boolean)
    if (!lines.length) return null
    try {
      const last = JSON.parse(lines[lines.length - 1]) as { entryHash?: string }
      return cleanString(last.entryHash) || null
    } catch {
      throw new Error('Firmware Registry journal tail is invalid.')
    }
  }

  private findDecision(decisionId: string): SignedApprovalRecord | null {
    const path = this.approvalPath()
    if (!existsSync(path)) return null
    for (const line of readFileSync(path, 'utf8').split(/\r?\n/).filter(Boolean)) {
      try {
        const record = JSON.parse(line) as SignedApprovalRecord
        if (record.decisionId === decisionId) return record
      } catch {
        throw new Error('Signed Approval Record journal is invalid.')
      }
    }
    return null
  }

  private signDecision(decision: FirmwareDecisionRequest): SignedApprovalRecord {
    const unsigned = {
      schema: 'vertex-firmware/signed-approval-record-1' as const,
      authority: 'HUMAN_GATE' as const,
      requestId: decision.requestId,
      decision: decision.decision,
      decisionId: decision.decisionId,
      decidedAt: decision.decidedAt,
      recordedAt: new Date().toISOString(),
      target: decision.target,
      currentVersion: decision.currentVersion,
      proposedVersion: decision.proposedVersion,
      source: decision.source,
      risk: decision.risk,
      compatibility: decision.compatibility,
      migration: decision.migration,
      changes: decision.changes,
      validation: decision.validation,
      impact: decision.impact,
      redConfirmed: decision.redConfirmed,
      signatureAlgorithm: 'HMAC-SHA256' as const
    }
    const signature = createHmac('sha256', this.key())
      .update(canonicalJson(unsigned), 'utf8')
      .digest('hex')
    const recordWithoutHash = { ...unsigned, signature }
    const recordHash = sha256(canonicalJson(recordWithoutHash))
    return { ...recordWithoutHash, recordHash }
  }

  private appendApproval(record: SignedApprovalRecord): void {
    appendFileSync(this.approvalPath(), `${JSON.stringify(record)}\n`, 'utf8')
  }

  private appendJournal(
    event: JournalEntry['event'],
    decision: FirmwareDecisionRequest,
    approvalRecordHash: string
  ): JournalEntry {
    const base = {
      schema: 'vertex-firmware/registry-journal-1' as const,
      event,
      recordedAt: new Date().toISOString(),
      requestId: decision.requestId,
      decisionId: decision.decisionId,
      target: decision.target,
      proposedVersion: decision.proposedVersion,
      approvalRecordHash,
      previousHash: this.previousJournalHash()
    }
    const entry: JournalEntry = {
      ...base,
      entryHash: sha256(canonicalJson(base))
    }
    appendFileSync(this.journalPath(), `${JSON.stringify(entry)}\n`, 'utf8')
    return entry
  }

  private assertDeterministicValidation(decision: FirmwareDecisionRequest): void {
    if (decision.decision !== 'APPROVE') return

    const validation = decision.validation ?? []
    if (!validation.length) {
      throw new Error('APPROVE requires deterministic validator evidence.')
    }
    if (validation.some(item => item.status !== 'PASS')) {
      throw new Error('APPROVE denied because validator evidence is not all PASS.')
    }
    if (decision.risk === 'RED' && !decision.redConfirmed) {
      throw new Error('RED firmware approval requires the second Human confirmation.')
    }
  }

  register(value: unknown): FirmwareRegistrarResult {
    const decision = normalizeDecision(value)
    this.assertDeterministicValidation(decision)

    const existingDecision = this.findDecision(decision.decisionId)
    if (existingDecision) {
      const same =
        existingDecision.requestId === decision.requestId
        && existingDecision.decision === decision.decision
        && existingDecision.target === decision.target
        && existingDecision.proposedVersion === decision.proposedVersion
      if (!same) {
        throw new Error('decisionId collision with different firmware decision content.')
      }
      const registry = this.loadRegistry()
      const committed = registry.entries[decision.target]?.decisionId === decision.decisionId
      return {
        accepted: true,
        committed,
        idempotent: true,
        decisionId: decision.decisionId,
        requestId: decision.requestId,
        target: decision.target,
        proposedVersion: decision.proposedVersion,
        registryState: decision.decision === 'REJECT'
          ? 'REJECTED'
          : committed ? 'APPROVED' : 'UNCHANGED',
        approvalRecordHash: existingDecision.recordHash,
        journalEntryHash: this.previousJournalHash() ?? ''
      }
    }

    const record = this.signDecision(decision)
    this.appendApproval(record)

    if (decision.decision === 'REJECT') {
      const journal = this.appendJournal('DECISION_REJECTED', decision, record.recordHash)
      return {
        accepted: true,
        committed: false,
        idempotent: false,
        decisionId: decision.decisionId,
        requestId: decision.requestId,
        target: decision.target,
        proposedVersion: decision.proposedVersion,
        registryState: 'REJECTED',
        approvalRecordHash: record.recordHash,
        journalEntryHash: journal.entryHash
      }
    }

    const path = this.registryPath()
    const previousBytes = existsSync(path) ? readFileSync(path) : null
    const registry = this.loadRegistry()
    const current = registry.entries[decision.target]

    if (decision.currentVersion !== undefined) {
      const actualCurrent = current?.version ?? ''
      if (actualCurrent !== decision.currentVersion) {
        throw new Error(
          `Firmware Registry version conflict for ${decision.target}: `
          + `expected=${decision.currentVersion} actual=${actualCurrent || '<none>'}`
        )
      }
    }

    const updatedAt = new Date().toISOString()
    const next: FirmwareRegistryState = {
      schema: 'vertex-firmware/registry-1',
      updatedAt,
      entries: {
        ...registry.entries,
        [decision.target]: {
          target: decision.target,
          version: decision.proposedVersion,
          requestId: decision.requestId,
          decisionId: decision.decisionId,
          approvedAt: updatedAt,
          approvalRecordHash: record.recordHash
        }
      }
    }

    this.atomicWriteRegistry(next)

    let journal: JournalEntry
    try {
      journal = this.appendJournal('REGISTRY_COMMIT', decision, record.recordHash)
    } catch (error) {
      if (previousBytes) {
        writeFileSync(path, previousBytes)
      } else {
        rmSync(path, { force: true })
      }
      throw error
    }

    return {
      accepted: true,
      committed: true,
      idempotent: false,
      decisionId: decision.decisionId,
      requestId: decision.requestId,
      target: decision.target,
      proposedVersion: decision.proposedVersion,
      registryState: 'APPROVED',
      approvalRecordHash: record.recordHash,
      journalEntryHash: journal.entryHash
    }
  }
}
