#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
MAIN = ROOT / "src" / "main" / "index.ts"
OBS_DIR = ROOT / "src" / "main" / "observability"
CORE = OBS_DIR / "vertex-observability-core.ts"
OBS_INDEX = OBS_DIR / "index.ts"
EVIDENCE_ROOT = ROOT / "EVIDENCE" / "OBSERVABILITY_CORE_FOUNDATION_000078V4"
IMPORT_LINE = "import './observability'"
CORE_TS = "import { app } from 'electron'\nimport * as crypto from 'node:crypto'\nimport * as fs from 'node:fs'\nimport * as path from 'node:path'\n\nexport type VertexObservationKind =\n  | 'lifecycle'\n  | 'trace'\n  | 'state'\n  | 'metric'\n  | 'incident'\n  | 'error'\n  | 'event-ray'\n\nexport type VertexObservationRecord = {\n  schema: 'vertex-session-portal/observability-record-1'\n  ts: string\n  mono_ms: number\n  kind: VertexObservationKind\n  event: string\n  correlation_id?: string\n  session_id?: string\n  job_id?: string\n  lane_id?: string\n  payload?: Record<string, unknown>\n}\n\nexport type VertexIncidentPack = {\n  schema: 'vertex-session-portal/incident-evidence-pack-1'\n  incident_id: string\n  created_at: string\n  reason: string\n  correlation_id?: string\n  trigger?: Record<string, unknown>\n  runtime: Record<string, unknown>\n  flight_recorder: VertexObservationRecord[]\n  event_ray_tail: Array<Record<string, unknown>>\n}\n\nconst SCHEMA = 'vertex-session-portal/observability-record-1' as const\nconst BLACK_BOX_MAX_BYTES = 25 * 1024 * 1024\nconst FLIGHT_WINDOW_MS = 5 * 60 * 1000\nconst FLIGHT_MAX_RECORDS = 20_000\nconst EVENT_RAY_TAIL_BYTES = 4 * 1024 * 1024\nconst METRIC_INTERVAL_MS = 5_000\nconst EVENT_RAY_POLL_MS = 750\nconst INCIDENT_COOLDOWN_MS = 10_000\n\nfunction nowIso(): string {\n  return new Date().toISOString()\n}\n\nfunction monoNow(): number {\n  return Date.now()\n}\n\nfunction safeError(error: unknown): Record<string, unknown> {\n  if (error instanceof Error) {\n    return {\n      name: error.name,\n      message: error.message,\n      stack_head: error.stack?.split('\\n').slice(0, 8).join('\\n') ?? null,\n    }\n  }\n  return { message: String(error) }\n}\n\nfunction sanitizeUrl(value: unknown): unknown {\n  if (typeof value !== 'string') return value\n  try {\n    const u = new URL(value)\n    u.search = ''\n    u.hash = ''\n    return u.toString()\n  } catch {\n    return value\n  }\n}\n\nfunction sanitizePayload(input: unknown, depth = 0): unknown {\n  if (depth > 5) return '<max-depth>'\n  if (input === null || input === undefined) return input\n  if (typeof input === 'number' || typeof input === 'boolean') return input\n  if (typeof input === 'string') {\n    return input.length > 512 ? `${input.slice(0, 512)}…` : input\n  }\n  if (Array.isArray(input)) {\n    return input.slice(0, 64).map((v) => sanitizePayload(v, depth + 1))\n  }\n  if (typeof input !== 'object') return String(input)\n\n  const source = input as Record<string, unknown>\n  const out: Record<string, unknown> = {}\n  for (const [key, value] of Object.entries(source)) {\n    const lk = key.toLowerCase()\n\n    if (\n      lk === 'text' ||\n      lk === 'value' ||\n      lk === 'prompt' ||\n      lk === 'message_content' ||\n      lk === 'innertext' ||\n      lk === 'textcontent' ||\n      lk === 'innerhtml' ||\n      lk === 'clipboard'\n    ) {\n      out[key] = '<redacted>'\n      continue\n    }\n\n    if (lk === 'url' || lk === 'href') {\n      out[key] = sanitizeUrl(value)\n      continue\n    }\n\n    out[key] = sanitizePayload(value, depth + 1)\n  }\n  return out\n}\n\nfunction readTail(pathname: string, maxBytes: number): string {\n  try {\n    const stat = fs.statSync(pathname)\n    const size = stat.size\n    const start = Math.max(0, size - maxBytes)\n    const fd = fs.openSync(pathname, 'r')\n    try {\n      const buffer = Buffer.alloc(size - start)\n      fs.readSync(fd, buffer, 0, buffer.length, start)\n      let text = buffer.toString('utf8')\n      if (start > 0) {\n        const firstNewline = text.indexOf('\\n')\n        if (firstNewline >= 0) text = text.slice(firstNewline + 1)\n      }\n      return text\n    } finally {\n      fs.closeSync(fd)\n    }\n  } catch {\n    return ''\n  }\n}\n\nasync function sha256File(pathname: string): Promise<string | null> {\n  return await new Promise((resolve) => {\n    try {\n      const hash = crypto.createHash('sha256')\n      const stream = fs.createReadStream(pathname)\n      stream.on('data', (chunk) => hash.update(chunk))\n      stream.on('error', () => resolve(null))\n      stream.on('end', () => resolve(hash.digest('hex')))\n    } catch {\n      resolve(null)\n    }\n  })\n}\n\nclass VertexObservabilityCore {\n  private started = false\n  private userData = ''\n  private root = ''\n  private blackBoxPath = ''\n  private incidentRoot = ''\n  private eventRayPath = ''\n  private flight: VertexObservationRecord[] = []\n  private lastMetricAt = monoNow()\n  private eventRayOffset = 0\n  private eventRayRemainder = ''\n  private incidentCooldown = new Map<string, number>()\n  private metricTimer: NodeJS.Timeout | null = null\n  private eventRayTimer: NodeJS.Timeout | null = null\n\n  start(): void {\n    if (this.started) return\n    this.started = true\n\n    this.userData = app.getPath('userData')\n    this.root = path.join(this.userData, 'observability')\n    this.blackBoxPath = path.join(this.root, 'black-box.jsonl')\n    this.incidentRoot = path.join(this.root, 'incidents')\n    this.eventRayPath = path.join(this.userData, 'event-ray', 'focus-scroll-event-ray.jsonl')\n\n    fs.mkdirSync(this.root, { recursive: true })\n    fs.mkdirSync(this.incidentRoot, { recursive: true })\n\n    this.record('lifecycle', 'runtime_start', {\n      pid: process.pid,\n      ppid: process.ppid,\n      app_name: app.getName(),\n      app_version: app.getVersion(),\n      electron: process.versions.electron,\n      chrome: process.versions.chrome,\n      node: process.versions.node,\n      platform: process.platform,\n      arch: process.arch,\n      exec_path: process.execPath,\n      app_path: app.getAppPath(),\n      user_data: this.userData,\n      event_ray_expected_path: this.eventRayPath,\n      observability_generation: '000078V4',\n    })\n\n    this.record('lifecycle', 'feature_flags', {\n      VERTEX_EVENT_RAY: process.env.VERTEX_EVENT_RAY ?? null,\n      observability_core: true,\n      auto_incident_from_event_ray: true,\n    })\n\n    this.installProcessObservers()\n    this.startMetrics()\n    this.startEventRayBridge()\n    void this.captureRuntimeHashes()\n\n    app.on('before-quit', () => {\n      this.record('lifecycle', 'runtime_before_quit', { pid: process.pid })\n      this.stopTimers()\n    })\n  }\n\n  trace(\n    event: string,\n    payload: Record<string, unknown> = {},\n    context: {\n      correlation_id?: string\n      session_id?: string\n      job_id?: string\n      lane_id?: string\n    } = {},\n  ): string {\n    const correlationId = context.correlation_id ?? crypto.randomUUID()\n    this.record('trace', event, payload, {\n      ...context,\n      correlation_id: correlationId,\n    })\n    return correlationId\n  }\n\n  stateTransition(\n    stateName: string,\n    from: unknown,\n    to: unknown,\n    payload: Record<string, unknown> = {},\n    context: {\n      correlation_id?: string\n      session_id?: string\n      job_id?: string\n      lane_id?: string\n    } = {},\n  ): void {\n    this.record('state', 'state_transition', {\n      state_name: stateName,\n      from,\n      to,\n      ...payload,\n    }, context)\n  }\n\n  metric(name: string, value: number, payload: Record<string, unknown> = {}): void {\n    this.record('metric', name, { value, ...payload })\n  }\n\n  markIncident(\n    reason: string,\n    trigger: Record<string, unknown> = {},\n    correlationId?: string,\n  ): string | null {\n    const cooldownKey = `${reason}:${String(trigger.wc_id ?? '')}`\n    const now = monoNow()\n    const previous = this.incidentCooldown.get(cooldownKey) ?? 0\n\n    if (now - previous < INCIDENT_COOLDOWN_MS) {\n      this.record('incident', 'incident_suppressed_cooldown', {\n        reason,\n        cooldown_key: cooldownKey,\n      }, { correlation_id: correlationId })\n      return null\n    }\n\n    this.incidentCooldown.set(cooldownKey, now)\n\n    const incidentId = `incident-${Date.now()}-${crypto.randomUUID().slice(0, 8)}`\n    const incidentDir = path.join(this.incidentRoot, incidentId)\n    fs.mkdirSync(incidentDir, { recursive: true })\n\n    const cutoff = now - 3 * 60 * 1000\n    const flightRecorder = this.flight.filter((record) => record.mono_ms >= cutoff)\n    const eventRayTail = this.collectEventRayTail(cutoff)\n\n    const pack: VertexIncidentPack = {\n      schema: 'vertex-session-portal/incident-evidence-pack-1',\n      incident_id: incidentId,\n      created_at: nowIso(),\n      reason,\n      correlation_id: correlationId,\n      trigger: sanitizePayload(trigger) as Record<string, unknown>,\n      runtime: {\n        pid: process.pid,\n        app_name: app.getName(),\n        app_version: app.getVersion(),\n        electron: process.versions.electron,\n        node: process.versions.node,\n        platform: process.platform,\n        arch: process.arch,\n        black_box_path: this.blackBoxPath,\n        event_ray_path: this.eventRayPath,\n        observability_generation: '000078V4',\n      },\n      flight_recorder: flightRecorder,\n      event_ray_tail: eventRayTail,\n    }\n\n    const packPath = path.join(incidentDir, 'incident-evidence-pack.json')\n    const flightPath = path.join(incidentDir, 'flight-recorder.jsonl')\n    const eventRayEvidencePath = path.join(incidentDir, 'event-ray-tail.jsonl')\n\n    fs.writeFileSync(packPath, JSON.stringify(pack, null, 2), 'utf8')\n    fs.writeFileSync(\n      flightPath,\n      flightRecorder.map((r) => JSON.stringify(r)).join('\\n') + '\\n',\n      'utf8',\n    )\n    fs.writeFileSync(\n      eventRayEvidencePath,\n      eventRayTail.map((r) => JSON.stringify(r)).join('\\n') + '\\n',\n      'utf8',\n    )\n\n    this.record('incident', 'incident_evidence_packed', {\n      incident_id: incidentId,\n      reason,\n      incident_dir: incidentDir,\n      flight_records: flightRecorder.length,\n      event_ray_records: eventRayTail.length,\n    }, { correlation_id: correlationId })\n\n    return incidentId\n  }\n\n  private record(\n    kind: VertexObservationKind,\n    event: string,\n    payload: Record<string, unknown> = {},\n    context: {\n      correlation_id?: string\n      session_id?: string\n      job_id?: string\n      lane_id?: string\n    } = {},\n  ): void {\n    if (!this.started && kind !== 'lifecycle') return\n\n    const record: VertexObservationRecord = {\n      schema: SCHEMA,\n      ts: nowIso(),\n      mono_ms: monoNow(),\n      kind,\n      event,\n      ...(context.correlation_id ? { correlation_id: context.correlation_id } : {}),\n      ...(context.session_id ? { session_id: context.session_id } : {}),\n      ...(context.job_id ? { job_id: context.job_id } : {}),\n      ...(context.lane_id ? { lane_id: context.lane_id } : {}),\n      payload: sanitizePayload(payload) as Record<string, unknown>,\n    }\n\n    this.flight.push(record)\n    this.pruneFlight(record.mono_ms)\n\n    try {\n      this.rotateBlackBox()\n      fs.appendFileSync(this.blackBoxPath, JSON.stringify(record) + '\\n', 'utf8')\n    } catch {\n      // Observability must never crash the product.\n    }\n  }\n\n  private pruneFlight(now: number): void {\n    const cutoff = now - FLIGHT_WINDOW_MS\n    let start = 0\n    while (start < this.flight.length && this.flight[start].mono_ms < cutoff) start += 1\n    if (start > 0) this.flight.splice(0, start)\n\n    if (this.flight.length > FLIGHT_MAX_RECORDS) {\n      this.flight.splice(0, this.flight.length - FLIGHT_MAX_RECORDS)\n    }\n  }\n\n  private rotateBlackBox(): void {\n    if (!fs.existsSync(this.blackBoxPath)) return\n    if (fs.statSync(this.blackBoxPath).size < BLACK_BOX_MAX_BYTES) return\n\n    for (let i = 3; i >= 1; i -= 1) {\n      const src = `${this.blackBoxPath}.${i}`\n      const dst = `${this.blackBoxPath}.${i + 1}`\n      if (!fs.existsSync(src)) continue\n      if (fs.existsSync(dst)) fs.unlinkSync(dst)\n      fs.renameSync(src, dst)\n    }\n\n    const first = `${this.blackBoxPath}.1`\n    if (fs.existsSync(first)) fs.unlinkSync(first)\n    fs.renameSync(this.blackBoxPath, first)\n  }\n\n  private installProcessObservers(): void {\n    process.on('uncaughtExceptionMonitor', (error, origin) => {\n      this.record('error', 'uncaught_exception_monitor', {\n        origin,\n        error: safeError(error),\n      })\n      this.markIncident('uncaught_exception', {\n        origin,\n        error: safeError(error),\n      })\n    })\n\n    process.on('warning', (warning) => {\n      this.record('error', 'process_warning', {\n        warning: safeError(warning),\n      })\n    })\n\n    const appAny = app as any\n\n    appAny.on?.('render-process-gone', (_event: unknown, webContents: any, details: any) => {\n      const trigger = {\n        wc_id: webContents?.id ?? null,\n        reason: details?.reason ?? null,\n        exit_code: details?.exitCode ?? null,\n      }\n      this.record('error', 'render_process_gone', trigger)\n      this.markIncident('render_process_gone', trigger)\n    })\n\n    appAny.on?.('child-process-gone', (_event: unknown, details: any) => {\n      const trigger = {\n        type: details?.type ?? null,\n        reason: details?.reason ?? null,\n        exit_code: details?.exitCode ?? null,\n        service_name: details?.serviceName ?? null,\n      }\n      this.record('error', 'child_process_gone', trigger)\n      this.markIncident('child_process_gone', trigger)\n    })\n  }\n\n  private startMetrics(): void {\n    let expected = monoNow() + METRIC_INTERVAL_MS\n    this.metricTimer = setInterval(() => {\n      const now = monoNow()\n      const lag = Math.max(0, now - expected)\n      expected = now + METRIC_INTERVAL_MS\n\n      const memory = process.memoryUsage()\n      this.record('metric', 'runtime_sample', {\n        event_loop_lag_ms: lag,\n        rss_bytes: memory.rss,\n        heap_used_bytes: memory.heapUsed,\n        heap_total_bytes: memory.heapTotal,\n        external_bytes: memory.external,\n        flight_records: this.flight.length,\n      })\n\n      this.lastMetricAt = now\n    }, METRIC_INTERVAL_MS)\n    this.metricTimer.unref()\n  }\n\n  private startEventRayBridge(): void {\n    try {\n      if (fs.existsSync(this.eventRayPath)) {\n        this.eventRayOffset = fs.statSync(this.eventRayPath).size\n      }\n    } catch {\n      this.eventRayOffset = 0\n    }\n\n    this.record('event-ray', 'event_ray_bridge_started', {\n      path: this.eventRayPath,\n      initial_offset: this.eventRayOffset,\n    })\n\n    this.eventRayTimer = setInterval(() => this.pollEventRay(), EVENT_RAY_POLL_MS)\n    this.eventRayTimer.unref()\n  }\n\n  private pollEventRay(): void {\n    try {\n      if (!fs.existsSync(this.eventRayPath)) return\n      const stat = fs.statSync(this.eventRayPath)\n\n      if (stat.size < this.eventRayOffset) {\n        this.eventRayOffset = 0\n        this.eventRayRemainder = ''\n        this.record('event-ray', 'event_ray_rotation_detected', { size: stat.size })\n      }\n\n      if (stat.size === this.eventRayOffset) return\n\n      const fd = fs.openSync(this.eventRayPath, 'r')\n      try {\n        const length = stat.size - this.eventRayOffset\n        const buffer = Buffer.alloc(length)\n        fs.readSync(fd, buffer, 0, length, this.eventRayOffset)\n        this.eventRayOffset = stat.size\n        this.consumeEventRayText(buffer.toString('utf8'))\n      } finally {\n        fs.closeSync(fd)\n      }\n    } catch (error) {\n      this.record('error', 'event_ray_bridge_error', { error: safeError(error) })\n    }\n  }\n\n  private consumeEventRayText(chunk: string): void {\n    const text = this.eventRayRemainder + chunk\n    const lines = text.split(/\\r?\\n/)\n    this.eventRayRemainder = lines.pop() ?? ''\n\n    const incidentTypes = new Set([\n      'focus_authority_violation_candidate',\n      'ime_composition_focus_loss_candidate',\n      'ime_submit_collision_candidate',\n      'ime_enter_during_composition',\n      'scroll_backlash_candidate',\n    ])\n\n    for (const line of lines) {\n      if (!line.trim()) continue\n\n      try {\n        const parsed = JSON.parse(line) as Record<string, unknown>\n        const type = typeof parsed.type === 'string' ? parsed.type : 'unknown'\n        const safe = this.safeEventRayRecord(parsed)\n\n        if (incidentTypes.has(type)) {\n          this.record('event-ray', 'event_ray_incident_candidate', {\n            candidate_type: type,\n            record: safe,\n          })\n\n          this.markIncident(type, {\n            wc_id: parsed.wc_id ?? null,\n            source: 'event-ray',\n            event: safe,\n          })\n        }\n      } catch {\n        // Ignore partial/corrupt line; Event Ray remains authoritative.\n      }\n    }\n  }\n\n  private safeEventRayRecord(parsed: Record<string, unknown>): Record<string, unknown> {\n    const payload =\n      parsed.payload && typeof parsed.payload === 'object'\n        ? sanitizePayload(parsed.payload)\n        : {}\n\n    return {\n      ts: parsed.ts ?? null,\n      type: parsed.type ?? null,\n      wc_id: parsed.wc_id ?? null,\n      wc_type: parsed.wc_type ?? null,\n      partition: parsed.partition ?? null,\n      title: parsed.title ?? null,\n      url: sanitizeUrl(parsed.url),\n      payload,\n    }\n  }\n\n  private collectEventRayTail(cutoffMono: number): Array<Record<string, unknown>> {\n    const text = readTail(this.eventRayPath, EVENT_RAY_TAIL_BYTES)\n    const records: Array<Record<string, unknown>> = []\n\n    for (const line of text.split(/\\r?\\n/)) {\n      if (!line.trim()) continue\n      try {\n        const parsed = JSON.parse(line) as Record<string, unknown>\n        const mono = typeof parsed.mono_ms === 'number' ? parsed.mono_ms : 0\n        if (mono > 0 && mono < cutoffMono) continue\n        records.push(this.safeEventRayRecord(parsed))\n      } catch {\n        // Ignore malformed lines in evidence tail.\n      }\n    }\n\n    return records.slice(-5000)\n  }\n\n  private async captureRuntimeHashes(): Promise<void> {\n    const execHash = await sha256File(process.execPath)\n    const packageJson = path.join(app.getAppPath(), 'package.json')\n    const packageHash = fs.existsSync(packageJson) ? await sha256File(packageJson) : null\n\n    this.record('lifecycle', 'runtime_fingerprint', {\n      exec_sha256: execHash,\n      package_json_sha256: packageHash,\n      app_path: app.getAppPath(),\n      observability_generation: '000078V4',\n    })\n  }\n\n  private stopTimers(): void {\n    if (this.metricTimer) clearInterval(this.metricTimer)\n    if (this.eventRayTimer) clearInterval(this.eventRayTimer)\n    this.metricTimer = null\n    this.eventRayTimer = null\n  }\n}\n\nexport const vertexObservability = new VertexObservabilityCore()\n"
OBS_INDEX_TS = "import { app } from 'electron'\nimport { vertexObservability } from './vertex-observability-core'\n\nlet activationRequested = false\n\nexport function activateVertexObservabilityCore(): void {\n  if (activationRequested) return\n  activationRequested = true\n\n  void app.whenReady().then(() => {\n    vertexObservability.start()\n  })\n}\n\nactivateVertexObservabilityCore()\n"

