// VXS_GIT_BOOTSTRAP_000068V3
// VERA_TO_VXS_TYPED_BRIDGE_000067V3
import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { app } from 'electron'
import { executeVxsCommand } from './vxs-command-registry'

const REQUEST_SCHEMA = 'vertex-vxs-request/1' as const
const RESULT_SCHEMA = 'vertex-vxs-result/1' as const
const AUDIT_SCHEMA = 'vertex-session-portal/vera-vxs-request-audit-1' as const
const VXS_VERSION = '0.1.0' as const
const VXS_CANONICAL_NAME = 'Vertex eXecution Shell' as const
const DEVELOPMENT_ROOT = path.resolve('G:\\Vertex_Project\\Development')
const MAX_MESSAGE_CHARS = 240
const MAX_PROJECT_ROOT_CHARS = 512
const EXECUTION_TIMEOUT_MS = 5 * 60 * 1000
const MAX_RESULT_BYTES = 2 * 1024 * 1024

const ORIGIN_SESSION_PATTERN = /^vera-0[1-5]$/
const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{8,160}$/

type VeraVxsRequest = {
  schema: typeof REQUEST_SCHEMA
  request_id: string
  origin_session: string
  action: 'git.publish' | 'git.bootstrap'
  project_root: string
  message?: string
  remote_url?: string
}

type AuditStatus = 'ACCEPTED' | 'SUCCEEDED' | 'FAILED' | 'REJECTED'

type AuditRecord = {
  schema: typeof AUDIT_SCHEMA
  request_id: string
  origin_session: string
  action: 'git.publish' | 'git.bootstrap'
  project_root: string
  message_sha256: string
  status: AuditStatus
  at_utc: string
  exit_code: number | null
  route_summary: string | null
  detail: string
}

type VeraVxsResult = {
  schema: typeof RESULT_SCHEMA
  request_id: string
  origin_session: string
  action: 'git.publish' | 'git.bootstrap'
  project_root: string
  status: 'SUCCEEDED' | 'FAILED' | 'REJECTED' | 'INDETERMINATE' | 'IDEMPOTENT_SUCCEEDED' | 'IDEMPOTENT_FAILED' | 'IDEMPOTENT_REJECTED'
  exit_code: number | null
  route_summary: string | null
  message: string
}

function requireRecord(value: unknown, code: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(code)
  return value as Record<string, unknown>
}

function requiredString(value: unknown, code: string): string {
  if (typeof value !== 'string' || !value.trim()) throw new Error(code)
  return value.trim()
}

function normalizeProjectRoot(value: string): string {
  if (value.length > MAX_PROJECT_ROOT_CHARS) throw new Error('VXS_REQUEST_PROJECT_ROOT_TOO_LARGE')
  if (!path.isAbsolute(value)) throw new Error('VXS_REQUEST_PROJECT_ROOT_NOT_ABSOLUTE')

  let resolved: string
  try {
    resolved = fs.realpathSync.native(path.resolve(value))
  } catch {
    throw new Error('VXS_REQUEST_PROJECT_ROOT_NOT_FOUND')
  }

  let developmentRoot: string
  try {
    developmentRoot = fs.realpathSync.native(DEVELOPMENT_ROOT)
  } catch {
    throw new Error('VXS_REQUEST_DEVELOPMENT_ROOT_NOT_FOUND')
  }

  const rel = path.relative(developmentRoot, resolved)
  if (rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))) return resolved
  throw new Error('VXS_REQUEST_PROJECT_ROOT_OUT_OF_SCOPE')
}

