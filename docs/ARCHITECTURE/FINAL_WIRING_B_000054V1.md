# Vertex Session Portal — Final Wiring B 000054V1

## Scope

Production mutation is limited to `vertex_session_portal`. `vertex_workstation` is READ-ONLY reference. This increment keeps the five Vera browser windows, Human Gate, VRA staging/export flow, Dispatch Bay density/theme, and `vra/1` compatibility.

## Observed Workstation production contract

Final Wiring B is bound to the production HTTP contract implemented by Workstation Final Wiring A plus `vertex-workstation-evidence-ack-boundary-000055V2`:

- bind: `127.0.0.1:47832`
- `GET /v1/health`
- `POST /v1/jobs` with `{ artifact_filename, artifact_sha256 }`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/evidence`
- `POST /v1/jobs/{job_id}/evidence/ack` with `{ evidence_id, artifact_id, returned_at }`
- ACK first transition requires `RETURN_QUEUED`; exact `RETURNED` retry with identical `returned_at` is idempotent.
- no HTTP APPLY / VERIFY / ROLLBACK.
- Workstation remains Lane Allocation Authority; 32 logical lanes maximum.

## Data commit before control registration

The Portal dispatch transaction is intentionally ordered:

1. immutable Capture origin already exists from `VeraBrowserSession.sessionId()` and registered `webContentsId`.
2. Human Approval is persisted to the Portal sidecar/ledger.
3. staged VRA is copied to a same-directory temporary `_incoming` file.
4. temporary file SHA256 must equal the captured artifact SHA256.
5. atomic rename publishes the final `<artifact_id>.vra`.
6. `_incoming/<artifact_id>.vra.meta.json` is atomically committed with `APPROVED`, `DISPATCHED`, exact origin/routing, and `allocated_lane=null`.
7. only then may `POST /v1/jobs` register control-plane work.

Filesystem is the Data Commit. HTTP is Control Registration. An unavailable Workstation leaves the approved publication durable and registration PENDING for the same filename/hash retry.

## Evidence return and ACK

Evidence is accepted only when its Workstation envelope matches the card's immutable `job_id`, `artifact_id`, `origin_vera`, `origin_session`, `origin_window`, `return_channel`, and `correlation_id`. Unknown or mismatched origin fails closed; active/focused Vera state is never a routing source.

Delivery lifecycle:

`AVAILABLE -> Portal cache -> exact origin resolve -> durable IN_FLIGHT receipt -> write-only Vera injection -> durable DELIVERED receipt -> ACK -> RETURNED`

A delivery failure known to have occurred before send may retry. An ambiguous injection failure remains `IN_FLIGHT` / `DELIVERY_UNCERTAIN`: no automatic redelivery and no ACK. After durable `DELIVERED`, the Portal never reinjects the same Evidence. ACK retries use the exact same `job_id`, `evidence_id`, `artifact_id`, and durable delivery timestamp as `returned_at`, therefore response loss uses Workstation's idempotent ACK path.

Successful and FAILED Evidence use the same exact-origin route. Any repaired VRA remains a new Human Approval event; there is no automatic rerun.

## Prompt Relay

The old free-form adjacent relay control is replaced by absolute `[1] [2] [3] [4] [5]` targets. It reads Windows clipboard text through a narrow Electron main-process IPC and writes it only to the explicitly selected `vera-01` ... `vera-05` composer. It never clicks Send. The current Vera button is disabled and a missing target fails closed. ChatGPT response DOM is never scraped.

## Display title

Each Vera header has a presentation-only `display_title`. Double-click starts edit, Enter commits, Escape cancels, and reset restores the authoritative `session-title` supplied by the Portal project/session model. The preference is stored under `vertex.vera.display-title.<session-id>` and survives Portal restart. It does not mutate `sessionId`, project/routing identity, Capture provenance, or Evidence routing.

## Header pulse

The existing header remains structurally intact. Search is compact (`⌕`) and expands by click or Ctrl+K. A small Workstation pulse uses the Portal's main-process health observation plus the Workstation facts already attached to VRA cards. It renders exactly 32 logical lane cells; allocated lanes are read-only Workstation facts. Clicking an observed allocated lane focuses the matching Dispatch Bay card. Offline renders quietly as `OFFLINE / --/32`.

This is not a new factory dashboard. Ray Console / Ray Core integration is explicitly deferred.