TSC_ERROR_RE = re.compile(
    r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.*)$"
)

def stamp():
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def sha256_path(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_typecheck():
    p = subprocess.run(
        ["npm.cmd", "run", "typecheck:node"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {"exit_code":p.returncode,"stdout":p.stdout,"stderr":p.stderr}

def diagnostics(run):
    out=[]
    for raw in (run["stdout"]+"\n"+run["stderr"]).splitlines():
        m=TSC_ERROR_RE.match(raw.strip())
        if not m:
            continue
        d=m.groupdict()
        out.append({
            "file":d["file"].replace("/","\\"),
            "line":int(d["line"]),
            "col":int(d["col"]),
            "code":d["code"],
            "msg":d["msg"],
        })
    return out

def diag_key(d):
    return (d["file"].lower(),d["line"],d["col"],d["code"],d["msg"])

def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".obs.tmp")
    tmp.write_text(text,encoding="utf-8")
    os.replace(tmp,path)

def restore(backups):
    for dst, info in backups.items():
        existed, backup = info
        if existed:
            shutil.copy2(backup,dst)
        elif dst.exists():
            dst.unlink()

def main():
    print("=== VERTEX SESSION PORTAL / OBSERVABILITY CORE FOUNDATION 000078V4 ===")

    if not ROOT.exists() or not MAIN.exists():
        print("PROJECT_PREFLIGHT=FAIL")
        return 2

    run_dir=EVIDENCE_ROOT/stamp()
    run_dir.mkdir(parents=True,exist_ok=True)

    baseline=run_typecheck()
    baseline_diags=diagnostics(baseline)
    (run_dir/"baseline-typecheck.stdout.txt").write_text(baseline["stdout"],encoding="utf-8")
    (run_dir/"baseline-typecheck.stderr.txt").write_text(baseline["stderr"],encoding="utf-8")

    targets=[MAIN,CORE,OBS_INDEX]
    backups={}
    for dst in targets:
        existed=dst.exists()
        backup=run_dir/(dst.name+".before")
        if existed:
            shutil.copy2(dst,backup)
        backups[dst]=(existed,backup)

    main_before=MAIN.read_text(encoding="utf-8-sig",errors="strict")
    main_hash_before=sha256_path(MAIN)

    if main_before.count(IMPORT_LINE)>1:
        print("OBS_IMPORT_DUPLICATE_PREEXISTING=FAIL")
        return 4

    atomic_write(CORE,CORE_TS)
    atomic_write(OBS_INDEX,OBS_INDEX_TS)

    if sha256_path(MAIN)!=main_hash_before:
        restore(backups)
        print("CONCURRENT_MAIN_CHANGE=FAIL_CLOSED")
        return 4

    current=MAIN.read_text(encoding="utf-8-sig",errors="strict")
    if IMPORT_LINE not in current:
        patched=current
        if not patched.endswith("\n"):
            patched+="\n"
        patched+="\n// VERTEX_OBSERVABILITY_CORE_000078V4\n"+IMPORT_LINE+"\n"
        atomic_write(MAIN,patched)

    post=run_typecheck()
    post_diags=diagnostics(post)
    (run_dir/"post-typecheck.stdout.txt").write_text(post["stdout"],encoding="utf-8")
    (run_dir/"post-typecheck.stderr.txt").write_text(post["stderr"],encoding="utf-8")

    baseline_keys={diag_key(x) for x in baseline_diags}
    new_diags=[x for x in post_diags if diag_key(x) not in baseline_keys]
    obs_diags=[
        x for x in post_diags
        if "\\src\\main\\observability\\" in ("\\"+x["file"].lower())
    ]

    if baseline["exit_code"]==0:
        acceptable=post["exit_code"]==0 and not post_diags
        mode="CLEAN_BASELINE_CLEAN_POST_REQUIRED"
    else:
        acceptable=(not new_diags) and (not obs_diags)
        mode="DIRTY_BASELINE_NO_NEW_DIAGNOSTIC_ALLOWED"

    if not acceptable:
        restore(backups)
        rp=run_dir/"observability_core_foundation_000078V4.json"
        rp.write_text(json.dumps({
            "status":"TYPECHECK_DELTA_FAILED_ROLLED_BACK",
            "baseline_exit":baseline["exit_code"],
            "post_exit":post["exit_code"],
            "new_diagnostics":new_diags,
            "observability_diagnostics":obs_diags,
            "comparison_mode":mode,
        },ensure_ascii=False,indent=2),encoding="utf-8")
        print("TYPECHECK_DELTA=FAIL")
        print(f"NEW_DIAGNOSTICS={len(new_diags)}")
        print(f"OBSERVABILITY_DIAGNOSTICS={len(obs_diags)}")
        for d in new_diags[:20]:
            print("NEW_TSC_ERROR="+json.dumps(d,ensure_ascii=False))
        print("TRANSACTION_ROLLBACK=PASS")
        print(f"EVIDENCE={rp}")
        return 5

    rp=run_dir/"observability_core_foundation_000078V4.json"
    rp.write_text(json.dumps({
        "schema":"vertex-session-portal/observability-core-install/1",
        "artifact":"vertex-session-portal-observability-core-foundation-000078V4",
        "status":"INSTALLED",
        "timestamp":dt.datetime.now().isoformat(),
        "comparison_mode":mode,
        "baseline_exit":baseline["exit_code"],
        "post_exit":post["exit_code"],
        "new_diagnostics":new_diags,
        "observability_diagnostics":obs_diags,
        "main_hash_before":main_hash_before,
        "main_hash_after":sha256_path(MAIN),
        "implemented":[
            "runtime_lifecycle_black_box",
            "runtime_fingerprint_hashes",
            "correlation_trace_api",
            "state_transition_journal",
            "performance_flight_recorder",
            "process_crash_observation",
            "event_ray_incident_bridge",
            "automatic_incident_evidence_packer",
            "log_rotation",
        ],
        "not_yet_wired":[
            "portal_vra_dispatch_correlation_binding",
            "workstation_job_evidence_correlation_binding",
            "human_incident_button",
            "renderer_ui",
        ],
        "runtime_paths":{
            "black_box":"app.getPath('userData')/observability/black-box.jsonl",
            "incidents":"app.getPath('userData')/observability/incidents/<incident_id>/",
        },
        "privacy":{
            "page_text_collected":False,
            "input_value_collected":False,
            "prompt_content_collected":False,
            "event_ray_url_query_preserved":False,
        },
        "behavior":{
            "auto_repair":False,
            "auto_apply":False,
            "focus_behavior_mutated":False,
            "ime_behavior_mutated":False,
            "scroll_behavior_mutated":False,
            "human_gate_mutated":False,
        },
        "restart_required":True,
    },ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"BASELINE_TYPECHECK_EXIT={baseline['exit_code']}")
    print(f"POST_TYPECHECK_EXIT={post['exit_code']}")
    print(f"TYPECHECK_COMPARISON_MODE={mode}")
    print("NEW_TYPESCRIPT_DIAGNOSTICS=0")
    print("OBSERVABILITY_TYPESCRIPT_DIAGNOSTICS=0")
    print("RUNTIME_LIFECYCLE_BLACK_BOX=IMPLEMENTED")
    print("CORRELATION_TRACE_API=IMPLEMENTED")
    print("STATE_TRANSITION_JOURNAL=IMPLEMENTED")
    print("PERFORMANCE_FLIGHT_RECORDER=IMPLEMENTED")
    print("EVENT_RAY_INCIDENT_BRIDGE=IMPLEMENTED")
    print("AUTOMATIC_INCIDENT_EVIDENCE_PACKER=IMPLEMENTED")
    print("PORTAL_WORKSTATION_CORRELATION_BINDING=NOT_YET_WIRED")
    print("HUMAN_INCIDENT_BUTTON=NOT_YET_WIRED")
    print("AUTO_REPAIR=FALSE")
    print("HUMAN_GATE_MUTATED=FALSE")
    print("RESTART_REQUIRED=TRUE")
    print(f"EVIDENCE={rp}")
    print("OBSERVABILITY_CORE_FOUNDATION_000078V4_APPLY=PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
