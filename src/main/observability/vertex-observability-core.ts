import { app } from 'electron'
import * as crypto from 'node:crypto'
import * as fs from 'node:fs'
import * as path from 'node:path'

export type VertexObservationKind =
  | 'lifecycle'
  | 'trace'
  | 'state'
  | 'metric'
  | 'incident'
  | 'error'
  | 'event-ray'

export type VertexObservationRecord = {
  schema: 'vertex-session-portal/observability-record-1'
  ts: string
  mono_ms: number
  kind: VertexObservationKind
  event: string
  correlation_id?: string
  session_id?: string
  job_id?: string
  lane_id?: string
  payload?: Record<string, unknown>
}

export type VertexIncidentPack = {
  schema: 'vertex-session-portal/incident-evidence-pack-1'
  incident_id: string
  created_at: string
  reason: string
  correlation_id?: string
  trigger?: Record<string, unknown>
  runtime: Record<string, unknown>
  flight_recorder: VertexObservationRecord[]
  event_ray_tail: Array<Record<string, unknown>>
}

const SCHEMA = 'vertex-session-portal/observability-record-1' as const
const BLACK_BOX_MAX_BYTES = 25 * 1024 * 1024
const FLIGHT_WINDOW_MS = 5 * 60 * 1000
const FLIGHT_MAX_RECORDS = 20_000
const EVENT_RAY_TAIL_BYTES = 4 * 1024 * 1024
const METRIC_INTERVAL_MS = 5_000
const EVENT_RAY_POLL_MS = 750
const INCIDENT_COOLDOWN_MS = 10_000

function nowIso(): string {
  return new Date().toISOString()
}

function monoNow(): number {
  return Date.now()
}

function safeError(error: unknown): Record<string, unknown> {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack_head: error.stack?.split('\n').slice(0, 8).join('\n') ?? null,
    }
  }
  return { message: String(error) }
}

function sanitizeUrl(value: unknown): unknown {
  if (typeof value !== 'string') return value
  try {
    const u = new URL(value)
    u.search = ''
    u.hash = ''
    return u.toString()
  } catch {
    return value
  }
}

function sanitizePayload(input: unknown, depth = 0): unknown {
  if (depth > 5) return '<max-depth>'
  if (input === null || input === undefined) return input
  if (typeof input === 'number' || typeof input === 'boolean') return input
  if (typeof input === 'string') {
    return input.length > 512 ? `${input.slice(0, 512)}…` : input
  }
  if (Array.isArray(input)) {
    return input.slice(0, 64).map((v) => sanitizePayload(v, depth + 1))
  }
  if (typeof input !== 'object') return String(input)

  const source = input as Record<string, unknown>
  const out: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(source)) {
    const lk = key.toLowerCase()

    if (
      lk === 'text' ||
      lk === 'value' ||
      lk === 'prompt' ||
      lk === 'message_content' ||
      lk === 'innertext' ||
      lk === 'textcontent' ||
      lk === 'innerhtml' ||
      lk === 'clipboard'
    ) {
      out[key] = '<redacted>'
      continue
    }

    if (lk === 'url' || lk === 'href') {
      out[key] = sanitizeUrl(value)
      continue
    }

    out[key] = sanitizePayload(value, depth + 1)
  }
  return out
}

function readTail(pathname: string, maxBytes: number): string {
  try {
    const stat = fs.statSync(pathname)
    const size = stat.size
    const start = Math.max(0, size - maxBytes)
    const fd = fs.openSync(pathname, 'r')
    try {
      const buffer = Buffer.alloc(size - start)
      fs.readSync(fd, buffer, 0, buffer.length, start)
      let text = buffer.toString('utf8')
      if (start > 0) {
        const firstNewline = text.indexOf('\n')
        if (firstNewline >= 0) text = text.slice(firstNewline + 1)
      }
      return text
    } finally {
      fs.closeSync(fd)
    }
  } catch {
    return ''
  }
}

async function sha256File(pathname: string): Promise<string | null> {
  return await new Promise((resolve) => {
    try {
      const hash = crypto.createHash('sha256')
      const stream = fs.createReadStream(pathname)
      stream.on('data', (chunk) => hash.update(chunk))
      stream.on('error', () => resolve(null))
      stream.on('end', () => resolve(hash.digest('hex')))
    } catch {
      resolve(null)
    }
  })
}

class VertexObservabilityCore {
  private started = false
  private userData = ''
  private root = ''
  private blackBoxPath = ''
  private incidentRoot = ''
  private eventRayPath = ''
  private flight: VertexObservationRecord[] = []
  private lastMetricAt = monoNow()
  private eventRayOffset = 0
  private eventRayRemainder = ''
  private incidentCooldown = new Map<string, number>()
  private metricTimer: NodeJS.Timeout | null = null
  private eventRayTimer: NodeJS.Timeout | null = null

