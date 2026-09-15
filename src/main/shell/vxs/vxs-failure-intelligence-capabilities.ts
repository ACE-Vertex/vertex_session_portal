// VXS_FAILURE_INTELLIGENCE_CAPABILITY_PACK_000019
import * as fs from 'node:fs'
import * as path from 'node:path'
import type {
  VxsCommandContext,
  VxsCommandDefinition,
  VxsCommandDispatchResult
} from './vxs-command-registry'

function line(value = ''): string {
  return `${value}\n`
}

function immediateError(
  message: string,
  hints: string[] = []
): VxsCommandDispatchResult {
  return {
    kind: 'immediate',
    output: [`ERROR: ${message}`, ...hints, ''].map(line).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

const JOB_ID_PATTERN = /^[A-Za-z0-9._:-]{1,256}$/

function readJsonFile(filePath: string, maxBytes = 4 * 1024 * 1024): unknown | null {
  try {
    const stat = fs.statSync(filePath)
    if (!stat.isFile() || stat.size > maxBytes) return null
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as unknown
  } catch {
    return null
  }
}

function readTextFile(filePath: string, maxBytes = 4 * 1024 * 1024): string | null {
  try {
    const stat = fs.statSync(filePath)
    if (!stat.isFile() || stat.size > maxBytes) return null
    return fs.readFileSync(filePath, 'utf-8')
  } catch {
    return null
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function stringValue(record: Record<string, unknown> | null, key: string): string {
  const value = record?.[key]
  return typeof value === 'string' ? value : ''
}

function boolValue(record: Record<string, unknown> | null, key: string): boolean | null {
  const value = record?.[key]
  return typeof value === 'boolean' ? value : null
}

function findRecordWithJobId(
  value: unknown,
  jobId: string,
  depth = 0
): Record<string, unknown> | null {
  if (depth > 8) return null

  const record = asRecord(value)
  if (record) {
    if (record.job_id === jobId) return record

    for (const child of Object.values(record)) {
      const found = findRecordWithJobId(child, jobId, depth + 1)
      if (found) return found
    }

    return null
  }

  if (Array.isArray(value)) {
    for (const child of value) {
      const found = findRecordWithJobId(child, jobId, depth + 1)
      if (found) return found
    }
  }

  return null
}

function portalMetadataRoots(): string[] {
  const appData = process.env.APPDATA ?? ''
  const localAppData = process.env.LOCALAPPDATA ?? ''

  return [
    path.join(appData, 'vertex-session-portal', 'vra-dispatch'),
    path.join(appData, 'Vertex Session Portal', 'vra-dispatch'),
    path.join(localAppData, 'vertex-session-portal', 'vra-dispatch')
  ].filter(value => value.length > 0)
}

function findPortalMetadata(
  jobId: string
): { path: string; record: Record<string, unknown> } | null {
  for (const root of portalMetadataRoots()) {
    if (!fs.existsSync(root)) continue

    let names: string[]
    try {
      names = fs.readdirSync(root)
        .filter(name => name.endsWith('.json'))
        .slice(-600)
        .reverse()
    } catch {
      continue
    }

    for (const name of names) {
      const filePath = path.join(root, name)
      const text = readTextFile(filePath)
      if (!text || !text.includes(jobId)) continue

      const data = readJsonFile(filePath)
      const found = findRecordWithJobId(data, jobId)
      if (found) return { path: filePath, record: found }

      const record = asRecord(data)
      if (record && record.job_id === jobId) {
        return { path: filePath, record }
      }
    }
  }

  return null
}

function findRegistryRecord(
  jobId: string
): { path: string; record: Record<string, unknown> } | null {
  const root =
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry'

  if (!fs.existsSync(root)) return null

  let names: string[]
  try {
    names = fs.readdirSync(root)
      .filter(name => name.endsWith('.json'))
      .slice(-1000)
      .reverse()
  } catch {
    return null
  }

  for (const name of names) {
    const filePath = path.join(root, name)
    const text = readTextFile(filePath)
    if (!text || !text.includes(jobId)) continue

    const data = readJsonFile(filePath)
    const found = findRecordWithJobId(data, jobId)
    if (found) return { path: filePath, record: found }
  }

  return null
}

interface EvidenceHit {
  path: string
  record: Record<string, unknown>
}

function findEvidence(
  jobId: string
): EvidenceHit | null {
  const roots = [
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\evidence',
    'G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\lanes'
  ]

  let scanned = 0
  const maxFiles = 1600

  function walk(current: string, depth: number): EvidenceHit | null {
    if (depth > 6 || scanned >= maxFiles) return null

    let entries: fs.Dirent[]
    try {
      entries = fs.readdirSync(current, { withFileTypes: true })
    } catch {
      return null
    }

    const ordered = [...entries].sort((a, b) => b.name.localeCompare(a.name))

    for (const entry of ordered) {
      if (scanned >= maxFiles) return null
      const full = path.join(current, entry.name)

      if (entry.isDirectory()) {
        const found = walk(full, depth + 1)
        if (found) return found
        continue
      }

      if (!entry.isFile() || !entry.name.endsWith('.json')) continue
      scanned += 1

      const text = readTextFile(full)
      if (!text || !text.includes(jobId)) continue

      const data = readJsonFile(full)
      const found = findRecordWithJobId(data, jobId)
      if (found) return { path: full, record: found }

      const record = asRecord(data)
      if (record) return { path: full, record }
    }

    return null
  }

  for (const root of roots) {
    if (!fs.existsSync(root)) continue
    const found = walk(root, 0)
    if (found) return found
  }

  return null
}

function classify(
  portal: Record<string, unknown> | null,
  registry: Record<string, unknown> | null,
  evidence: Record<string, unknown> | null
): string {
  const lastError = (
    stringValue(portal, 'workstation_last_error') ||
    stringValue(portal, 'workstationLastError') ||
    stringValue(portal, 'error')
  ).toLowerCase()

  if (lastError) {
    if (lastError.includes('inspector') || lastError.includes('parse manifest')) {
      return 'INSPECTOR_REJECT'
    }
    if (lastError.includes('sha') || lastError.includes('hash')) {
      return 'SHA_MISMATCH'
    }
    if (lastError.includes('approval') || lastError.includes('human')) {
      return 'APPROVAL_REJECT'
    }
    if (lastError.includes('routing') || lastError.includes('origin')) {
      return 'ROUTING_REJECT'
    }
    if (
      lastError.includes('409') ||
      lastError.includes('conflict') ||
      lastError.includes('duplicate')
    ) {
      return 'IDENTITY_CONFLICT'
    }
    return 'REGISTRATION_ERROR'
  }

  const evidenceSuccess =
    boolValue(evidence, 'success') ??
    boolValue(evidence, 'verified')

  const evidenceState = (
    stringValue(evidence, 'final_state') ||
    stringValue(evidence, 'state') ||
    stringValue(registry, 'evidence_state')
  ).toUpperCase()

  if (evidenceSuccess === false || evidenceState === 'FAILED') {
    return 'VERIFY_FAILED'
  }

  const returnState = (
    stringValue(registry, 'evidence_return_state') ||
    stringValue(portal, 'workstation_evidence_return_state') ||
    stringValue(evidence, 'evidence_return_state')
  ).toUpperCase()

  if (returnState === 'RETURNED') return 'RETURNED'
  if (returnState === 'RETURN_QUEUED') return 'RETURN_QUEUED'

  const state = (
    stringValue(registry, 'state') ||
    stringValue(asRecord(registry?.record), 'state') ||
    stringValue(portal, 'workstation_job_state')
  ).toUpperCase()

  if (state === 'FAILED' || state === 'REJECTED') return state

  const allocated =
    stringValue(registry, 'allocated_lane') ||
    stringValue(asRecord(registry?.record), 'execution_lane')

  if (allocated) {
    if (state === 'EXECUTING') return 'EXECUTING'
    if (state === 'SUCCEEDED') return 'SUCCEEDED'
    return 'ALLOCATED'
  }

  if (state === 'REGISTERED') return 'REGISTERED'

  const registration = (
    stringValue(portal, 'workstation_registration')
  ).toUpperCase()

  if (registration === 'REGISTERED') return 'REGISTERED'
  if (registration === 'BLOCKED') return 'REGISTRATION_BLOCKED'

  if (portal || registry || evidence) return 'OBSERVED_UNCLASSIFIED'
  return 'NOT_FOUND'
}

function triageCommand(
  args: string[],
  _context: VxsCommandContext
): VxsCommandDispatchResult {
  const jobId = (args[0] ?? '').trim()

  if (!jobId) {
    return immediateError(
      'Job ID is required.',
      ['Usage: vxs triage <job-id>']
    )
  }

  if (!JOB_ID_PATTERN.test(jobId)) {
    return immediateError('Job ID contains unsupported characters.')
  }

  const portalHit = findPortalMetadata(jobId)
  const registryHit = findRegistryRecord(jobId)
  const evidenceHit = findEvidence(jobId)

  const portal = portalHit?.record ?? null
  const registry = registryHit?.record ?? null
  const evidence = evidenceHit?.record ?? null

  const classification = classify(portal, registry, evidence)

  const lastError =
    stringValue(portal, 'workstation_last_error') ||
    stringValue(portal, 'workstationLastError') ||
    stringValue(portal, 'error')

  const state =
    stringValue(registry, 'state') ||
    stringValue(asRecord(registry?.record), 'state') ||
    stringValue(portal, 'workstation_job_state')

  const allocated =
    stringValue(registry, 'allocated_lane') ||
    stringValue(asRecord(registry?.record), 'execution_lane')

  const evidenceState =
    stringValue(registry, 'evidence_state') ||
    stringValue(portal, 'workstation_evidence_state') ||
    stringValue(evidence, 'final_state') ||
    stringValue(evidence, 'state')

  const returnState =
    stringValue(registry, 'evidence_return_state') ||
    stringValue(portal, 'workstation_evidence_return_state') ||
    stringValue(evidence, 'evidence_return_state')

  const rows = [
    'VXS TRIAGE',
    `Job ID: ${jobId}`,
    `Classification: ${classification}`,
    `Job State: ${state || '(unknown)'}`,
    `Allocated Lane: ${allocated || '(none)'}`,
    `Evidence State: ${evidenceState || '(none)'}`,
    `Return State: ${returnState || '(none)'}`,
    '',
    `Portal Metadata: ${portalHit?.path ?? '(not found)'}`,
    `Job Registry: ${registryHit?.path ?? '(not found)'}`,
    `Evidence: ${evidenceHit?.path ?? '(not found)'}`,
    ''
  ]

  if (lastError) {
    rows.push('Last Error:')
    rows.push(lastError.slice(0, 3000))
    rows.push('')
  }

  rows.push('TRIAGE_MUTATION=NONE')
  rows.push('')

  return {
    kind: 'immediate',
    output: rows.map(line).join(''),
    exitCode: classification === 'NOT_FOUND' ? 1 : 0,
    stream: classification === 'NOT_FOUND' ? 'stderr' : 'system'
  }
}

export function createVxsFailureIntelligenceCommands(): VxsCommandDefinition[] {
  return [
    {
      name: 'triage',
      aliases: ['diagnose-job'],
      usage: 'vxs triage <job-id>',
      summary: 'Classify Portal/Workstation failure and lifecycle evidence',
      execute: triageCommand
    }
  ]
}
