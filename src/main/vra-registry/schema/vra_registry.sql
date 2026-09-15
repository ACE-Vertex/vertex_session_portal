CREATE TABLE IF NOT EXISTS vra_registry (
 registry_id TEXT PRIMARY KEY,
 job_id TEXT UNIQUE NOT NULL,
 artifact_id TEXT NOT NULL,
 correlation_id TEXT NOT NULL,
 state TEXT NOT NULL,
 origin_vera TEXT NOT NULL,
 origin_session TEXT NOT NULL,
 origin_window TEXT NOT NULL,
 return_channel TEXT NOT NULL,
 evidence_id TEXT,
 created_utc TEXT NOT NULL,
 updated_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vertex_vlog (
 event_id TEXT PRIMARY KEY,
 kind TEXT NOT NULL,
 registry_id TEXT NOT NULL,
 job_id TEXT NOT NULL,
 artifact_id TEXT NOT NULL,
 correlation_id TEXT NOT NULL,
 occurred_utc TEXT NOT NULL,
 state_from TEXT,
 state_to TEXT,
 evidence_id TEXT,
 code TEXT,
 note TEXT
);
