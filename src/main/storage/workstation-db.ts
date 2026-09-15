import Database from 'better-sqlite3'
import { createHash, randomUUID } from 'node:crypto'
import type {
  AiLaneId,
  AppendSessionMessageRequest,
  CreateVirtualArdHandoffRequest,
  HandoffKind,
  PortalBootstrapState,
  ProjectVirtualArdRequest,
  SaveVcaCuratorSettingsRequest,
  SessionKind,
  SessionMessage,
  SessionMessageActor,
  SessionState,
  SidebarTab,
  StorageStatus,
  UpsertVcrEntryRequest,
  AppendVcaMemoryEventRequest,
  AppendVcaWeightRevisionRequest,
  VcaCompensationPacket,
  VcaCaptureKind,
  VcaInboxEnqueueResult,
  VcaInboxItem,
  VcaInboxState,
  VcaCuratorMode,
  VcaCuratorSettings,
  VcaMemoryActor,
  UpdateVeraSessionThreadRequest,
  VeraSessionThreadBinding,
  EnqueueVcaInboxRequest,
  VcaMemoryClockState,
  VcaRecord,
  VcrEntry,
  VirtualArdHandoff,
  VirtualArdMission,
  VirtualArdProjection,
  VirtualArdRole,
  VirtualArdState
} from '../../shared/contracts'

export class WorkstationDb {
  private readonly db: Database.Database

  constructor(filePath: string) {
    this.db = new Database(filePath)
    this.db.pragma('journal_mode = WAL')
    this.db.pragma('foreign_keys = ON')
    this.initialize()
  }