function parseRequest(encoded: string): VeraVxsRequest {
  let decoded: unknown
  try {
    decoded = JSON.parse(decodeURIComponent(encoded)) as unknown
  } catch {
    throw new Error('VXS_REQUEST_PAYLOAD_INVALID')
  }

  const row = requireRecord(decoded, 'VXS_REQUEST_PAYLOAD_INVALID')
  if (row.schema !== REQUEST_SCHEMA) throw new Error('VXS_REQUEST_SCHEMA_UNSUPPORTED')

  const requestId = requiredString(row.request_id, 'VXS_REQUEST_ID_REQUIRED')
  if (!REQUEST_ID_PATTERN.test(requestId)) throw new Error('VXS_REQUEST_ID_INVALID')

  const originSession = requiredString(row.origin_session, 'VXS_REQUEST_ORIGIN_REQUIRED').toLowerCase()
  if (!ORIGIN_SESSION_PATTERN.test(originSession)) throw new Error('VXS_REQUEST_ORIGIN_INVALID')

  if (row.action !== 'git.publish' && row.action !== 'git.bootstrap') {
    throw new Error('VXS_REQUEST_ACTION_FORBIDDEN')
  }

  const projectRoot = normalizeProjectRoot(requiredString(row.project_root, 'VXS_REQUEST_PROJECT_ROOT_REQUIRED'))

  if (row.action === 'git.publish') {
    const message = requiredString(row.message, 'VXS_REQUEST_MESSAGE_REQUIRED')
    if (message.length > MAX_MESSAGE_CHARS || /[\r\n]/.test(message)) {
      throw new Error('VXS_REQUEST_MESSAGE_INVALID')
    }
    if (row.remote_url !== undefined) throw new Error('VXS_REQUEST_REMOTE_URL_FORBIDDEN')

    return {
      schema: REQUEST_SCHEMA,
      request_id: requestId,
      origin_session: originSession,
      action: 'git.publish',
      project_root: projectRoot,
      message,
    }
  }

  const remoteUrl = requiredString(row.remote_url, 'VXS_REQUEST_REMOTE_URL_REQUIRED')
  if (!/^https:\/\/github\.com\/[^/\s]+\/[^/\s]+(?:\.git)?$/i.test(remoteUrl)) {
    throw new Error('VXS_REQUEST_REMOTE_URL_INVALID')
  }
  if (row.message !== undefined) throw new Error('VXS_REQUEST_MESSAGE_FORBIDDEN')

  return {
    schema: REQUEST_SCHEMA,
    request_id: requestId,
    origin_session: originSession,
    action: 'git.bootstrap',
    project_root: projectRoot,
    remote_url: remoteUrl,
  }
}

function stagingRoot(): string {
  return path.join(app.getPath('userData'), 'vra-dispatch')
}

function auditPath(): string {
  return path.join(stagingRoot(), 'vera-vxs-request-audit.jsonl')
}

function messageSha256(message: string): string {
  return createHash('sha256').update(message, 'utf8').digest('hex')
}

function appendAudit(request: VeraVxsRequest, status: AuditStatus, detail: string, exitCode: number | null, routeSummary: string | null): void {
  const root = stagingRoot()
  fs.mkdirSync(root, { recursive: true })
  const record: AuditRecord = {
    schema: AUDIT_SCHEMA,
    request_id: request.request_id,
    origin_session: request.origin_session,
    action: request.action,
    project_root: request.project_root,
    message_sha256: messageSha256(request.action === 'git.publish' ? request.message! : request.remote_url!),
    status,
    at_utc: new Date().toISOString(),
    exit_code: exitCode,
    route_summary: routeSummary,
    detail: detail.slice(-12000),
  }
  fs.appendFileSync(auditPath(), `${JSON.stringify(record)}\n`, { encoding: 'utf8' })
}

function priorAudit(requestId: string): AuditRecord | null {
  const file = auditPath()
  if (!fs.existsSync(file)) return null
  let text = ''
  try {
    text = fs.readFileSync(file, 'utf8')
  } catch {
    return null
  }

  let latest: AuditRecord | null = null
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue
    try {
      const row = JSON.parse(line) as Partial<AuditRecord>
      if (row.schema !== AUDIT_SCHEMA || row.request_id !== requestId) continue
      latest = row as AuditRecord
    } catch {
      // Corrupt unrelated audit lines do not authorize execution.
    }
  }
  return latest
}

