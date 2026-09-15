import Database from 'better-sqlite3'
import { randomUUID } from 'node:crypto'
import type {
  RetrievalHit,
  SessionChatMessage,
  SessionChatRole,
  SessionKind,
  VirtualArdRole
} from '../../shared/contracts'

export interface SessionDescriptor {
  id: string
  title: string
  kind: SessionKind
}

export interface ActiveProjection {
  missionId: string
  objective: string
  role: VirtualArdRole
  brief: string
}

export interface IncomingHandoff {
  kind: string
  fromSessionId: string
  body: string
  createdUtc: string
}

export class SessionAgentStore {
  private readonly db: Database.Database

  constructor(filePath: string) {
    this.db = new Database(filePath)
    this.db.pragma('journal_mode = WAL')
    this.db.pragma('foreign_keys = ON')
    this.initialize()
  }

  private initialize(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS session_chat_message (
        message_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        body TEXT NOT NULL,
        created_utc TEXT NOT NULL,
        FOREIGN KEY (session_id)
          REFERENCES session_state(session_id)
      );

      CREATE INDEX IF NOT EXISTS idx_session_chat_context
        ON session_chat_message (
          session_id,
          created_utc,
          message_id
        );

      CREATE TABLE IF NOT EXISTS session_retrieval_hit (
        retrieval_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        user_message_id TEXT NOT NULL,
        source TEXT NOT NULL,
        relative_path TEXT NOT NULL,
        line_start INTEGER NOT NULL,
        line_end INTEGER NOT NULL,
        snippet TEXT NOT NULL,
        score REAL NOT NULL,
        created_utc TEXT NOT NULL,
        FOREIGN KEY (session_id)
          REFERENCES session_state(session_id),
        FOREIGN KEY (user_message_id)
          REFERENCES session_chat_message(message_id)
      );

      CREATE INDEX IF NOT EXISTS idx_session_retrieval_latest
        ON session_retrieval_hit (
          session_id,
          created_utc,
          retrieval_id
        );
    `)
  }

  getSession(
    sessionId: string
  ): SessionDescriptor {
    const row = this.db
      .prepare(`
        SELECT
          session_id AS id,
          title,
          kind
        FROM session_state
        WHERE session_id = ?
          AND active = 1
      `)
      .get(sessionId) as
        | SessionDescriptor
        | undefined

    if (!row) {
      throw new Error(
        `SESSION_AGENT_SESSION_NOT_FOUND:${sessionId}`
      )
    }

    return row
  }

  getActiveProjection(
    sessionId: string
  ): ActiveProjection | null {
    const setting = this.db
      .prepare(`
        SELECT value
        FROM portal_setting
        WHERE key = 'active_ard_mission_id'
      `)
      .get() as
        | { value: string }
        | undefined

    if (!setting?.value) {
      return null
    }

    const row = this.db
      .prepare(`
        SELECT
          p.mission_id AS missionId,
          m.objective AS objective,
          p.role AS role,
          p.brief AS brief
        FROM ard_projection AS p
        INNER JOIN ard_mission AS m
          ON m.mission_id = p.mission_id
        WHERE p.mission_id = ?
          AND p.session_id = ?
      `)
      .get(
        setting.value,
        sessionId
      ) as
        | ActiveProjection
        | undefined

    return row ?? null
  }

  getIncomingHandoffs(
    missionId: string,
    sessionId: string,
    limit = 6
  ): IncomingHandoff[] {
    return this.db
      .prepare(`
        SELECT
          kind,
          from_session_id AS fromSessionId,
          body,
          created_utc AS createdUtc
        FROM ard_handoff
        WHERE mission_id = ?
          AND to_session_id = ?
        ORDER BY created_utc DESC, handoff_id DESC
        LIMIT ?
      `)
      .all(
        missionId,
        sessionId,
        limit
      ) as IncomingHandoff[]
  }

  listMessages(
    sessionId: string,
    limit = 16
  ): SessionChatMessage[] {
    return this.db
      .prepare(`
        SELECT *
        FROM (
          SELECT
            message_id AS id,
            session_id AS sessionId,
            role,
            body,
            created_utc AS createdUtc
          FROM session_chat_message
          WHERE session_id = ?
          ORDER BY created_utc DESC, message_id DESC
          LIMIT ?
        )
        ORDER BY createdUtc ASC, id ASC
      `)
      .all(
        sessionId,
        limit
      ) as SessionChatMessage[]
  }

  appendMessage(
    sessionId: string,
    role: SessionChatRole,
    body: string
  ): SessionChatMessage {
    this.getSession(sessionId)

    const normalized =
      this.requireBody(body)

    const message:
      SessionChatMessage = {
        id: randomUUID(),
        sessionId,
        role,
        body: normalized,
        createdUtc:
          new Date().toISOString()
      }

    this.db
      .prepare(`
        INSERT INTO session_chat_message
        (
          message_id,
          session_id,
          role,
          body,
          created_utc
        )
        VALUES (?, ?, ?, ?, ?)
      `)
      .run(
        message.id,
        message.sessionId,
        message.role,
        message.body,
        message.createdUtc
      )

    return message
  }


  replaceLatestRetrieval(
    sessionId: string,
    userMessageId: string,
    hits: RetrievalHit[]
  ): void {
    this.getSession(
      sessionId
    )

    this.db.transaction(
      () => {
        this.db
          .prepare(`
            DELETE FROM session_retrieval_hit
            WHERE session_id = ?
          `)
          .run(
            sessionId
          )

        const insert =
          this.db.prepare(`
            INSERT INTO session_retrieval_hit
            (
              retrieval_id,
              session_id,
              user_message_id,
              source,
              relative_path,
              line_start,
              line_end,
              snippet,
              score,
              created_utc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          `)

        const now =
          new Date().toISOString()

        for (
          const hit of hits
        ) {
          insert.run(
            randomUUID(),
            sessionId,
            userMessageId,
            hit.source,
            hit.relativePath,
            hit.lineStart,
            hit.lineEnd,
            hit.snippet,
            hit.score,
            now
          )
        }
      }
    )()
  }

  getLatestRetrieval(
    sessionId: string
  ): RetrievalHit[] {
    this.getSession(
      sessionId
    )

    return this.db
      .prepare(`
        SELECT
          source,
          relative_path AS relativePath,
          line_start AS lineStart,
          line_end AS lineEnd,
          snippet,
          score
        FROM session_retrieval_hit
        WHERE session_id = ?
        ORDER BY score DESC, relative_path ASC
      `)
      .all(
        sessionId
      ) as RetrievalHit[]
  }

  close(): void {
    this.db.close()
  }

  private requireBody(
    value: unknown
  ): string {
    if (typeof value !== 'string') {
      throw new Error(
        'SESSION_AGENT_BODY_NOT_STRING'
      )
    }

    const body = value.trim()

    if (!body) {
      throw new Error(
        'SESSION_AGENT_BODY_EMPTY'
      )
    }

    if (body.length > 12000) {
      throw new Error(
        'SESSION_AGENT_BODY_TOO_LONG'
      )
    }

    return body
  }
}