  start(): void {
    if (this.started) return
    this.started = true

    this.userData = app.getPath('userData')
    this.root = path.join(this.userData, 'observability')
    this.blackBoxPath = path.join(this.root, 'black-box.jsonl')
    this.incidentRoot = path.join(this.root, 'incidents')
    this.eventRayPath = path.join(this.userData, 'event-ray', 'focus-scroll-event-ray.jsonl')

    fs.mkdirSync(this.root, { recursive: true })
    fs.mkdirSync(this.incidentRoot, { recursive: true })

    this.record('lifecycle', 'runtime_start', {
      pid: process.pid,
      ppid: process.ppid,
      app_name: app.getName(),
      app_version: app.getVersion(),
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      node: process.versions.node,
      platform: process.platform,
      arch: process.arch,
      exec_path: process.execPath,
      app_path: app.getAppPath(),
      user_data: this.userData,
      event_ray_expected_path: this.eventRayPath,
      observability_generation: '000078V4',
    })

    this.record('lifecycle', 'feature_flags', {
      VERTEX_EVENT_RAY: process.env.VERTEX_EVENT_RAY ?? null,
      observability_core: true,
      auto_incident_from_event_ray: true,
    })

    this.installProcessObservers()
    this.startMetrics()
    this.startEventRayBridge()
    void this.captureRuntimeHashes()

    app.on('before-quit', () => {
      this.record('lifecycle', 'runtime_before_quit', { pid: process.pid })
      this.stopTimers()
    })
  }

  trace(
    event: string,
    payload: Record<string, unknown> = {},
    context: {
      correlation_id?: string
      session_id?: string
      job_id?: string
      lane_id?: string
    } = {},
  ): string {
    const correlationId = context.correlation_id ?? crypto.randomUUID()
    this.record('trace', event, payload, {
      ...context,
      correlation_id: correlationId,
    })
    return correlationId
  }

  stateTransition(
    stateName: string,
    from: unknown,
    to: unknown,
    payload: Record<string, unknown> = {},
    context: {
      correlation_id?: string
      session_id?: string
      job_id?: string
      lane_id?: string
    } = {},
  ): void {
    this.record('state', 'state_transition', {
      state_name: stateName,
      from,
      to,
      ...payload,
    }, context)
  }

  metric(name: string, value: number, payload: Record<string, unknown> = {}): void {
    this.record('metric', name, { value, ...payload })
  }

  markIncident(
    reason: string,
    trigger: Record<string, unknown> = {},
    correlationId?: string,
  ): string | null {
    const cooldownKey = `${reason}:${String(trigger.wc_id ?? '')}`
    const now = monoNow()
    const previous = this.incidentCooldown.get(cooldownKey) ?? 0

    if (now - previous < INCIDENT_COOLDOWN_MS) {
      this.record('incident', 'incident_suppressed_cooldown', {
        reason,
        cooldown_key: cooldownKey,
      }, { correlation_id: correlationId })
      return null
    }

    this.incidentCooldown.set(cooldownKey, now)

    const incidentId = `incident-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`
    const incidentDir = path.join(this.incidentRoot, incidentId)
    fs.mkdirSync(incidentDir, { recursive: true })

    const cutoff = now - 3 * 60 * 1000
    const flightRecorder = this.flight.filter((record) => record.mono_ms >= cutoff)
    const eventRayTail = this.collectEventRayTail(cutoff)

    const pack: VertexIncidentPack = {
      schema: 'vertex-session-portal/incident-evidence-pack-1',
      incident_id: incidentId,
      created_at: nowIso(),
      reason,
      correlation_id: correlationId,
      trigger: sanitizePayload(trigger) as Record<string, unknown>,
      runtime: {
        pid: process.pid,
        app_name: app.getName(),
        app_version: app.getVersion(),
        electron: process.versions.electron,
        node: process.versions.node,
        platform: process.platform,
        arch: process.arch,
        black_box_path: this.blackBoxPath,
        event_ray_path: this.eventRayPath,
        observability_generation: '000078V4',
      },
      flight_recorder: flightRecorder,
      event_ray_tail: eventRayTail,
    }

    const packPath = path.join(incidentDir, 'incident-evidence-pack.json')
    const flightPath = path.join(incidentDir, 'flight-recorder.jsonl')
    const eventRayEvidencePath = path.join(incidentDir, 'event-ray-tail.jsonl')

    fs.writeFileSync(packPath, JSON.stringify(pack, null, 2), 'utf8')
    fs.writeFileSync(
      flightPath,
      flightRecorder.map((r) => JSON.stringify(r)).join('\n') + '\n',
      'utf8',
    )
    fs.writeFileSync(
      eventRayEvidencePath,
      eventRayTail.map((r) => JSON.stringify(r)).join('\n') + '\n',
      'utf8',
    )

    this.record('incident', 'incident_evidence_packed', {
      incident_id: incidentId,
      reason,
      incident_dir: incidentDir,
      flight_records: flightRecorder.length,
      event_ray_records: eventRayTail.length,
    }, { correlation_id: correlationId })

    return incidentId
  }

