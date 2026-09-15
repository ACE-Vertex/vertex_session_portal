import Database from 'better-sqlite3'

import type { RegistryRecord } from './vra-registry-contract'
import { VRA_REGISTRY_SCHEMA } from './vra-registry-contract'
import type {
  VLogAppendStore,
  VLogEvent,
  VLogQuery,
  VLogQueryGate,
} from './vlog-contract'
import { validateVLogQuery } from './vlog-contract'
import type { VraRegistryStore } from './vra-registry-store'

type RegistryRow = {
  registry_id: string
  job_id: string
  artifact_id: string
  correlation_id: string
  dispatch_mode: 'AUTO'
  project_id: string | null
  project_name: string | null
  requested_lane: string | null
  lane_policy: 'ANY' | 'PREFER'
  parallelism: number
  worker_concurrency: number | null
  origin_vera: RegistryRecord['origin']['originVera']
  origin_session: RegistryRecord['origin']['originSession']
  origin_window: RegistryRecord['origin']['originWindow']
  return_channel: string
  state: RegistryRecord['state']
  allocated_lane: string | null
  evidence_id: string | null
  rerun_of_job_id: string | null
  created_utc: string
  updated_utc: string
}

type IdentityRow = Pick<
  RegistryRow,
  'registry_id' | 'job_id' | 'artifact_id' | 'correlation_id'
>

type VLogRow = {
  event_id: string
  kind: VLogEvent['kind']
  registry_id: string
  job_id: string
  artifact_id: string
  correlation_id: string
  occurred_utc: string
  state_from: string | null
  state_to: string | null
  evidence_id: string | null
  code: string | null
  note: string | null
}