function result(
  request: VeraVxsRequest,
  status: VeraVxsResult['status'],
  message: string,
  exitCode: number | null,
  routeSummary: string | null,
): string {
  const payload: VeraVxsResult = {
    schema: RESULT_SCHEMA,
    request_id: request.request_id,
    origin_session: request.origin_session,
    action: request.action,
    project_root: request.project_root,
    status,
    exit_code: exitCode,
    route_summary: routeSummary,
    message: message.slice(-12000),
  }
  return JSON.stringify(payload)
}

function idempotentResult(request: VeraVxsRequest, prior: AuditRecord): string | null {
  if (prior.status === 'SUCCEEDED') {
    return result(request, 'IDEMPOTENT_SUCCEEDED', prior.detail, prior.exit_code, prior.route_summary)
  }
  if (prior.status === 'FAILED') {
    return result(request, 'IDEMPOTENT_FAILED', prior.detail, prior.exit_code, prior.route_summary)
  }
  if (prior.status === 'REJECTED') {
    return result(request, 'IDEMPOTENT_REJECTED', prior.detail, prior.exit_code, prior.route_summary)
  }
  if (prior.status === 'ACCEPTED') {
    return result(
      request,
      'INDETERMINATE',
      'A previous execution crossed the durable ACCEPTED boundary but no terminal audit record exists. Automatic replay is forbidden.',
      null,
      prior.route_summary,
    )
  }
  return null
}

export function dispatchVeraVxsRequest(encoded: string): string {
  const request = parseRequest(encoded)
  const prior = priorAudit(request.request_id)
  if (prior) {
    const replay = idempotentResult(request, prior)
    if (replay) return replay
  }

  const rawCommand = request.action === 'git.publish'
    ? `vxs git publish ${request.origin_session} ${request.message}`
    : `vxs git bootstrap ${request.origin_session} ${request.remote_url}`
  const dispatch = executeVxsCommand(rawCommand, {
    cwd: request.project_root,
    version: VXS_VERSION,
    canonicalName: VXS_CANONICAL_NAME,
    compatibilityBackend: 'pwsh.exe',
  })

  if (!dispatch) {
    const detail = 'VXS command registry did not accept the typed git.publish request.'
    appendAudit(request, 'REJECTED', detail, null, null)
    return result(request, 'REJECTED', detail, null, null)
  }

  if (dispatch.kind === 'immediate') {
    const detail = dispatch.output || 'VXS rejected the typed git.publish request.'
    appendAudit(request, 'REJECTED', detail, dispatch.exitCode, 'VXS immediate rejection')
    return result(request, 'REJECTED', detail, dispatch.exitCode, 'VXS immediate rejection')
  }

  appendAudit(request, 'ACCEPTED', `Typed ${request.action} request accepted by VXS. Execution begins.`, null, dispatch.routeSummary)

  const child = spawnSync(
    'pwsh.exe',
    ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', dispatch.executionCommand],
    {
      cwd: dispatch.executionCwd,
      encoding: 'utf8',
      windowsHide: true,
      timeout: EXECUTION_TIMEOUT_MS,
      maxBuffer: MAX_RESULT_BYTES,
    }
  )

  const stdout = typeof child.stdout === 'string' ? child.stdout : ''
  const stderr = typeof child.stderr === 'string' ? child.stderr : ''
  const detail = [
    stdout ? `STDOUT\n${stdout}` : '',
    stderr ? `STDERR\n${stderr}` : '',
    child.error ? `ERROR\n${child.error.message}` : '',
    child.signal ? `SIGNAL\n${child.signal}` : '',
  ].filter(Boolean).join('\n').slice(-12000)

  if (!child.error && child.status === 0) {
    appendAudit(request, 'SUCCEEDED', detail || `VXS ${request.action} completed successfully.`, 0, dispatch.routeSummary)
    return result(
      request,
      'SUCCEEDED',
      detail || `VXS ${request.action} completed successfully.`,
      0,
      dispatch.routeSummary,
    )
  }

  const exitCode = typeof child.status === 'number' ? child.status : null
  const failure = detail || `VXS ${request.action} failed without process output.`
  appendAudit(request, 'FAILED', failure, exitCode, dispatch.routeSummary)
  return result(request, 'FAILED', failure, exitCode, dispatch.routeSummary)
}