  private record(
    kind: VertexObservationKind,
    event: string,
    payload: Record<string, unknown> = {},
    context: {
      correlation_id?: string
      session_id?: string
      job_id?: string
      lane_id?: string
    } = {},
  ): void {
    if (!this.started && kind !== 'lifecycle') return

    const record: VertexObservationRecord = {
      schema: SCHEMA,
      ts: nowIso(),
      mono_ms: monoNow(),
      kind,
      event,
      ...(context.correlation_id ? { correlation_id: context.correlation_id } : {}),
      ...(context.session_id ? { session_id: context.session_id } : {}),
      ...(context.job_id ? { job_id: context.job_id } : {}),
      ...(context.lane_id ? { lane_id: context.lane_id } : {}),
      payload: sanitizePayload(payload) as Record<string, unknown>,
    }

    this.flight.push(record)
    this.pruneFlight(record.mono_ms)

    try {
      this.rotateBlackBox()
      fs.appendFileSync(this.blackBoxPath, JSON.stringify(record) + '\n', 'utf8')
    } catch {
      // Observability must never crash the product.
    }
  }

  private pruneFlight(now: number): void {
    const cutoff = now - FLIGHT_WINDOW_MS
    let start = 0
    while (start < this.flight.length && this.flight[start].mono_ms < cutoff) start += 1
    if (start > 0) this.flight.splice(0, start)

    if (this.flight.length > FLIGHT_MAX_RECORDS) {
      this.flight.splice(0, this.flight.length - FLIGHT_MAX_RECORDS)
    }
  }

  private rotateBlackBox(): void {
    if (!fs.existsSync(this.blackBoxPath)) return
    if (fs.statSync(this.blackBoxPath).size < BLACK_BOX_MAX_BYTES) return

    for (let i = 3; i >= 1; i -= 1) {
      const src = `${this.blackBoxPath}.${i}`
      const dst = `${this.blackBoxPath}.${i + 1}`
      if (!fs.existsSync(src)) continue
      if (fs.existsSync(dst)) fs.unlinkSync(dst)
      fs.renameSync(src, dst)
    }

    const first = `${this.blackBoxPath}.1`
    if (fs.existsSync(first)) fs.unlinkSync(first)
    fs.renameSync(this.blackBoxPath, first)
  }

  private installProcessObservers(): void {
    process.on('uncaughtExceptionMonitor', (error, origin) => {
      this.record('error', 'uncaught_exception_monitor', {
        origin,
        error: safeError(error),
      })
      this.markIncident('uncaught_exception', {
        origin,
        error: safeError(error),
      })
    })

    process.on('warning', (warning) => {
      this.record('error', 'process_warning', {
        warning: safeError(warning),
      })
    })

    const appAny = app as any

    appAny.on?.('render-process-gone', (_event: unknown, webContents: any, details: any) => {
      const trigger = {
        wc_id: webContents?.id ?? null,
        reason: details?.reason ?? null,
        exit_code: details?.exitCode ?? null,
      }
      this.record('error', 'render_process_gone', trigger)
      this.markIncident('render_process_gone', trigger)
    })

    appAny.on?.('child-process-gone', (_event: unknown, details: any) => {
      const trigger = {
        type: details?.type ?? null,
        reason: details?.reason ?? null,
        exit_code: details?.exitCode ?? null,
        service_name: details?.serviceName ?? null,
      }
      this.record('error', 'child_process_gone', trigger)
      this.markIncident('child_process_gone', trigger)
    })
  }

  private startMetrics(): void {
    let expected = monoNow() + METRIC_INTERVAL_MS
    this.metricTimer = setInterval(() => {
      const now = monoNow()
      const lag = Math.max(0, now - expected)
      expected = now + METRIC_INTERVAL_MS

      const memory = process.memoryUsage()
      this.record('metric', 'runtime_sample', {
        event_loop_lag_ms: lag,
        rss_bytes: memory.rss,
        heap_used_bytes: memory.heapUsed,
        heap_total_bytes: memory.heapTotal,
        external_bytes: memory.external,
        flight_records: this.flight.length,
      })

      this.lastMetricAt = now
    }, METRIC_INTERVAL_MS)
    this.metricTimer.unref()
  }