const REGISTRY_SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS vra_registry (
  registry_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL UNIQUE,
  artifact_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  dispatch_mode TEXT NOT NULL CHECK (dispatch_mode = 'AUTO'),
  project_id TEXT NULL,
  project_name TEXT NULL,
  requested_lane TEXT NULL,
  lane_policy TEXT NOT NULL CHECK (lane_policy IN ('ANY', 'PREFER')),
  parallelism INTEGER NOT NULL CHECK (parallelism BETWEEN 1 AND 32),
  worker_concurrency INTEGER NULL,
  origin_vera TEXT NOT NULL,
  origin_session TEXT NOT NULL,
  origin_window TEXT NOT NULL,
  return_channel TEXT NOT NULL,
  state TEXT NOT NULL,
  allocated_lane TEXT NULL,
  evidence_id TEXT NULL,
  rerun_of_job_id TEXT NULL,
  created_utc TEXT NOT NULL,
  updated_utc TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vra_registry_artifact
  ON vra_registry (artifact_id);

CREATE INDEX IF NOT EXISTS idx_vra_registry_correlation
  ON vra_registry (correlation_id);

CREATE INDEX IF NOT EXISTS idx_vra_registry_state
  ON vra_registry (state, updated_utc);

CREATE TABLE IF NOT EXISTS vertex_vlog (
  event_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  kind TEXT NOT NULL,
  registry_id TEXT NOT NULL,
  job_id TEXT NOT NULL,
  artifact_id TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  occurred_utc TEXT NOT NULL,
  state_from TEXT NULL,
  state_to TEXT NULL,
  evidence_id TEXT NULL,
  code TEXT NULL,
  note TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_vertex_vlog_job
  ON vertex_vlog (job_id, occurred_utc);

CREATE INDEX IF NOT EXISTS idx_vertex_vlog_artifact
  ON vertex_vlog (artifact_id, occurred_utc);

CREATE INDEX IF NOT EXISTS idx_vertex_vlog_correlation
  ON vertex_vlog (correlation_id, occurred_utc);
`.trim()

function rowToRecord(row: RegistryRow): RegistryRecord {
  return {
    schema: VRA_REGISTRY_SCHEMA,
    dispatchMode: row.dispatch_mode,
    registryId: row.registry_id,
    jobId: row.job_id,
    artifactId: row.artifact_id,
    correlationId: row.correlation_id,
    projectId: row.project_id,
    projectName: row.project_name,
    requestedLane: row.requested_lane,
    lanePolicy: row.lane_policy,
    parallelism: row.parallelism,
    workerConcurrency: row.worker_concurrency,
    origin: {
      originVera: row.origin_vera,
      originSession: row.origin_session,
      originWindow: row.origin_window,
      returnChannel: row.return_channel,
    },
    state: row.state,
    allocatedLane: row.allocated_lane,
    evidenceId: row.evidence_id,
    rerunOfJobId: row.rerun_of_job_id,
    createdUtc: row.created_utc,
    updatedUtc: row.updated_utc,
  }
}

function rowToVLogEvent(row: VLogRow): VLogEvent {
  return {
    schema: 'vertex-session-portal/vlog/1',
    eventId: row.event_id,
    kind: row.kind,
    registryId: row.registry_id,
    jobId: row.job_id,
    artifactId: row.artifact_id,
    correlationId: row.correlation_id,
    occurredUtc: row.occurred_utc,
    stateFrom: row.state_from,
    stateTo: row.state_to,
    evidenceId: row.evidence_id,
    code: row.code,
    note: row.note,
  }
}

/**
 * Durable Registry department storage.
 *
 * This class owns persistence only. It does not allocate lanes, dispatch work,
 * approve work, mutate VRA manifests, or route Evidence to a Vera window.
 */
export class SqliteVraRegistryStore
  implements VraRegistryStore, VLogAppendStore, VLogQueryGate
{
  private readonly db: Database.Database

  constructor(filePath: string) {
    this.db = new Database(filePath)
    this.db.pragma('journal_mode = WAL')
    this.db.pragma('foreign_keys = ON')
    this.db.exec(REGISTRY_SCHEMA_SQL)
  }

  close(): void {
    this.db.close()
  }

  getByRegistryId(registryId: string): RegistryRecord | null {
    const row = this.db.prepare(`
      SELECT *
      FROM vra_registry
      WHERE registry_id = ?
    `).get(registryId) as RegistryRow | undefined

    return row ? rowToRecord(row) : null
  }

  getByJobId(jobId: string): RegistryRecord | null {
    const row = this.db.prepare(`
      SELECT *
      FROM vra_registry
      WHERE job_id = ?
    `).get(jobId) as RegistryRow | undefined

    return row ? rowToRecord(row) : null
  }

  put(record: RegistryRecord): void {
    this.assertIdentityCompatible(record)

    this.db.prepare(`
      INSERT INTO vra_registry (
        registry_id,
        job_id,
        artifact_id,
        correlation_id,
        dispatch_mode,
        project_id,
        project_name,
        requested_lane,
        lane_policy,
        parallelism,
        worker_concurrency,
        origin_vera,
        origin_session,
        origin_window,
        return_channel,
        state,
        allocated_lane,
        evidence_id,
        rerun_of_job_id,
        created_utc,
        updated_utc
      )
      VALUES (
        @registryId,
        @jobId,
        @artifactId,
        @correlationId,
        @dispatchMode,
        @projectId,
        @projectName,
        @requestedLane,
        @lanePolicy,
        @parallelism,
        @workerConcurrency,
        @originVera,
        @originSession,
        @originWindow,
        @returnChannel,
        @state,
        @allocatedLane,
        @evidenceId,
        @rerunOfJobId,
        @createdUtc,
        @updatedUtc
      )
      ON CONFLICT(registry_id) DO UPDATE SET
        state = excluded.state,
        allocated_lane = excluded.allocated_lane,
        evidence_id = excluded.evidence_id,
        updated_utc = excluded.updated_utc
    `).run({
      registryId: record.registryId,
      jobId: record.jobId,
      artifactId: record.artifactId,
      correlationId: record.correlationId,
      dispatchMode: record.dispatchMode,
      projectId: record.projectId,
      projectName: record.projectName,
      requestedLane: record.requestedLane,
      lanePolicy: record.lanePolicy,
      parallelism: record.parallelism,
      workerConcurrency: record.workerConcurrency,
      originVera: record.origin.originVera,
      originSession: record.origin.originSession,
      originWindow: record.origin.originWindow,
      returnChannel: record.origin.returnChannel,
      state: record.state,
      allocatedLane: record.allocatedLane,
      evidenceId: record.evidenceId,
      rerunOfJobId: record.rerunOfJobId,
      createdUtc: record.createdUtc,
      updatedUtc: record.updatedUtc,
    })
  }

  append(event: VLogEvent): void {
    this.db.prepare(`
      INSERT OR IGNORE INTO vertex_vlog (
        event_id,
        schema_version,
        kind,
        registry_id,
        job_id,
        artifact_id,
        correlation_id,
        occurred_utc,
        state_from,
        state_to,
        evidence_id,
        code,
        note
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      event.eventId,
      event.schema,
      event.kind,
      event.registryId,
      event.jobId,
      event.artifactId,
      event.correlationId,
      event.occurredUtc,
      event.stateFrom,
      event.stateTo,
      event.evidenceId,
      event.code,
      event.note,
    )
  }

  query(request: VLogQuery): readonly VLogEvent[] {
    const query = validateVLogQuery(request)
    const where: string[] = []
    const args: Array<string | number> = []

    if (query.jobId) {
      where.push('job_id = ?')
      args.push(query.jobId)
    }
    if (query.artifactId) {
      where.push('artifact_id = ?')
      args.push(query.artifactId)
    }
    if (query.correlationId) {
      where.push('correlation_id = ?')
      args.push(query.correlationId)
    }

    const rows = this.db.prepare(`
      SELECT
        event_id,
        kind,
        registry_id,
        job_id,
        artifact_id,
        correlation_id,
        occurred_utc,
        state_from,
        state_to,
        evidence_id,
        code,
        note
      FROM vertex_vlog
      WHERE ${where.join(' AND ')}
      ORDER BY occurred_utc DESC, event_id DESC
      LIMIT ?
    `).all(...args, query.limit) as VLogRow[]

    return rows.reverse().map(rowToVLogEvent)
  }

  private assertIdentityCompatible(record: RegistryRecord): void {
    const byRegistry = this.db.prepare(`
      SELECT registry_id, job_id, artifact_id, correlation_id
      FROM vra_registry
      WHERE registry_id = ?
    `).get(record.registryId) as IdentityRow | undefined

    const byJob = this.db.prepare(`
      SELECT registry_id, job_id, artifact_id, correlation_id
      FROM vra_registry
      WHERE job_id = ?
    `).get(record.jobId) as IdentityRow | undefined

    for (const existing of [byRegistry, byJob]) {
      if (!existing) continue
      if (
        existing.registry_id !== record.registryId ||
        existing.job_id !== record.jobId ||
        existing.artifact_id !== record.artifactId ||
        existing.correlation_id !== record.correlationId
      ) {
        throw new Error('REGISTRY_IDENTITY_CONFLICT')
      }
    }
  }
}

export { REGISTRY_SCHEMA_SQL }
