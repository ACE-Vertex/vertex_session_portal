import { app } from 'electron'
import { createHash, createHmac, randomBytes } from 'node:crypto'
import { appendFileSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

export type SystemPolicyDecision = {
  decision: 'APPROVE' | 'REJECT'
  target: string
  currentVersion?: string | null
  proposedVersion: string
  validation: unknown
  impact?: unknown
  risk?: unknown
  compatibility?: unknown
  migration?: unknown
  changes?: unknown
  source?: unknown
  redConfirmed?: boolean
  decisionId?: string
  decidedAt?: string
  [key: string]: unknown
}

export type SystemPolicyRegistrarResult =
  | { ok: true; committed: boolean; idempotent?: boolean; target: string; version?: string }
  | { ok: false; committed: false; code: string; message: string }

type ActiveRecord = {
  schema: 'vertex-system-policy/active-1'
  target: string
  version: string
  committedAt: string
  lastDecisionId: string
  policy: SystemPolicyDecision
}

function stable(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']'
  const obj = value as Record<string, unknown>
  return '{' + Object.keys(obj).sort().map((k) => JSON.stringify(k) + ':' + stable(obj[k])).join(',') + '}'
}

function sha256(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex')
}

function safeTarget(target: string): string {
  const s = target.trim().replace(/[^A-Za-z0-9._-]+/g, '_')
  return s || 'default'
}

function validationPass(value: unknown): boolean {
  if (typeof value === 'string') return value.trim().toUpperCase() === 'PASS'
  if (!value || typeof value !== 'object') return false
  const obj = value as Record<string, unknown>
  for (const key of ['result', 'status', 'state', 'verdict']) {
    const v = obj[key]
    if (typeof v === 'string' && v.trim().toUpperCase() === 'PASS') return true
  }
  return false
}

function requiresRedConfirmation(decision: SystemPolicyDecision): boolean {
  const values = [decision.risk, decision.impact]
  return values.some((value) => {
    if (typeof value === 'string') {
      const v = value.trim().toUpperCase()
      return v === 'RED' || v === 'CRITICAL'
    }
    if (value && typeof value === 'object') {
      const obj = value as Record<string, unknown>
      return ['level', 'risk', 'severity', 'classification'].some((key) => {
        const v = obj[key]
        return typeof v === 'string' && ['RED', 'CRITICAL'].includes(v.trim().toUpperCase())
      })
    }
    return false
  })
}

export class SystemPolicyRegistrar {
  private baseDir(): string {
    return join(app.getPath('userData'), 'vra-registry', 'system-policy')
  }

  private ensureBase(): string {
    const dir = this.baseDir()
    mkdirSync(dir, { recursive: true })
    return dir
  }

  private signingKey(): string {
    const dir = this.ensureBase()
    const p = join(dir, '.signing-key')
    if (!existsSync(p)) {
      writeFileSync(p, randomBytes(32).toString('hex'), { encoding: 'utf8', flag: 'wx' })
    }
    return readFileSync(p, 'utf8').trim()
  }

  private registryPath(target: string): string {
    return join(this.ensureBase(), safeTarget(target) + '.json')
  }

  private approvalPath(): string {
    return join(this.ensureBase(), 'signed-policy-approvals.jsonl')
  }

  private journalPath(): string {
    return join(this.ensureBase(), 'policy-journal.jsonl')
  }

  private readActive(target: string): ActiveRecord | null {
    const p = this.registryPath(target)
    if (!existsSync(p)) return null
    return JSON.parse(readFileSync(p, 'utf8')) as ActiveRecord
  }

  readActivePolicy(target: string): ActiveRecord | null {
    if (typeof target !== 'string' || !target.trim()) return null
    return this.readActive(target)
  }

  private appendJournal(event: Record<string, unknown>): void {
    const p = this.journalPath()
    let previousHash = 'GENESIS'
    if (existsSync(p)) {
      const lines = readFileSync(p, 'utf8').split(/\r?\n/).filter(Boolean)
      if (lines.length) {
        const last = JSON.parse(lines[lines.length - 1]) as Record<string, unknown>
        if (typeof last.entryHash === 'string') previousHash = last.entryHash
      }
    }
    const base = { ...event, previousHash }
    const entryHash = sha256(stable(base))
    appendFileSync(p, JSON.stringify({ ...base, entryHash }) + '\n', 'utf8')
  }

  submitDecision(input: unknown): SystemPolicyRegistrarResult {
    if (!input || typeof input !== 'object') {
      return { ok: false, committed: false, code: 'INVALID_INPUT', message: 'Decision must be an object.' }
    }

    const decision = input as SystemPolicyDecision
    if (decision.decision !== 'APPROVE' && decision.decision !== 'REJECT') {
      return { ok: false, committed: false, code: 'INVALID_DECISION', message: 'Decision must be APPROVE or REJECT.' }
    }
    if (typeof decision.target !== 'string' || !decision.target.trim()) {
      return { ok: false, committed: false, code: 'INVALID_TARGET', message: 'target is required.' }
    }
    if (typeof decision.proposedVersion !== 'string' || !decision.proposedVersion.trim()) {
      return { ok: false, committed: false, code: 'INVALID_PROPOSED_VERSION', message: 'proposedVersion is required.' }
    }

    const decisionId =
      typeof decision.decisionId === 'string' && decision.decisionId.trim()
        ? decision.decisionId.trim()
        : sha256(stable(decision))

    const now = new Date().toISOString()
    const active = this.readActive(decision.target)

    if (active?.lastDecisionId === decisionId) {
      return {
        ok: true,
        committed: decision.decision === 'APPROVE',
        idempotent: true,
        target: decision.target,
        version: active.version
      }
    }

    if (decision.decision === 'REJECT') {
      this.appendJournal({
        schema: 'vertex-system-policy/journal-1',
        event: 'DECISION_REJECTED',
        at: now,
        target: decision.target,
        proposedVersion: decision.proposedVersion,
        decisionId
      })
      return { ok: true, committed: false, target: decision.target }
    }

    if (!validationPass(decision.validation)) {
      return {
        ok: false,
        committed: false,
        code: 'VALIDATION_NOT_PASS',
        message: 'Deterministic validation must be PASS.'
      }
    }

    if (requiresRedConfirmation(decision) && decision.redConfirmed !== true) {
      return {
        ok: false,
        committed: false,
        code: 'RED_CONFIRMATION_REQUIRED',
        message: 'RED/CRITICAL Policy requires explicit confirmation.'
      }
    }

    if (
      active &&
      typeof decision.currentVersion === 'string' &&
      decision.currentVersion.trim() &&
      decision.currentVersion !== active.version
    ) {
      return {
        ok: false,
        committed: false,
        code: 'STALE_VERSION',
        message: 'currentVersion does not match active Policy.'
      }
    }

    if (active && decision.proposedVersion === active.version) {
      return {
        ok: false,
        committed: false,
        code: 'VERSION_NOT_ADVANCED',
        message: 'proposedVersion must advance active Policy version.'
      }
    }

    const signedBody = {
      schema: 'vertex-system-policy/approval-1',
      at: now,
      decisionId,
      target: decision.target,
      currentVersion: active?.version ?? null,
      proposedVersion: decision.proposedVersion,
      decision
    }
    const signature = createHmac('sha256', this.signingKey())
      .update(stable(signedBody), 'utf8')
      .digest('hex')

    const record: ActiveRecord = {
      schema: 'vertex-system-policy/active-1',
      target: decision.target,
      version: decision.proposedVersion,
      committedAt: now,
      lastDecisionId: decisionId,
      policy: decision
    }

    const registryPath = this.registryPath(decision.target)
    const tempPath = registryPath + '.tmp-' + process.pid + '-' + Date.now()
    writeFileSync(tempPath, JSON.stringify(record, null, 2) + '\n', 'utf8')

    appendFileSync(
      this.approvalPath(),
      JSON.stringify({ ...signedBody, signature, algorithm: 'HMAC-SHA256' }) + '\n',
      'utf8'
    )

    renameSync(tempPath, registryPath)

    this.appendJournal({
      schema: 'vertex-system-policy/journal-1',
      event: 'REGISTRY_COMMIT',
      at: now,
      target: decision.target,
      proposedVersion: decision.proposedVersion,
      decisionId,
      registrySha256: sha256(stable(record))
    })

    return { ok: true, committed: true, target: decision.target, version: decision.proposedVersion }
  }

  listActivePolicies(): unknown[] {
    const fs = require('node:fs') as typeof import('node:fs')
    const path = require('node:path') as typeof import('node:path')
    const { app } = require('electron') as typeof import('electron')

    const dir = path.join(app.getPath('userData'), 'vra-registry', 'system-policy')
    if (!fs.existsSync(dir)) return []

    const active: Array<Record<string, unknown>> = []
    for (const name of fs.readdirSync(dir)) {
      if (!name.endsWith('.json')) continue
      try {
        const value: unknown = JSON.parse(
          fs.readFileSync(path.join(dir, name), 'utf8')
        )
        if (
          value &&
          typeof value === 'object' &&
          !Array.isArray(value) &&
          (value as Record<string, unknown>).schema === 'vertex-system-policy/active-1'
        ) {
          active.push(value as Record<string, unknown>)
        }
      } catch {
        // Ignore non-active/corrupt auxiliary files; readActivePolicy remains fail-closed by target.
      }
    }

    active.sort((a, b) => {
      const at = typeof a.target === 'string' ? a.target : ''
      const bt = typeof b.target === 'string' ? b.target : ''
      return at.localeCompare(bt)
    })
    return active
  }

}