  private startEventRayBridge(): void {
    try {
      if (fs.existsSync(this.eventRayPath)) {
        this.eventRayOffset = fs.statSync(this.eventRayPath).size
      }
    } catch {
      this.eventRayOffset = 0
    }

    this.record('event-ray', 'event_ray_bridge_started', {
      path: this.eventRayPath,
      initial_offset: this.eventRayOffset,
    })

    this.eventRayTimer = setInterval(() => this.pollEventRay(), EVENT_RAY_POLL_MS)
    this.eventRayTimer.unref()
  }

  private pollEventRay(): void {
    try {
      if (!fs.existsSync(this.eventRayPath)) return
      const stat = fs.statSync(this.eventRayPath)

      if (stat.size < this.eventRayOffset) {
        this.eventRayOffset = 0
        this.eventRayRemainder = ''
        this.record('event-ray', 'event_ray_rotation_detected', { size: stat.size })
      }

      if (stat.size === this.eventRayOffset) return

      const fd = fs.openSync(this.eventRayPath, 'r')
      try {
        const length = stat.size - this.eventRayOffset
        const buffer = Buffer.alloc(length)
        fs.readSync(fd, buffer, 0, length, this.eventRayOffset)
        this.eventRayOffset = stat.size
        this.consumeEventRayText(buffer.toString('utf8'))
      } finally {
        fs.closeSync(fd)
      }
    } catch (error) {
      this.record('error', 'event_ray_bridge_error', { error: safeError(error) })
    }
  }

  private consumeEventRayText(chunk: string): void {
    const text = this.eventRayRemainder + chunk
    const lines = text.split(/\r?\n/)
    this.eventRayRemainder = lines.pop() ?? ''

    const incidentTypes = new Set([
      'focus_authority_violation_candidate',
      'ime_composition_focus_loss_candidate',
      'ime_submit_collision_candidate',
      'ime_enter_during_composition',
      'scroll_backlash_candidate',
      'page:human_incident_marker',
    ])

    for (const line of lines) {
      if (!line.trim()) continue

      try {
        const parsed = JSON.parse(line) as Record<string, unknown>
        const type = typeof parsed.type === 'string' ? parsed.type : 'unknown'
        const safe = this.safeEventRayRecord(parsed)

        if (incidentTypes.has(type)) {
          this.record('event-ray', 'event_ray_incident_candidate', {
            candidate_type: type,
            record: safe,
          })

          this.markIncident(type, {
            wc_id: parsed.wc_id ?? null,
            source: 'event-ray',
            event: safe,
          })
        }
      } catch {
        // Ignore partial/corrupt line; Event Ray remains authoritative.
      }
    }
  }

  private safeEventRayRecord(parsed: Record<string, unknown>): Record<string, unknown> {
    const payload =
      parsed.payload && typeof parsed.payload === 'object'
        ? sanitizePayload(parsed.payload)
        : {}

    return {
      ts: parsed.ts ?? null,
      type: parsed.type ?? null,
      wc_id: parsed.wc_id ?? null,
      wc_type: parsed.wc_type ?? null,
      partition: parsed.partition ?? null,
      title: parsed.title ?? null,
      url: sanitizeUrl(parsed.url),
      payload,
    }
  }

  private collectEventRayTail(cutoffMono: number): Array<Record<string, unknown>> {
    const text = readTail(this.eventRayPath, EVENT_RAY_TAIL_BYTES)
    const records: Array<Record<string, unknown>> = []

    for (const line of text.split(/\r?\n/)) {
      if (!line.trim()) continue
      try {
        const parsed = JSON.parse(line) as Record<string, unknown>
        const mono = typeof parsed.mono_ms === 'number' ? parsed.mono_ms : 0
        if (mono > 0 && mono < cutoffMono) continue
        records.push(this.safeEventRayRecord(parsed))
      } catch {
        // Ignore malformed lines in evidence tail.
      }
    }

    return records.slice(-5000)
  }

  private async captureRuntimeHashes(): Promise<void> {
    const execHash = await sha256File(process.execPath)
    const packageJson = path.join(app.getAppPath(), 'package.json')
    const packageHash = fs.existsSync(packageJson) ? await sha256File(packageJson) : null

    this.record('lifecycle', 'runtime_fingerprint', {
      exec_sha256: execHash,
      package_json_sha256: packageHash,
      app_path: app.getAppPath(),
      observability_generation: '000078V4',
    })
  }

  private stopTimers(): void {
    if (this.metricTimer) clearInterval(this.metricTimer)
    if (this.eventRayTimer) clearInterval(this.eventRayTimer)
    this.metricTimer = null
    this.eventRayTimer = null
  }
}

export const vertexObservability = new VertexObservabilityCore()
