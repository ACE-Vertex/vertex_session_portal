import { createServer, type Server } from 'node:http'
import type { AddressInfo } from 'node:net'
import type { VertexShellService } from '../vertex-shell-service'
import { executeVeraVxsRequest } from './vera-vxs-interface'
import {
  beginVeraVxsActivity,
  completeVeraVxsActivity,
  failVeraVxsActivity
} from './vera-vxs-activity'
import {
  getVeraVxsHumanAuthorityState,
  isVeraVxsHumanFullAccessGranted
} from './vera-vxs-human-authority'

export const VERA_VXS_VRA_DIRECT_NERVE_SCHEMA =
  'vertex-vxs/vra-direct-request-1' as const
export const VERA_VXS_VRA_DIRECT_RESPONSE_SCHEMA =
  'vertex-vxs/vra-direct-response-1' as const
export const VERA_VXS_VRA_DIRECT_DEFAULT_HOST = '127.0.0.1' as const
export const VERA_VXS_VRA_DIRECT_DEFAULT_PORT = 47834 as const

const MAX_BODY_BYTES = 64 * 1024
const MAX_COMMAND_CHARS = 16 * 1024
const MAX_CWD_CHARS = 4096
const ORIGIN_RE = /^VERA(\d{2})$/
const SESSION_RE = /^vera-(\d{2})$/

export interface VeraVxsVraDirectRequest {
  schema: typeof VERA_VXS_VRA_DIRECT_NERVE_SCHEMA
  request_id: string
  correlation_id: string
  origin: {
    vera: string
    session: string
    window: string
  }
  command: string
  cwd?: string
}

export interface VeraVxsVraDirectServerHandle {
  host: string
  port: number
  close(): Promise<void>
}

function json(
  response: import('node:http').ServerResponse,
  status: number,
  payload: unknown
): void {
  const bytes = Buffer.from(JSON.stringify(payload), 'utf8')
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': String(bytes.length),
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff'
  })
  response.end(bytes)
}

function errorPayload(
  code: string,
  message: string,
  requestId: string | null = null
): Record<string, unknown> {
  return {
    schema: VERA_VXS_VRA_DIRECT_RESPONSE_SCHEMA,
    ok: false,
    request_id: requestId,
    error: code,
    message
  }
}

function validateOrigin(origin: VeraVxsVraDirectRequest['origin']): void {
  const vera = ORIGIN_RE.exec(origin.vera)
  const session = SESSION_RE.exec(origin.session)
  const window = SESSION_RE.exec(origin.window)
  if (!vera || !session || !window) {
    throw new Error('VERA_VXS_DIRECT_ORIGIN_FORMAT_INVALID')
  }
  if (vera[1] !== session[1] || vera[1] !== window[1]) {
    throw new Error('VERA_VXS_DIRECT_ORIGIN_MISMATCH')
  }
}

function validateRequest(value: unknown): VeraVxsVraDirectRequest {
  if (!value || typeof value !== 'object') {
    throw new Error('VERA_VXS_DIRECT_REQUEST_OBJECT_REQUIRED')
  }

  const input = value as Record<string, unknown>
  if (input.schema !== VERA_VXS_VRA_DIRECT_NERVE_SCHEMA) {
    throw new Error('VERA_VXS_DIRECT_SCHEMA_INVALID')
  }

  const requestId = String(input.request_id ?? '')
  const correlationId = String(input.correlation_id ?? '')
  const command = String(input.command ?? '')
  const cwd = input.cwd == null ? undefined : String(input.cwd)
  const originInput = input.origin

  if (!/^[A-Za-z0-9._:-]{1,160}$/.test(requestId)) {
    throw new Error('VERA_VXS_DIRECT_REQUEST_ID_INVALID')
  }
  if (!/^[A-Za-z0-9._:-]{1,200}$/.test(correlationId)) {
    throw new Error('VERA_VXS_DIRECT_CORRELATION_ID_INVALID')
  }
  if (!command.trim() || command.length > MAX_COMMAND_CHARS) {
    throw new Error('VERA_VXS_DIRECT_COMMAND_INVALID')
  }
  if (cwd != null && cwd.length > MAX_CWD_CHARS) {
    throw new Error('VERA_VXS_DIRECT_CWD_INVALID')
  }
  if (!originInput || typeof originInput !== 'object') {
    throw new Error('VERA_VXS_DIRECT_ORIGIN_REQUIRED')
  }

  const originRecord = originInput as Record<string, unknown>
  const origin = {
    vera: String(originRecord.vera ?? ''),
    session: String(originRecord.session ?? ''),
    window: String(originRecord.window ?? '')
  }
  validateOrigin(origin)

  return {
    schema: VERA_VXS_VRA_DIRECT_NERVE_SCHEMA,
    request_id: requestId,
    correlation_id: correlationId,
    origin,
    command,
    ...(cwd ? { cwd } : {})
  }
}

async function readJsonBody(
  request: import('node:http').IncomingMessage
): Promise<unknown> {
  const chunks: Buffer[] = []
  let size = 0

  for await (const chunk of request) {
    const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
    size += bytes.length
    if (size > MAX_BODY_BYTES) {
      throw new Error('VERA_VXS_DIRECT_BODY_TOO_LARGE')
    }
    chunks.push(bytes)
  }

  const text = Buffer.concat(chunks).toString('utf8')
  if (!text.trim()) throw new Error('VERA_VXS_DIRECT_BODY_REQUIRED')
  return JSON.parse(text)
}

