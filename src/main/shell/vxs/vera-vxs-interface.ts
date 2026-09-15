// VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_INTERFACE_IMPORT
import { isVeraVxsHumanFullAccessGranted } from './vera-vxs-human-authority'
import type {
  VertexShellCommandRequest,
  VertexShellCommandResult,
  VertexShellStreamEvent
} from '../../../shared/vertex-shell-contracts'
import {
  VERA_VXS_REQUEST_SCHEMA,
  VERA_VXS_RESULT_SCHEMA,
  type VeraVxsRequest,
  type VeraVxsResult
} from '../../../shared/vera-vxs-contracts'

const MAX_COMMAND_CHARS = 32_000
const MAX_RETURN_STREAM_BYTES = 512 * 1024

export interface VeraVxsExecutor {
  execute(
    request: VertexShellCommandRequest,
    sink: (event: VertexShellStreamEvent) => void
  ): Promise<VertexShellCommandResult>
}

function requiredText(value: unknown, field: string, max = 512): string {
  if (typeof value !== 'string') {
    throw new Error(`VERA_VXS_INVALID_${field.toUpperCase()}`)
  }
  const trimmed = value.trim()
  if (!trimmed || trimmed.length > max) {
    throw new Error(`VERA_VXS_INVALID_${field.toUpperCase()}`)
  }
  return trimmed
}

function validateOrigin(origin: VeraVxsRequest['origin']): VeraVxsRequest['origin'] {
  if (!origin || typeof origin !== 'object') {
    throw new Error('VERA_VXS_INVALID_ORIGIN')
  }

  const vera = requiredText(origin.vera, 'origin_vera', 32).toUpperCase()
  const session = requiredText(origin.session, 'origin_session', 32).toLowerCase()
  const window = requiredText(origin.window, 'origin_window', 32).toLowerCase()

  const veraMatch = /^VERA(\d{2})$/.exec(vera)
  const sessionMatch = /^vera-(\d{2})$/.exec(session)
  const windowMatch = /^vera-(\d{2})$/.exec(window)

  if (!veraMatch || !sessionMatch || !windowMatch) {
    throw new Error('VERA_VXS_INVALID_ORIGIN')
  }

  if (veraMatch[1] !== sessionMatch[1] || veraMatch[1] !== windowMatch[1]) {
    throw new Error('VERA_VXS_ORIGIN_MISMATCH')
  }

  return { vera, session, window }
}

function normalizeRequest(input: VeraVxsRequest): VeraVxsRequest {
  if (!input || typeof input !== 'object') {
    throw new Error('VERA_VXS_REQUEST_REQUIRED')
  }

  if (input.schema !== VERA_VXS_REQUEST_SCHEMA) {
    throw new Error('VERA_VXS_SCHEMA_UNSUPPORTED')
  }

  const requestId = requiredText(input.requestId, 'request_id', 256)
  const correlationId = requiredText(input.correlationId, 'correlation_id', 256)
  const origin = validateOrigin(input.origin)

  if (input.authority !== 'AUTO_SAFE' && input.authority !== 'HUMAN_APPLY') {
    throw new Error('VERA_VXS_INVALID_AUTHORITY')
  }

  const command = requiredText(input.command, 'command', MAX_COMMAND_CHARS)

  // Dedicated VERA ingress is VXS-only. It cannot be used as an arbitrary
  // PowerShell/cmd/process launcher. All execution still flows through the
  // canonical VXS command registry and provider routing inside VertexShellService.
  if (!isVeraVxsHumanFullAccessGranted() && (!/^vxs(?:\s|$)/i.test(command))) {
    throw new Error('VERA_VXS_CANONICAL_VXS_COMMAND_REQUIRED')
  }

  const cwd =
    input.cwd === undefined
      ? undefined
      : requiredText(input.cwd, 'cwd', 4096)

  return {
    schema: VERA_VXS_REQUEST_SCHEMA,
    requestId,
    correlationId,
    origin,
    authority: input.authority,
    command,
    ...(cwd ? { cwd } : {})
  }
}

export async function executeVeraVxsRequest(
  executor: VeraVxsExecutor,
  input: VeraVxsRequest
): Promise<VeraVxsResult> {
  // VERA_VXS_HUMAN_FULL_ACCESS_GATE_000088V4_GATE
  if (!isVeraVxsHumanFullAccessGranted()) {
    throw new Error('VERA_VXS_HUMAN_GATE_REQUIRED')
  }

  const request = normalizeRequest(input)
  const acceptedAt = new Date().toISOString()

  const streamEvents: VertexShellStreamEvent[] = []
  let streamBytes = 0
  let streamTruncated = false

  const sink = (event: VertexShellStreamEvent): void => {
    if (streamTruncated) return

    const eventBytes = Buffer.byteLength(event.chunk ?? '', 'utf8')
    if (streamBytes + eventBytes > MAX_RETURN_STREAM_BYTES) {
      streamTruncated = true
      return
    }

    streamBytes += eventBytes
    streamEvents.push(event)
  }

  const shellRequest: VertexShellCommandRequest = {
    command: request.command,
    ...(request.cwd ? { cwd: request.cwd } : {})
  }

  // Requested authority is provenance/intent metadata only. This bridge does
  // not grant or elevate authority. The existing VXS policy / Human Gate /
  // provider resolver remains the execution authority.
  const shellResult = await executor.execute(shellRequest, sink)

  return {
    schema: VERA_VXS_RESULT_SCHEMA,
    requestId: request.requestId,
    correlationId: request.correlationId,
    origin: request.origin,
    requestedAuthority: request.authority,
    authorityEnforcement: 'VXS_EXISTING_POLICY',
    transport: 'VERTEX_SHELL_SERVICE',
    acceptedAt,
    completedAt: new Date().toISOString(),
    streamBytes,
    streamTruncated,
    streamEvents,
    shellResult
  }
}