  private initialize(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS portal_setting (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS session_state (
        session_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        kind TEXT NOT NULL,
        position INTEGER NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        priority INTEGER NOT NULL DEFAULT 0,
        updated_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS ard_mission (
        mission_id TEXT PRIMARY KEY,
        objective TEXT NOT NULL,
        created_utc TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS ard_projection (
        mission_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        brief TEXT NOT NULL,
        PRIMARY KEY (mission_id, session_id),
        FOREIGN KEY (mission_id)
          REFERENCES ard_mission(mission_id),
        FOREIGN KEY (session_id)
          REFERENCES session_state(session_id)
      );

      CREATE TABLE IF NOT EXISTS session_message (
        message_id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        actor TEXT NOT NULL,
        body TEXT NOT NULL,
        created_utc TEXT NOT NULL,
        FOREIGN KEY (mission_id)
          REFERENCES ard_mission(mission_id),
        FOREIGN KEY (session_id)
          REFERENCES session_state(session_id)
      );

      CREATE INDEX IF NOT EXISTS idx_session_message_context
        ON session_message (mission_id, session_id, created_utc);

      CREATE TABLE IF NOT EXISTS ard_handoff (
        handoff_id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL,
        from_session_id TEXT NOT NULL,
        to_session_id TEXT NOT NULL,
        kind TEXT NOT NULL,
        body TEXT NOT NULL,
        created_utc TEXT NOT NULL,
        FOREIGN KEY (mission_id)
          REFERENCES ard_mission(mission_id),
        FOREIGN KEY (from_session_id)
          REFERENCES session_state(session_id),
        FOREIGN KEY (to_session_id)
          REFERENCES session_state(session_id)
      );

      CREATE INDEX IF NOT EXISTS idx_ard_handoff_flow
        ON ard_handoff (
          mission_id,
          from_session_id,
          to_session_id,
          created_utc
        );


CREATE TABLE IF NOT EXISTS session_chat_message (
  message_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  body TEXT NOT NULL,
  created_utc TEXT NOT NULL,
  FOREIGN KEY (session_id)
    REFERENCES session_state(session_id)
);

CREATE INDEX IF NOT EXISTS idx_vca_session_chat
  ON session_chat_message (session_id, created_utc, message_id);

CREATE TABLE IF NOT EXISTS vcr_revision (
  canonical_key TEXT NOT NULL,
  revision INTEGER NOT NULL,
  title TEXT NOT NULL,
  category TEXT NOT NULL,
  status TEXT NOT NULL,
  body TEXT NOT NULL,
  recorded_utc TEXT NOT NULL,
  PRIMARY KEY (canonical_key, revision)
);

CREATE INDEX IF NOT EXISTS idx_vcr_revision_recorded
  ON vcr_revision (recorded_utc DESC, canonical_key ASC, revision DESC);

CREATE TABLE IF NOT EXISTS vca_memory_event (
  memory_revision INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  session_id TEXT NOT NULL,
  actor TEXT NOT NULL,
  body TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_ref TEXT,
  created_utc TEXT NOT NULL,
  FOREIGN KEY (session_id)
    REFERENCES session_state(session_id)
);

CREATE INDEX IF NOT EXISTS idx_vca_memory_event_session
  ON vca_memory_event (session_id, memory_revision);
CREATE INDEX IF NOT EXISTS idx_vca_memory_event_created
  ON vca_memory_event (created_utc DESC, memory_revision DESC);

CREATE TABLE IF NOT EXISTS vca_weight_revision (
  event_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  human_signal REAL NOT NULL,
  vera_signal REAL NOT NULL,
  mutual_signal REAL NOT NULL,
  purpose_relation REAL NOT NULL,
  implementation_link REAL NOT NULL,
  recurrence REAL NOT NULL,
  novelty REAL NOT NULL,
  confidence REAL NOT NULL,
  memory_gravity REAL NOT NULL,
  curator TEXT NOT NULL,
  rationale TEXT NOT NULL,
  recorded_utc TEXT NOT NULL,
  PRIMARY KEY (event_id, revision),
  FOREIGN KEY (event_id)
    REFERENCES vca_memory_event(event_id)
);

CREATE INDEX IF NOT EXISTS idx_vca_weight_gravity
  ON vca_weight_revision (memory_gravity DESC, event_id, revision DESC);

CREATE TABLE IF NOT EXISTS vera_memory_clock (
  session_id TEXT PRIMARY KEY,
  observed_revision INTEGER NOT NULL DEFAULT 0,
  compensated_revision INTEGER NOT NULL DEFAULT 0,
  updated_utc TEXT NOT NULL,
  FOREIGN KEY (session_id)
    REFERENCES session_state(session_id)
);

CREATE TABLE IF NOT EXISTS vera_session_thread (
  session_id TEXT PRIMARY KEY,
  thread_url TEXT NOT NULL,
  thread_key TEXT NOT NULL,
  updated_utc TEXT NOT NULL,
  FOREIGN KEY (session_id)
    REFERENCES session_state(session_id)
);

CREATE TABLE IF NOT EXISTS vca_memory_inbox (
  inbox_id TEXT PRIMARY KEY,
  fingerprint TEXT NOT NULL UNIQUE,
  session_id TEXT NOT NULL,
  thread_url TEXT NOT NULL,
  thread_key TEXT NOT NULL,
  actor TEXT NOT NULL,
  body TEXT NOT NULL,
  capture_kind TEXT NOT NULL,
  source_ref TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING',
  promoted_event_id TEXT,
  duplicate_hits INTEGER NOT NULL DEFAULT 0,
  created_utc TEXT NOT NULL,
  processed_utc TEXT,
  FOREIGN KEY (session_id)
    REFERENCES session_state(session_id),
  FOREIGN KEY (promoted_event_id)
    REFERENCES vca_memory_event(event_id)
);

CREATE INDEX IF NOT EXISTS idx_vca_memory_inbox_status
  ON vca_memory_inbox (status, created_utc DESC, inbox_id);
CREATE INDEX IF NOT EXISTS idx_vca_memory_inbox_thread
  ON vca_memory_inbox (session_id, thread_key, created_utc DESC);

CREATE TABLE IF NOT EXISTS vca_memory_relation (
  relation_id TEXT PRIMARY KEY,
  left_event_id TEXT NOT NULL,
  right_event_id TEXT NOT NULL,
  relation_kind TEXT NOT NULL,
  strength REAL NOT NULL,
  curator TEXT NOT NULL,
  created_utc TEXT NOT NULL,
  UNIQUE (left_event_id, right_event_id, relation_kind),
  FOREIGN KEY (left_event_id)
    REFERENCES vca_memory_event(event_id),
  FOREIGN KEY (right_event_id)
    REFERENCES vca_memory_event(event_id)
);
    `)

    const insert = this.db.prepare(`
      INSERT OR IGNORE INTO session_state
      (
        session_id,
        title,
        kind,
        position,
        active,
        priority,
        updated_utc
      )
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `)

    const now = new Date().toISOString()

    const seed: Array<
      [
        string,
        string,
        SessionKind,
        number,
        number,
        number,
        string
      ]
    > = [
      ['vera-01', 'Vera 01', 'MAIN', 1, 1, 0, now],
      ['vera-02', 'Vera 02', 'MAIN', 2, 1, 1, now],
      ['vera-03', 'Vera 03', 'MAIN', 3, 1, 0, now],
      ['vera-04', 'Vera 04', 'MAIN', 4, 0, 0, now],
      ['vera-05', 'Vera 05', 'MAIN', 5, 0, 0, now],
      ['vera-search', 'Search Vera', 'SEARCH', 6, 1, 0, now]
    ]

    this.db.transaction(() => {
      for (const row of seed) insert.run(...row)

      this.db.prepare(`
        UPDATE session_state
        SET position = 6, updated_utc = ?
        WHERE session_id = 'vera-search'
          AND position <> 6
      `).run(now)

      this.db.prepare(`
        INSERT OR IGNORE INTO portal_setting
        (key, value)
        VALUES ('sidebar_tab', 'PROJECT')
      `).run()

      this.db.prepare(`
        INSERT OR IGNORE INTO portal_setting
        (key, value)
        VALUES ('vca_curator_lane', 'lane-4')
      `).run()

      this.db.prepare(`
        INSERT OR IGNORE INTO portal_setting
        (key, value)
        VALUES ('vca_curator_auto', '0')
      `).run()

      this.db.prepare(`
        INSERT OR IGNORE INTO portal_setting
        (key, value)
        VALUES ('vca_curator_batch', '8')
      `).run()
    })()

    this.initializeVcaMemoryLayer()
  }

  private initializeVcaMemoryLayer(): void {
    const now = new Date().toISOString()

    this.db.transaction(() => {
      this.db.prepare(`
        INSERT OR IGNORE INTO vca_memory_event
        (event_id, session_id, actor, body, source_kind, source_ref, created_utc)
        SELECT
          message_id,
          session_id,
          CASE role WHEN 'USER' THEN 'HUMAN' ELSE 'VERA' END,
          body,
          'PORTAL_CHAT',
          message_id,
          created_utc
        FROM session_chat_message
        ORDER BY created_utc ASC, message_id ASC
      `).run()

      this.db.prepare(`
        INSERT OR IGNORE INTO vera_memory_clock
        (session_id, observed_revision, compensated_revision, updated_utc)
        SELECT session_id, 0, 0, ?
        FROM session_state
        WHERE kind = 'MAIN'
      `).run(now)


      this.db.prepare(`
        INSERT OR IGNORE INTO vera_session_thread
        (session_id, thread_url, thread_key, updated_utc)
        SELECT session_id, 'https://chatgpt.com/', '/', ?
        FROM session_state
        WHERE kind = 'MAIN'
      `).run(now)

      this.db.prepare(`
        UPDATE vera_memory_clock
        SET observed_revision = MAX(
              observed_revision,
              COALESCE((
                SELECT MAX(memory_revision)
                FROM vca_memory_event AS e
                WHERE e.session_id = vera_memory_clock.session_id
              ), 0)
            ),
            updated_utc = ?
      `).run(now)
    })()

    const unweighted = this.db.prepare(`
      SELECT event_id AS id, actor, body
      FROM vca_memory_event AS e
      WHERE NOT EXISTS (
        SELECT 1 FROM vca_weight_revision AS w
        WHERE w.event_id = e.event_id
      )
      ORDER BY memory_revision ASC
    `).all() as Array<{ id: string; actor: VcaMemoryActor; body: string }>

    for (const event of unweighted) {
      const seed = this.seedVcaWeight(event.actor, event.body)
      this.insertVcaWeightRevision(event.id, seed, 'DETERMINISTIC_SEED', 'Initial deterministic memory-gravity seed; AI Assistant may append a later revision.')
    }
  }

  getBootstrapState(): PortalBootstrapState {
    const setting = this.db
      .prepare(`
        SELECT value
        FROM portal_setting
        WHERE key = 'sidebar_tab'
      `)
      .get() as { value?: string } | undefined

    const rows = this.db
      .prepare(`
        SELECT
          session_id AS id,
          title,
          kind,
          position,
          active,
          priority
        FROM session_state
        ORDER BY position ASC
      `)
      .all() as Array<{
        id: string
        title: string
        kind: SessionKind
        position: number
        active: number
        priority: number
      }>

    return {
      sidebarTab:
        this.normalizeSidebarTab(
          setting?.value
        ),
      sessions:
        rows.map(
          (row): SessionState => ({
            ...row,
            active: Boolean(row.active),
            priority: Boolean(row.priority)
          })
        ),
      virtualArd:
        this.getVirtualArdState()
    }
  }

  activateNextMainLane(): PortalBootstrapState {
    const next = this.db.prepare(`
      SELECT session_id AS id
      FROM session_state
      WHERE kind = 'MAIN'
        AND active = 0
      ORDER BY position ASC
      LIMIT 1
    `).get() as { id: string } | undefined

    if (!next) return this.getBootstrapState()

    this.db.prepare(`
      UPDATE session_state
      SET active = 1,
          updated_utc = ?
      WHERE session_id = ?
    `).run(new Date().toISOString(), next.id)

    return this.getBootstrapState()
  }

  setPrioritySession(
    sessionId: string
  ): PortalBootstrapState {
    this.assertSessionExists(
      sessionId
    )

    this.db.transaction(() => {
      const now =
        new Date().toISOString()

      this.db
        .prepare(`
          UPDATE session_state
          SET priority = 0,
              updated_utc = ?
        `)
        .run(now)

      this.db
        .prepare(`
          UPDATE session_state
          SET priority = 1,
              updated_utc = ?
          WHERE session_id = ?
        `)
        .run(
          now,
          sessionId
        )
    })()

    return this.getBootstrapState()
  }

  setSidebarTab(
    tab: SidebarTab
  ): void {
    this.db
      .prepare(`
        INSERT INTO portal_setting
        (key, value)
        VALUES ('sidebar_tab', ?)
        ON CONFLICT(key)
        DO UPDATE SET
          value = excluded.value
      `)
      .run(tab)
  }

  projectVirtualArd(
    request: ProjectVirtualArdRequest
  ): VirtualArdState {
    const objective =
      this.requireText(
        request.objective,
        'ARD_OBJECTIVE',
        8000
      )

    if (
      !Array.isArray(
        request.assignments
      ) ||
      request.assignments.length !== 3
    ) {
      throw new Error(
        'ARD_REQUIRES_EXACTLY_THREE_MAIN_ASSIGNMENTS'
      )
    }

    const sessionIds =
      request.assignments.map(
        (item) => item.sessionId
      )

    if (
      new Set(
        sessionIds
      ).size !== 3
    ) {
      throw new Error(
        'ARD_ASSIGNMENT_SESSION_DUPLICATE'
      )
    }

    const roles =
      request.assignments.map(
        (item) => item.role
      )

    if (
      new Set(
        roles
      ).size !== 3
    ) {
      throw new Error(
        'ARD_ASSIGNMENT_ROLE_DUPLICATE'
      )
    }

    const requiredRoles:
      VirtualArdRole[] = [
        'ARCHITECT',
        'DEVELOPER',
        'REVIEWER'
      ]

    for (
      const role of requiredRoles
    ) {
      if (!roles.includes(role)) {
        throw new Error(
          `ARD_REQUIRED_ROLE_MISSING:${role}`
        )
      }
    }

    for (
      const assignment
      of request.assignments
    ) {
      this.assertMainSession(
        assignment.sessionId
      )

      this.requireText(
        assignment.brief,
        'ARD_BRIEF',
        8000
      )
    }

    const missionId =
      randomUUID()

    const createdUtc =
      new Date().toISOString()

    this.db.transaction(() => {
      this.db
        .prepare(`
          INSERT INTO ard_mission
          (
            mission_id,
            objective,
            created_utc
          )
          VALUES (?, ?, ?)
        `)
        .run(
          missionId,
          objective,
          createdUtc
        )

      const insertProjection =
        this.db.prepare(`
          INSERT INTO ard_projection
          (
            mission_id,
            session_id,
            role,
            brief
          )
          VALUES (?, ?, ?, ?)
        `)

      for (
        const assignment
        of request.assignments
      ) {
        insertProjection.run(
          missionId,
          assignment.sessionId,
          assignment.role,
          assignment.brief
        )
      }

      this.db
        .prepare(`
          INSERT INTO portal_setting
          (key, value)
          VALUES (
            'active_ard_mission_id',
            ?
          )
          ON CONFLICT(key)
          DO UPDATE SET
            value = excluded.value
        `)
        .run(missionId)
    })()

    return this.requireVirtualArdState(
      missionId
    )
  }

  appendSessionMessage(
    request: AppendSessionMessageRequest
  ): SessionMessage {
    this.assertMissionExists(
      request.missionId
    )

    this.assertSessionExists(
      request.sessionId
    )

    const actor =
      this.normalizeActor(
        request.actor
      )

    const body =
      this.requireText(
        request.body,
        'SESSION_MESSAGE_BODY',
        20000
      )

    const message: SessionMessage = {
      id: randomUUID(),
      missionId: request.missionId,
      sessionId: request.sessionId,
      actor,
      body,
      createdUtc:
        new Date().toISOString()
    }

    this.db
      .prepare(`
        INSERT INTO session_message
        (
          message_id,
          mission_id,
          session_id,
          actor,
          body,
          created_utc
        )
        VALUES (?, ?, ?, ?, ?, ?)
      `)
      .run(
        message.id,
        message.missionId,
        message.sessionId,
        message.actor,
        message.body,
        message.createdUtc
      )

    return message
  }

  createVirtualArdHandoff(
    request:
      CreateVirtualArdHandoffRequest
  ): VirtualArdHandoff {
    this.assertMissionExists(
      request.missionId
    )

    this.assertProjectedSession(
      request.missionId,
      request.fromSessionId
    )

    this.assertProjectedSession(
      request.missionId,
      request.toSessionId
    )

    if (
      request.fromSessionId ===
      request.toSessionId
    ) {
      throw new Error(
        'ARD_HANDOFF_SELF_TARGET_REJECTED'
      )
    }

    const handoff:
      VirtualArdHandoff = {
        id: randomUUID(),
        missionId:
          request.missionId,
        fromSessionId:
          request.fromSessionId,
        toSessionId:
          request.toSessionId,
        kind:
          this.normalizeHandoffKind(
            request.kind
          ),
        body:
          this.requireText(
            request.body,
            'ARD_HANDOFF_BODY',
            20000
          ),
        createdUtc:
          new Date().toISOString()
      }

    this.db
      .prepare(`
        INSERT INTO ard_handoff
        (
          handoff_id,
          mission_id,
          from_session_id,
          to_session_id,
          kind,
          body,
          created_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
      `)
      .run(
        handoff.id,
        handoff.missionId,
        handoff.fromSessionId,
        handoff.toSessionId,
        handoff.kind,
        handoff.body,
        handoff.createdUtc
      )

    return handoff
  }

  getVirtualArdState(
    missionId?: string
  ): VirtualArdState | null {
    const resolvedMissionId =
      missionId ??
      this.getSetting(
        'active_ard_mission_id'
      )

    if (!resolvedMissionId) {
      return null
    }

    const missionRow =
      this.db
        .prepare(`
          SELECT
            mission_id AS id,
            objective,
            created_utc AS createdUtc
          FROM ard_mission
          WHERE mission_id = ?
        `)
        .get(
          resolvedMissionId
        ) as
          | VirtualArdMission
          | undefined

    if (!missionRow) {
      return null
    }

    const projections =
      this.db
        .prepare(`
          SELECT
            mission_id AS missionId,
            session_id AS sessionId,
            role,
            brief
          FROM ard_projection
          WHERE mission_id = ?
          ORDER BY session_id ASC
        `)
        .all(
          resolvedMissionId
        ) as VirtualArdProjection[]

    const messages =
      this.db
        .prepare(`
          SELECT
            message_id AS id,
            mission_id AS missionId,
            session_id AS sessionId,
            actor,
            body,
            created_utc AS createdUtc
          FROM session_message
          WHERE mission_id = ?
          ORDER BY
            created_utc ASC,
            message_id ASC
        `)
        .all(
          resolvedMissionId
        ) as SessionMessage[]

    const handoffs =
      this.db
        .prepare(`
          SELECT
            handoff_id AS id,
            mission_id AS missionId,
            from_session_id AS fromSessionId,
            to_session_id AS toSessionId,
            kind,
            body,
            created_utc AS createdUtc
          FROM ard_handoff
          WHERE mission_id = ?
          ORDER BY
            created_utc ASC,
            handoff_id ASC
        `)
        .all(
          resolvedMissionId
        ) as VirtualArdHandoff[]

    return {
      mission:
        missionRow,
      projections,
      messages,
      handoffs
    }
  }


storageStatus(): StorageStatus {
  const vcrCount = (
    this.db.prepare('SELECT COUNT(DISTINCT canonical_key) AS count FROM vcr_revision').get() as { count: number }
  ).count

  const vcaCount = (
    this.db.prepare('SELECT COUNT(*) AS count FROM vca_memory_event').get() as { count: number }
  ).count

  return {
    sqliteConnected: true,
    vcrReady: true,
    vcaReady: true,
    vcrCount,
    vcaCount
  }
}

searchVcr(query = '', limit = 60): VcrEntry[] {
  const normalized = query.trim()
  const safeLimit = Math.min(Math.max(Math.trunc(limit), 1), 200)
  const filter = normalized
    ? `WHERE current.canonical_key LIKE ? COLLATE NOCASE
       OR current.title LIKE ? COLLATE NOCASE
       OR current.category LIKE ? COLLATE NOCASE
       OR current.status LIKE ? COLLATE NOCASE
       OR current.body LIKE ? COLLATE NOCASE`
    : ''

  const sql = `
    WITH summary AS (
      SELECT
        canonical_key,
        MAX(revision) AS current_revision,
        MIN(recorded_utc) AS first_created_utc
      FROM vcr_revision
      GROUP BY canonical_key
    )
    SELECT
      current.canonical_key AS key,
      current.title,
      current.category,
      current.status,
      current.body,
      current.revision,
      summary.first_created_utc AS createdUtc,
      current.recorded_utc AS updatedUtc
    FROM vcr_revision AS current
    INNER JOIN summary
      ON summary.canonical_key = current.canonical_key
     AND summary.current_revision = current.revision
    ${filter}
    ORDER BY current.recorded_utc DESC, current.canonical_key ASC
    LIMIT ?
  `

  if (!normalized) {
    return this.db.prepare(sql).all(safeLimit) as VcrEntry[]
  }

  const like = `%${normalized}%`
  return this.db.prepare(sql).all(like, like, like, like, like, safeLimit) as VcrEntry[]
}

upsertVcrEntry(request: UpsertVcrEntryRequest): VcrEntry {
  const key = this.requireText(request.key, 'VCR_KEY', 240)
  const title = this.requireText(request.title, 'VCR_TITLE', 500)
  const category = this.requireText(request.category, 'VCR_CATEGORY', 120)
  const status = this.requireText(request.status, 'VCR_STATUS', 80)
  const body = this.requireText(request.body, 'VCR_BODY', 100000)
  const now = new Date().toISOString()

  this.db.transaction(() => {
    const row = this.db.prepare(`
      SELECT COALESCE(MAX(revision), 0) AS revision
      FROM vcr_revision
      WHERE canonical_key = ?
    `).get(key) as { revision: number }

    const nextRevision = row.revision + 1

    this.db.prepare(`
      INSERT INTO vcr_revision
      (canonical_key, revision, title, category, status, body, recorded_utc)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(key, nextRevision, title, category, status, body, now)
  })()

  const result = this.searchVcr(key, 200).find(entry => entry.key === key)
  if (!result) throw new Error(`VCR_WRITE_NOT_VISIBLE:${key}`)
  return result
}

searchVca(query = '', limit = 100): VcaRecord[] {
  const normalized = query.trim()
  const safeLimit = Math.min(Math.max(Math.trunc(limit), 1), 300)
  const params: Array<string | number> = []
  const filter = normalized
    ? `WHERE e.body LIKE ? COLLATE NOCASE
       OR s.title LIKE ? COLLATE NOCASE
       OR e.session_id LIKE ? COLLATE NOCASE
       OR e.source_kind LIKE ? COLLATE NOCASE
       OR COALESCE(w.rationale, '') LIKE ? COLLATE NOCASE`
    : ''

  if (normalized) {
    const like = `%${normalized}%`
    params.push(like, like, like, like, like)
  }

  params.push(safeLimit)

  return this.db.prepare(`
    WITH current_weight AS (
      SELECT wr.*
      FROM vca_weight_revision AS wr
      INNER JOIN (
        SELECT event_id, MAX(revision) AS current_revision
        FROM vca_weight_revision
        GROUP BY event_id
      ) AS latest
        ON latest.event_id = wr.event_id
       AND latest.current_revision = wr.revision
    )
    SELECT
      e.event_id AS id,
      e.memory_revision AS memoryRevision,
      e.session_id AS sessionId,
      COALESCE(s.title, e.session_id) AS sessionTitle,
      CASE e.actor WHEN 'HUMAN' THEN 'USER' ELSE 'ASSISTANT' END AS role,
      e.actor AS actor,
      e.body AS body,
      e.source_kind AS sourceKind,
      e.source_ref AS sourceRef,
      COALESCE(w.revision, 0) AS weightRevision,
      COALESCE(w.human_signal, 0) AS humanSignal,
      COALESCE(w.vera_signal, 0) AS veraSignal,
      COALESCE(w.mutual_signal, 0) AS mutualSignal,
      COALESCE(w.purpose_relation, 0) AS purposeRelation,
      COALESCE(w.implementation_link, 0) AS implementationLink,
      COALESCE(w.recurrence, 0) AS recurrence,
      COALESCE(w.novelty, 0) AS novelty,
      COALESCE(w.confidence, 0) AS confidence,
      COALESCE(w.memory_gravity, 0) AS memoryGravity,
      COALESCE(w.curator, 'UNWEIGHTED') AS curator,
      COALESCE(w.rationale, '') AS rationale,
      e.created_utc AS createdUtc,
      COALESCE(w.recorded_utc, e.created_utc) AS weightedUtc
    FROM vca_memory_event AS e
    LEFT JOIN session_state AS s
      ON s.session_id = e.session_id
    LEFT JOIN current_weight AS w
      ON w.event_id = e.event_id
    ${filter}
    ORDER BY
      COALESCE(w.memory_gravity, 0) DESC,
      e.memory_revision DESC
    LIMIT ?
  `).all(...params) as VcaRecord[]
}

appendVcaMemoryEvent(request: AppendVcaMemoryEventRequest): VcaRecord {
  this.assertSessionExists(request.sessionId)
  const actor = this.normalizeVcaActor(request.actor)
  const body = this.requireText(request.body, 'VCA_MEMORY_BODY', 120000)
  const sourceKind = this.requireText(request.sourceKind, 'VCA_SOURCE_KIND', 80)
  const sourceRef = typeof request.sourceRef === 'string' && request.sourceRef.trim()
    ? request.sourceRef.trim().slice(0, 4096)
    : null
  const createdUtc = typeof request.createdUtc === 'string' && request.createdUtc.trim()
    ? request.createdUtc.trim().slice(0, 80)
    : new Date().toISOString()
  const eventId = randomUUID()

  const revision = this.db.transaction(() => {
    const result = this.db.prepare(`
      INSERT INTO vca_memory_event
      (event_id, session_id, actor, body, source_kind, source_ref, created_utc)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(eventId, request.sessionId, actor, body, sourceKind, sourceRef, createdUtc)

    const memoryRevision = Number(result.lastInsertRowid)
    const now = new Date().toISOString()
    this.db.prepare(`
      INSERT INTO vera_memory_clock
      (session_id, observed_revision, compensated_revision, updated_utc)
      VALUES (?, ?, 0, ?)
      ON CONFLICT(session_id) DO UPDATE SET
        observed_revision = MAX(observed_revision, excluded.observed_revision),
        updated_utc = excluded.updated_utc
    `).run(request.sessionId, memoryRevision, now)

    return memoryRevision
  })()

  const seed = this.seedVcaWeight(actor, body)
  this.insertVcaWeightRevision(
    eventId,
    seed,
    'DETERMINISTIC_SEED',
    `Initial seed at memory frontier r${revision}; curator revision may supersede it.`
  )

  return this.getVcaRecordById(eventId)
}

appendVcaWeightRevision(request: AppendVcaWeightRevisionRequest): VcaRecord {
  const eventId = this.requireText(request.eventId, 'VCA_EVENT_ID', 128)
  this.assertVcaEventExists(eventId)
  const dimensions = {
    humanSignal: this.normalizeWeight(request.humanSignal, 'HUMAN_SIGNAL'),
    veraSignal: this.normalizeWeight(request.veraSignal, 'VERA_SIGNAL'),
    mutualSignal: this.normalizeWeight(request.mutualSignal, 'MUTUAL_SIGNAL'),
    purposeRelation: this.normalizeWeight(request.purposeRelation, 'PURPOSE_RELATION'),
    implementationLink: this.normalizeWeight(request.implementationLink, 'IMPLEMENTATION_LINK'),
    recurrence: this.normalizeWeight(request.recurrence, 'RECURRENCE'),
    novelty: this.normalizeWeight(request.novelty, 'NOVELTY'),
    confidence: this.normalizeWeight(request.confidence, 'CONFIDENCE')
  }
  const curator = this.requireText(request.curator, 'VCA_CURATOR', 120)
  const rationale = this.requireText(request.rationale, 'VCA_RATIONALE', 4000)
  this.insertVcaWeightRevision(eventId, dimensions, curator, rationale)
  return this.getVcaRecordById(eventId)
}

getVcaMemoryClockState(): VcaMemoryClockState {
  const canonicalRevision = this.getCanonicalMemoryRevision()
  const rows = this.db.prepare(`
    SELECT
      s.session_id AS sessionId,
      s.title AS sessionTitle,
      COALESCE(c.observed_revision, 0) AS observedRevision,
      COALESCE(c.compensated_revision, 0) AS compensatedRevision,
      COALESCE(c.updated_utc, s.updated_utc) AS updatedUtc
    FROM session_state AS s
    LEFT JOIN vera_memory_clock AS c
      ON c.session_id = s.session_id
    WHERE s.kind = 'MAIN'
    ORDER BY s.position ASC
  `).all() as Array<{
    sessionId: string
    sessionTitle: string
    observedRevision: number
    compensatedRevision: number
    updatedUtc: string
  }>

  return {
    canonicalRevision,
    sessions: rows.map(row => {
      const effectiveRevision = Math.max(row.observedRevision, row.compensatedRevision)
      return {
        ...row,
        effectiveRevision,
        canonicalRevision,
        lag: Math.max(0, canonicalRevision - effectiveRevision)
      }
    })
  }
}

getVcaCompensation(sessionId: string, limit = 24): VcaCompensationPacket {
  this.assertMainSession(sessionId)
  const clock = this.getVcaMemoryClockState()
  const lane = clock.sessions.find(item => item.sessionId === sessionId)
  if (!lane) throw new Error(`VCA_CLOCK_NOT_FOUND:${sessionId}`)
  const safeLimit = Math.min(Math.max(Math.trunc(limit), 1), 100)
  const fromRevision = lane.effectiveRevision

  const memories = this.db.prepare(`
    WITH current_weight AS (
      SELECT wr.*
      FROM vca_weight_revision AS wr
      INNER JOIN (
        SELECT event_id, MAX(revision) AS current_revision
        FROM vca_weight_revision
        GROUP BY event_id
      ) AS latest
        ON latest.event_id = wr.event_id
       AND latest.current_revision = wr.revision
    )
    SELECT
      e.event_id AS id,
      e.memory_revision AS memoryRevision,
      e.session_id AS sessionId,
      COALESCE(s.title, e.session_id) AS sessionTitle,
      CASE e.actor WHEN 'HUMAN' THEN 'USER' ELSE 'ASSISTANT' END AS role,
      e.actor AS actor,
      e.body AS body,
      e.source_kind AS sourceKind,
      e.source_ref AS sourceRef,
      COALESCE(w.revision, 0) AS weightRevision,
      COALESCE(w.human_signal, 0) AS humanSignal,
      COALESCE(w.vera_signal, 0) AS veraSignal,
      COALESCE(w.mutual_signal, 0) AS mutualSignal,
      COALESCE(w.purpose_relation, 0) AS purposeRelation,
      COALESCE(w.implementation_link, 0) AS implementationLink,
      COALESCE(w.recurrence, 0) AS recurrence,
      COALESCE(w.novelty, 0) AS novelty,
      COALESCE(w.confidence, 0) AS confidence,
      COALESCE(w.memory_gravity, 0) AS memoryGravity,
      COALESCE(w.curator, 'UNWEIGHTED') AS curator,
      COALESCE(w.rationale, '') AS rationale,
      e.created_utc AS createdUtc,
      COALESCE(w.recorded_utc, e.created_utc) AS weightedUtc
    FROM vca_memory_event AS e
    LEFT JOIN session_state AS s ON s.session_id = e.session_id
    LEFT JOIN current_weight AS w ON w.event_id = e.event_id
    WHERE e.memory_revision > ?
      AND e.memory_revision <= ?
    ORDER BY COALESCE(w.memory_gravity, 0) DESC, e.memory_revision ASC
    LIMIT ?
  `).all(fromRevision, clock.canonicalRevision, safeLimit) as VcaRecord[]

  return {
    sessionId,
    fromRevision,
    targetRevision: clock.canonicalRevision,
    lag: lane.lag,
    memories
  }
}

acknowledgeVcaCompensation(sessionId: string, throughRevision: number): VcaMemoryClockState {
  this.assertMainSession(sessionId)
  const canonicalRevision = this.getCanonicalMemoryRevision()
  const safeRevision = Math.max(0, Math.min(Math.trunc(throughRevision), canonicalRevision))
  this.db.prepare(`
    INSERT INTO vera_memory_clock
    (session_id, observed_revision, compensated_revision, updated_utc)
    VALUES (?, 0, ?, ?)
    ON CONFLICT(session_id) DO UPDATE SET
      compensated_revision = MAX(compensated_revision, excluded.compensated_revision),
      updated_utc = excluded.updated_utc
  `).run(sessionId, safeRevision, new Date().toISOString())
  return this.getVcaMemoryClockState()
}


getVeraSessionThreadBindings(): VeraSessionThreadBinding[] {
  const clock = this.getVcaMemoryClockState()
  const bySession = new Map(clock.sessions.map(item => [item.sessionId, item]))
  const rows = this.db.prepare(`
    SELECT
      t.session_id AS sessionId,
      COALESCE(s.title, t.session_id) AS sessionTitle,
      t.thread_url AS threadUrl,
      t.thread_key AS threadKey,
      t.updated_utc AS updatedUtc
    FROM vera_session_thread AS t
    JOIN session_state AS s ON s.session_id = t.session_id
    WHERE s.kind = 'MAIN'
    ORDER BY s.position ASC
  `).all() as Array<{
    sessionId: string
    sessionTitle: string
    threadUrl: string
    threadKey: string
    updatedUtc: string
  }>

  return rows.map(row => {
    const laneClock = bySession.get(row.sessionId)
    return {
      ...row,
      observedRevision: laneClock?.observedRevision ?? 0,
      compensatedRevision: laneClock?.compensatedRevision ?? 0,
      canonicalRevision: laneClock?.canonicalRevision ?? clock.canonicalRevision,
      lag: laneClock?.lag ?? clock.canonicalRevision
    }
  })
}

updateVeraSessionThread(request: UpdateVeraSessionThreadRequest): VeraSessionThreadBinding {
  this.assertSessionExists(request.sessionId)
  const thread = this.normalizeChatGptThreadUrl(request.threadUrl)
  const now = new Date().toISOString()
  this.db.prepare(`
    INSERT INTO vera_session_thread
    (session_id, thread_url, thread_key, updated_utc)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(session_id) DO UPDATE SET
      thread_url = excluded.thread_url,
      thread_key = excluded.thread_key,
      updated_utc = excluded.updated_utc
  `).run(request.sessionId, thread.url, thread.key, now)

  const result = this.getVeraSessionThreadBindings().find(item => item.sessionId === request.sessionId)
  if (!result) throw new Error(`VERA_THREAD_BINDING_NOT_VISIBLE:${request.sessionId}`)
  return result
}

getVcaInbox(limit = 60): VcaInboxState {
  const safeLimit = Math.min(Math.max(Math.trunc(limit), 1), 200)
  const counts = this.db.prepare(`
    SELECT
      SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) AS pendingCount,
      SUM(CASE WHEN status = 'CURATED' THEN 1 ELSE 0 END) AS curatedCount,
      COALESCE(SUM(duplicate_hits), 0) AS duplicateHits
    FROM vca_memory_inbox
  `).get() as { pendingCount: number | null; curatedCount: number | null; duplicateHits: number | null }

  const items = this.db.prepare(`
    SELECT
      i.inbox_id AS id,
      i.fingerprint AS fingerprint,
      i.session_id AS sessionId,
      COALESCE(s.title, i.session_id) AS sessionTitle,
      i.thread_url AS threadUrl,
      i.thread_key AS threadKey,
      i.actor AS actor,
      i.body AS body,
      i.capture_kind AS captureKind,
      i.source_ref AS sourceRef,
      i.status AS status,
      i.promoted_event_id AS promotedEventId,
      i.duplicate_hits AS duplicateHits,
      i.created_utc AS createdUtc,
      i.processed_utc AS processedUtc
    FROM vca_memory_inbox AS i
    LEFT JOIN session_state AS s ON s.session_id = i.session_id
    ORDER BY i.created_utc DESC, i.inbox_id DESC
    LIMIT ?
  `).all(safeLimit) as VcaInboxItem[]

  return {
    pendingCount: counts.pendingCount ?? 0,
    curatedCount: counts.curatedCount ?? 0,
    duplicateHits: counts.duplicateHits ?? 0,
    items
  }
}

enqueueVcaInbox(request: EnqueueVcaInboxRequest): VcaInboxEnqueueResult {
  this.assertSessionExists(request.sessionId)
  const actor = this.normalizeVcaActor(request.actor)
  const body = this.requireText(request.body, 'VCA_INBOX_BODY', 120000)
  const captureKind = this.normalizeVcaCaptureKind(request.captureKind)
  const binding = this.getVeraSessionThreadBindings().find(item => item.sessionId === request.sessionId)
  const thread = this.normalizeChatGptThreadUrl(request.threadUrl || binding?.threadUrl || 'https://chatgpt.com/')
  const sourceRef = typeof request.sourceRef === 'string' && request.sourceRef.trim()
    ? request.sourceRef.trim().slice(0, 4096)
    : null
  const createdUtc = typeof request.createdUtc === 'string' && request.createdUtc.trim()
    ? request.createdUtc.trim().slice(0, 80)
    : new Date().toISOString()
  const fingerprint = this.vcaInboxFingerprint(request.sessionId, thread.key, actor, body)
  const existing = this.db.prepare(`
    SELECT inbox_id AS id
    FROM vca_memory_inbox
    WHERE fingerprint = ?
  `).get(fingerprint) as { id: string } | undefined

  if (existing) {
    this.db.prepare(`
      UPDATE vca_memory_inbox
      SET duplicate_hits = duplicate_hits + 1
      WHERE inbox_id = ?
    `).run(existing.id)
    return {
      duplicate: true,
      item: this.getVcaInboxItem(existing.id),
      memory: null
    }
  }

  const inboxId = randomUUID()
  this.db.prepare(`
    INSERT INTO vca_memory_inbox
    (inbox_id, fingerprint, session_id, thread_url, thread_key, actor, body,
     capture_kind, source_ref, status, promoted_event_id, duplicate_hits, created_utc, processed_utc)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', NULL, 0, ?, NULL)
  `).run(
    inboxId,
    fingerprint,
    request.sessionId,
    thread.url,
    thread.key,
    actor,
    body,
    captureKind,
    sourceRef,
    createdUtc
  )

  const memory = this.promoteVcaInboxItem(inboxId)
  return {
    duplicate: false,
    item: this.getVcaInboxItem(inboxId),
    memory
  }
}

markVcaInboxCuratedByEvent(eventId: string): void {
  const normalized = this.requireText(eventId, 'VCA_CURATED_EVENT_ID', 128)
  this.db.prepare(`
    UPDATE vca_memory_inbox
    SET status = 'CURATED', processed_utc = ?
    WHERE promoted_event_id = ?
      AND status <> 'CURATED'
  `).run(new Date().toISOString(), normalized)
}

private promoteVcaInboxItem(inboxId: string): VcaRecord {
  const item = this.getVcaInboxItem(inboxId)
  if (item.promotedEventId) return this.getVcaRecordById(item.promotedEventId)

  const memory = this.appendVcaMemoryEvent({
    sessionId: item.sessionId,
    actor: item.actor,
    body: item.body,
    sourceKind: 'SESSION_CAPTURE',
    sourceRef: `VCA_INBOX:${item.id}:${item.threadUrl}`,
    createdUtc: item.createdUtc
  })

  this.db.prepare(`
    UPDATE vca_memory_inbox
    SET promoted_event_id = ?
    WHERE inbox_id = ?
  `).run(memory.id, item.id)
  return memory
}

private getVcaInboxItem(inboxId: string): VcaInboxItem {
  const row = this.db.prepare(`
    SELECT
      i.inbox_id AS id,
      i.fingerprint AS fingerprint,
      i.session_id AS sessionId,
      COALESCE(s.title, i.session_id) AS sessionTitle,
      i.thread_url AS threadUrl,
      i.thread_key AS threadKey,
      i.actor AS actor,
      i.body AS body,
      i.capture_kind AS captureKind,
      i.source_ref AS sourceRef,
      i.status AS status,
      i.promoted_event_id AS promotedEventId,
      i.duplicate_hits AS duplicateHits,
      i.created_utc AS createdUtc,
      i.processed_utc AS processedUtc
    FROM vca_memory_inbox AS i
    LEFT JOIN session_state AS s ON s.session_id = i.session_id
    WHERE i.inbox_id = ?
  `).get(inboxId) as VcaInboxItem | undefined
  if (!row) throw new Error(`VCA_INBOX_NOT_FOUND:${inboxId}`)
  return row
}

private normalizeVcaCaptureKind(value: VcaCaptureKind): VcaCaptureKind {
  if (value === 'SESSION_BRIDGE' || value === 'MANUAL_BOUNDARY' || value === 'ARD' || value === 'IMPORT') return value
  throw new Error('VCA_CAPTURE_KIND_INVALID')
}

private normalizeChatGptThreadUrl(value: string): { url: string; key: string } {
  let parsed: URL
  try {
    parsed = new URL(value)
  } catch {
    throw new Error('VERA_THREAD_URL_INVALID')
  }
  if (parsed.protocol !== 'https:' || parsed.hostname !== 'chatgpt.com') {
    throw new Error('VERA_THREAD_URL_NOT_CHATGPT')
  }
  parsed.hash = ''
  const key = `${parsed.pathname || '/'}${parsed.search || ''}`.slice(0, 2048)
  return { url: parsed.toString().slice(0, 4096), key }
}

private vcaInboxFingerprint(sessionId: string, threadKey: string, actor: VcaMemoryActor, body: string): string {
  const normalizedBody = body.normalize('NFKC').trim().replace(/\s+/g, ' ').toLowerCase()
  return createHash('sha256')
    .update(`${sessionId}\n${threadKey}\n${actor}\n${normalizedBody}`, 'utf8')
    .digest('hex')
}

getVcaCuratorSettings(): VcaCuratorSettings {
  const rows = this.db.prepare(`
    SELECT key, value
    FROM portal_setting
    WHERE key IN ('vca_curator_lane', 'vca_curator_auto', 'vca_curator_batch')
  `).all() as Array<{ key: string; value: string }>
  const values = new Map(rows.map(row => [row.key, row.value]))
  const laneId = this.normalizeAiLaneId(values.get('vca_curator_lane') ?? 'lane-4')
  const autoRun = values.get('vca_curator_auto') === '1'
  const batchRaw = Number.parseInt(values.get('vca_curator_batch') ?? '8', 10)
  const batchSize = Math.min(Math.max(Number.isFinite(batchRaw) ? batchRaw : 8, 1), 24)
  return { laneId, autoRun, batchSize }
}

saveVcaCuratorSettings(request: SaveVcaCuratorSettingsRequest): VcaCuratorSettings {
  const laneId = this.normalizeAiLaneId(request.laneId)
  const autoRun = Boolean(request.autoRun)
  const batchSize = Math.min(Math.max(Math.trunc(request.batchSize ?? 8), 1), 24)
  const save = this.db.prepare(`
    INSERT INTO portal_setting (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
  `)
  this.db.transaction(() => {
    save.run('vca_curator_lane', laneId)
    save.run('vca_curator_auto', autoRun ? '1' : '0')
    save.run('vca_curator_batch', String(batchSize))
  })()
  return this.getVcaCuratorSettings()
}

countVcaCuratorPending(): number {
  const row = this.db.prepare(`
    WITH latest AS (
      SELECT event_id, MAX(revision) AS revision
      FROM vca_weight_revision
      GROUP BY event_id
    )
    SELECT COUNT(*) AS count
    FROM vca_memory_event AS e
    LEFT JOIN latest ON latest.event_id = e.event_id
    LEFT JOIN vca_weight_revision AS w
      ON w.event_id = latest.event_id AND w.revision = latest.revision
    WHERE COALESCE(w.curator, 'UNWEIGHTED') IN ('DETERMINISTIC_SEED', 'UNWEIGHTED')
  `).get() as { count: number }
  return row.count
}

listVcaCuratorCandidates(mode: VcaCuratorMode, limit = 8): VcaRecord[] {
  const safeLimit = Math.min(Math.max(Math.trunc(limit), 1), 24)
  const records = this.searchVca('', 300)
  if (mode === 'PENDING') {
    return records
      .filter(record => record.curator === 'DETERMINISTIC_SEED' || record.curator === 'UNWEIGHTED')
      .sort((a, b) => a.memoryRevision - b.memoryRevision)
      .slice(0, safeLimit)
  }

  return records
    .filter(record => record.curator !== 'UNWEIGHTED')
    .sort((a, b) => {
      if (b.memoryGravity !== a.memoryGravity) return b.memoryGravity - a.memoryGravity
      return a.weightedUtc.localeCompare(b.weightedUtc)
    })
    .slice(0, safeLimit)
}

private normalizeAiLaneId(value: unknown): AiLaneId {
  if (value === 'lane-1' || value === 'lane-2' || value === 'lane-3' || value === 'lane-4' || value === 'lane-5') return value
  throw new Error('VCA_CURATOR_LANE_INVALID')
}

private getCanonicalMemoryRevision(): number {
  const row = this.db.prepare(`
    SELECT COALESCE(MAX(memory_revision), 0) AS revision
    FROM vca_memory_event
  `).get() as { revision: number }
  return row.revision
}

private getVcaRecordById(eventId: string): VcaRecord {
  const record = this.db.prepare(`
    WITH current_weight AS (
      SELECT wr.*
      FROM vca_weight_revision AS wr
      INNER JOIN (
        SELECT event_id, MAX(revision) AS current_revision
        FROM vca_weight_revision
        GROUP BY event_id
      ) AS latest
        ON latest.event_id = wr.event_id
       AND latest.current_revision = wr.revision
    )
    SELECT
      e.event_id AS id,
      e.memory_revision AS memoryRevision,
      e.session_id AS sessionId,
      COALESCE(s.title, e.session_id) AS sessionTitle,
      CASE e.actor WHEN 'HUMAN' THEN 'USER' ELSE 'ASSISTANT' END AS role,
      e.actor AS actor,
      e.body AS body,
      e.source_kind AS sourceKind,
      e.source_ref AS sourceRef,
      COALESCE(w.revision, 0) AS weightRevision,
      COALESCE(w.human_signal, 0) AS humanSignal,
      COALESCE(w.vera_signal, 0) AS veraSignal,
      COALESCE(w.mutual_signal, 0) AS mutualSignal,
      COALESCE(w.purpose_relation, 0) AS purposeRelation,
      COALESCE(w.implementation_link, 0) AS implementationLink,
      COALESCE(w.recurrence, 0) AS recurrence,
      COALESCE(w.novelty, 0) AS novelty,
      COALESCE(w.confidence, 0) AS confidence,
      COALESCE(w.memory_gravity, 0) AS memoryGravity,
      COALESCE(w.curator, 'UNWEIGHTED') AS curator,
      COALESCE(w.rationale, '') AS rationale,
      e.created_utc AS createdUtc,
      COALESCE(w.recorded_utc, e.created_utc) AS weightedUtc
    FROM vca_memory_event AS e
    LEFT JOIN session_state AS s ON s.session_id = e.session_id
    LEFT JOIN current_weight AS w ON w.event_id = e.event_id
    WHERE e.event_id = ?
  `).get(eventId) as VcaRecord | undefined
  if (!record) throw new Error(`VCA_EVENT_NOT_VISIBLE:${eventId}`)
  return record
}

private assertVcaEventExists(eventId: string): void {
  const row = this.db.prepare('SELECT 1 FROM vca_memory_event WHERE event_id = ?').get(eventId)
  if (!row) throw new Error(`VCA_EVENT_NOT_FOUND:${eventId}`)
}

private normalizeVcaActor(value: VcaMemoryActor): VcaMemoryActor {
  if (value === 'HUMAN' || value === 'VERA' || value === 'MUTUAL' || value === 'UNKNOWN' || value === 'SYSTEM') return value
  throw new Error('VCA_ACTOR_INVALID')
}

private normalizeWeight(value: unknown, label: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`VCA_WEIGHT_${label}_INVALID`)
  }
  return Math.max(0, Math.min(100, value))
}

private memoryGravity(dimensions: {
  humanSignal: number
  veraSignal: number
  mutualSignal: number
  purposeRelation: number
  implementationLink: number
  recurrence: number
  novelty: number
  confidence: number
}): number {
  // Human and Vera signals deliberately carry identical coefficients.
  const gravity =
    dimensions.humanSignal * 0.16 +
    dimensions.veraSignal * 0.16 +
    dimensions.mutualSignal * 0.14 +
    dimensions.purposeRelation * 0.18 +
    dimensions.implementationLink * 0.16 +
    dimensions.recurrence * 0.08 +
    dimensions.novelty * 0.06 +
    dimensions.confidence * 0.06
  return Math.round(gravity * 100) / 100
}

private seedVcaWeight(actor: VcaMemoryActor, body: string) {
  const text = body.toLowerCase()
  const cue = (pairs: Array<[string, number]>): number => {
    let score = 0
    for (const [needle, value] of pairs) {
      if (text.includes(needle.toLowerCase())) score = Math.max(score, value)
    }
    return score
  }
  const directImpact = cue([
    ['超絶採用', 100], ['超採用', 92], ['正式採用', 90], ['採用!', 82], ['採用！', 82],
    ['これで行く', 76], ['固定', 72], ['canonical', 72], ['重要', 66], ['本質', 68], ['核心', 68]
  ])
  const purposeRelation = cue([
    ['目的', 78], ['目標', 78], ['原点', 82], ['設計思想', 84], ['本筋', 84], ['方針', 68], ['identity', 70], ['アイデンティティ', 76]
  ])
  const implementationLink = cue([
    ['vra', 90], ['works', 84], ['実装', 82], ['ソース', 76], ['build', 78], ['evidence', 82], ['修正', 62], ['設計', 68]
  ])
  const novelty = Math.min(80, 20 + Math.floor(Math.min(body.length, 2400) / 60))
  return {
    humanSignal: actor === 'HUMAN' || actor === 'MUTUAL' ? directImpact : 0,
    veraSignal: actor === 'VERA' || actor === 'MUTUAL' ? directImpact : 0,
    mutualSignal: actor === 'MUTUAL' ? directImpact : 0,
    purposeRelation,
    implementationLink,
    recurrence: 0,
    novelty,
    confidence: 36
  }
}

private insertVcaWeightRevision(
  eventId: string,
  dimensions: {
    humanSignal: number
    veraSignal: number
    mutualSignal: number
    purposeRelation: number
    implementationLink: number
    recurrence: number
    novelty: number
    confidence: number
  },
  curator: string,
  rationale: string
): void {
  const row = this.db.prepare(`
    SELECT COALESCE(MAX(revision), 0) AS revision
    FROM vca_weight_revision
    WHERE event_id = ?
  `).get(eventId) as { revision: number }
  const gravity = this.memoryGravity(dimensions)
  this.db.prepare(`
    INSERT INTO vca_weight_revision
    (event_id, revision, human_signal, vera_signal, mutual_signal, purpose_relation,
     implementation_link, recurrence, novelty, confidence, memory_gravity, curator, rationale, recorded_utc)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    eventId,
    row.revision + 1,
    dimensions.humanSignal,
    dimensions.veraSignal,
    dimensions.mutualSignal,
    dimensions.purposeRelation,
    dimensions.implementationLink,
    dimensions.recurrence,
    dimensions.novelty,
    dimensions.confidence,
    gravity,
    curator,
    rationale,
    new Date().toISOString()
  )
}

close(): void {
  this.db.close()
}

  private requireVirtualArdState(
    missionId: string
  ): VirtualArdState {
    const state =
      this.getVirtualArdState(
        missionId
      )

    if (!state) {
      throw new Error(
        `ARD_STATE_NOT_FOUND:${missionId}`
      )
    }

    return state
  }

  private assertMissionExists(
    missionId: string
  ): void {
    const id =
      this.requireText(
        missionId,
        'ARD_MISSION_ID',
        128
      )

    const row =
      this.db
        .prepare(`
          SELECT 1
          FROM ard_mission
          WHERE mission_id = ?
        `)
        .get(id)

    if (!row) {
      throw new Error(
        `ARD_MISSION_NOT_FOUND:${id}`
      )
    }
  }

  private assertSessionExists(
    sessionId: string
  ): void {
    const id =
      this.requireText(
        sessionId,
        'SESSION_ID',
        128
      )

    const row =
      this.db
        .prepare(`
          SELECT 1
          FROM session_state
          WHERE session_id = ?
        `)
        .get(id)

    if (!row) {
      throw new Error(
        `SESSION_NOT_FOUND:${id}`
      )
    }
  }

  private assertMainSession(
    sessionId: string
  ): void {
    const id =
      this.requireText(
        sessionId,
        'SESSION_ID',
        128
      )

    const row =
      this.db
        .prepare(`
          SELECT kind
          FROM session_state
          WHERE session_id = ?
        `)
        .get(id) as
          | { kind: SessionKind }
          | undefined

    if (!row) {
      throw new Error(
        `SESSION_NOT_FOUND:${id}`
      )
    }

    if (row.kind !== 'MAIN') {
      throw new Error(
        `ARD_ROLE_REQUIRES_MAIN_SESSION:${id}`
      )
    }
  }

  private assertProjectedSession(
    missionId: string,
    sessionId: string
  ): void {
    const row =
      this.db
        .prepare(`
          SELECT 1
          FROM ard_projection
          WHERE mission_id = ?
            AND session_id = ?
        `)
        .get(
          missionId,
          sessionId
        )

    if (!row) {
      throw new Error(
        `ARD_SESSION_NOT_PROJECTED:${sessionId}`
      )
    }
  }

  private getSetting(
    key: string
  ): string | undefined {
    const row =
      this.db
        .prepare(`
          SELECT value
          FROM portal_setting
          WHERE key = ?
        `)
        .get(key) as
          | { value: string }
          | undefined

    return row?.value
  }

  private requireText(
    value: unknown,
    label: string,
    maxLength: number
  ): string {
    if (typeof value !== 'string') {
      throw new Error(
        `${label}_NOT_STRING`
      )
    }

    const text = value.trim()

    if (!text) {
      throw new Error(
        `${label}_EMPTY`
      )
    }

    if (
      text.length > maxLength
    ) {
      throw new Error(
        `${label}_TOO_LONG`
      )
    }

    return text
  }

  private normalizeActor(
    value:
      SessionMessageActor
  ): SessionMessageActor {
    if (
      value === 'HUMAN' ||
      value === 'VERA' ||
      value === 'SYSTEM'
    ) {
      return value
    }

    throw new Error(
      'SESSION_MESSAGE_ACTOR_INVALID'
    )
  }

  private normalizeHandoffKind(
    value: HandoffKind
  ): HandoffKind {
    const allowed:
      HandoffKind[] = [
        'PLAN',
        'IMPLEMENTATION',
        'REVIEW',
        'EVIDENCE',
        'NOTE'
      ]

    if (
      allowed.includes(value)
    ) {
      return value
    }

    throw new Error(
      'ARD_HANDOFF_KIND_INVALID'
    )
  }

  private normalizeSidebarTab(
    value?: string
  ): SidebarTab {
    return value === 'VCR' ||
      value === 'VCA' ||
      value === 'AI'
      ? value
      : 'PROJECT'
  }
}