export function createVeraVxsVraDirectServer(
  service: VertexShellService,
  options: {
    host?: string
    port?: number
  } = {}
): Promise<VeraVxsVraDirectServerHandle> {
  const host = options.host ?? VERA_VXS_VRA_DIRECT_DEFAULT_HOST
  const port = options.port ?? VERA_VXS_VRA_DIRECT_DEFAULT_PORT

  if (host !== '127.0.0.1') {
    return Promise.reject(new Error('VERA_VXS_DIRECT_LOOPBACK_ONLY'))
  }

  let inFlight = false

  const server: Server = createServer(async (request, response) => {
    const remote = request.socket.remoteAddress ?? ''
    if (
      remote !== '127.0.0.1' &&
      remote !== '::1' &&
      remote !== '::ffff:127.0.0.1'
    ) {
      json(response, 403, errorPayload(
        'VERA_VXS_DIRECT_LOOPBACK_REQUIRED',
        'VXS direct nerve accepts loopback clients only.'
      ))
      return
    }

    if (request.method === 'GET' && request.url === '/health') {
      const authority = getVeraVxsHumanAuthorityState()
      json(response, 200, {
        schema: 'vertex-vxs/vra-direct-health-1',
        status: 'READY',
        host,
        authority: {
          mode: authority.mode,
          granted: authority.granted,
          granted_by: authority.grantedBy,
          persistence: authority.persistence
        }
      })
      return
    }

    if (request.method !== 'POST' || request.url !== '/v1/execute') {
      json(response, 404, errorPayload(
        'VERA_VXS_DIRECT_ROUTE_NOT_FOUND',
        'Use POST /v1/execute.'
      ))
      return
    }

    if (!isVeraVxsHumanFullAccessGranted()) {
      json(response, 423, errorPayload(
        'VERA_VXS_HUMAN_GATE_REQUIRED',
        'Human AUTH must be FULL before VRA direct execution.'
      ))
      return
    }

    if (inFlight) {
      json(response, 429, errorPayload(
        'VERA_VXS_DIRECT_BUSY',
        'Another VRA direct request is currently executing.'
      ))
      return
    }

    let direct: VeraVxsVraDirectRequest
    try {
      direct = validateRequest(await readJsonBody(request))
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      json(response, 400, errorPayload(message, message))
      return
    }

    inFlight = true
    beginVeraVxsActivity({
      originVera: direct.origin.vera,
      originSession: direct.origin.session,
      command: direct.command,
      requestId: direct.request_id,
      correlationId: direct.correlation_id
    })

    try {
      const result = await executeVeraVxsRequest(service, {
        schema: 'vertex-vxs/vera-request-1',
        requestId: direct.request_id,
        correlationId: direct.correlation_id,
        origin: direct.origin,
        authority: 'AUTO_SAFE',
        command: direct.command,
        ...(direct.cwd ? { cwd: direct.cwd } : {})
      })

      completeVeraVxsActivity(direct.request_id, result) // VXS_VERA_PERSISTENT_WORKSPACE_000097V4

      json(response, 200, {
        schema: VERA_VXS_VRA_DIRECT_RESPONSE_SCHEMA,
        ok: true,
        request_id: direct.request_id,
        correlation_id: direct.correlation_id,
        origin: direct.origin,
        transport: 'VRA_DIRECT_HTTP_LOOPBACK',
        result
      })
    } catch (error) {
      failVeraVxsActivity(direct.request_id, error)
      const message = error instanceof Error ? error.message : String(error)
      json(response, 500, errorPayload(
        'VERA_VXS_DIRECT_EXECUTION_FAILED',
        message,
        direct.request_id
      ))
    } finally {
      inFlight = false
    }
  })

  return new Promise((resolve, reject) => {
    const onError = (error: Error) => reject(error)
    server.once('error', onError)
    server.listen(port, host, () => {
      server.off('error', onError)
      const address = server.address() as AddressInfo | null
      if (!address) {
        server.close()
        reject(new Error('VERA_VXS_DIRECT_ADDRESS_UNAVAILABLE'))
        return
      }
      resolve({
        host,
        port: address.port,
        close: () =>
          new Promise<void>((closeResolve, closeReject) => {
            server.close(error => error ? closeReject(error) : closeResolve())
          })
      })
    })
  })
}

let productionHandle: VeraVxsVraDirectServerHandle | null = null
let productionStarting: Promise<VeraVxsVraDirectServerHandle> | null = null

export function registerVeraVxsVraDirectHttpNerve(
  service: VertexShellService
): void {
  if (productionHandle || productionStarting) return

  productionStarting = createVeraVxsVraDirectServer(service)
  productionStarting
    .then(handle => {
      productionHandle = handle
      productionStarting = null
      console.log(
        `[VERA_VXS_DIRECT] READY http://${handle.host}:${handle.port}`
      )
    })
    .catch(error => {
      productionStarting = null
      console.error(
        '[VERA_VXS_DIRECT] START_FAILED',
        error instanceof Error ? error.message : String(error)
      )
    })
}
