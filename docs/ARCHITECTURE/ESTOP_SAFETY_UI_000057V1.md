# Vertex Session Portal / Workstation Safety Control UI 000057V1

## Scope

Portal-only integration. Production mutation is limited to `vertex_session_portal`. `vertex_workstation` is READ-ONLY and remains the sole Safety State / Safety Authority owner.

This increment preserves Final Wiring B (`000054V1H2`): Human VRA approval, atomic `_incoming` publication, `POST /v1/jobs`, exact Evidence routing, Evidence ACK, Prompt Relay paste-only behavior, editable durable display title, 32-lane header pulse, Dispatch Bay visual density, hidden paths, no response DOM scrape, and no automatic APPLY/re-run.

## Observed Workstation production contract

Bind: `127.0.0.1:47832` only.

Endpoints:

- `GET /v1/safety`
- `POST /v1/safety/drain`
- `POST /v1/safety/estop`
- `POST /v1/safety/reset`
- `POST /v1/safety/resume`

Every Safety POST accepts exactly:

```json
{
  "request_id": "string, required, max 256",
  "authority": "HUMAN",
  "reason": "string, required, max 2048"
}
```

Unknown fields are rejected by Workstation. Portal renderer cannot supply `authority`; the main/service boundary always emits literal `HUMAN`.

Successful POST response is HTTP 200:

```json
{
  "action": "DRAIN | ESTOP | RESET | RESUME",
  "previous_state": "RUNNING | DRAINING | ESTOP_LATCHED | RESET_READY",
  "state": "RUNNING | DRAINING | ESTOP_LATCHED | RESET_READY",
  "generation": 0,
  "idempotent": false,
  "transition": "SafetyTransitionEvidence | null",
  "auto_reset": false,
  "auto_resume": false,
  "authority": "HUMAN"
}
```

`GET /v1/safety` returns the durable Safety document plus live safety metrics:

```text
safety.schema = vertex-workstation/durable-safety-state-1
safety.generation
safety.state
safety.latched
safety.new_work_allowed
safety.active_continuation_allowed
safety.auto_reset = false
safety.auto_resume = false
safety.last_transition
metrics.active_jobs
metrics.queued_jobs
metrics.active_lanes
metrics.locks
metrics.recovery_result
execution_plane = AVAILABLE | STOPPED
observation_plane = ALIVE
evidence_return_plane = ALIVE
```

Error body is `{ error: { code, message } }`. Invalid transition / recovery block / safety-state rejection is HTTP 409. Non-Human authority is HTTP 403. Invalid JSON or field validation is HTTP 400. Unknown route is 404 and unsupported method is 405.

## State machine and idempotency

- `RUNNING -> DRAIN -> DRAINING`.
- `RUNNING | DRAINING | RESET_READY -> ESTOP -> ESTOP_LATCHED`.
- `ESTOP_LATCHED -> RESET -> RESET_READY`, only after Workstation recovery validation.
- `RESET_READY | DRAINING -> RESUME -> RUNNING`, only after Workstation recovery validation.

Recovery validation requires zero active jobs and `recovery_result == PASS`; the Workstation metric also incorporates orphan locks, recovery-pending state, unsafe inflight state and Evidence registry consistency.

DRAIN while already DRAINING, E-STOP while already latched, and RESET while already RESET_READY are idempotent. RESUME after a response loss is idempotent only when Workstation is already RUNNING and the retry carries the exact same `request_id` as the last RESUME. Portal therefore persists a pending Human Safety action/request id before POST and reuses that id for a Human retry. It never automatically retries a Safety POST.

## Portal boundary

`WorkstationClient` owns the fixed loopback HTTP paths. Renderer uses only typed IPC/preload methods:

- `getWorkstationSafety()`
- `performWorkstationSafetyAction({ action, requestId, reason })`

The renderer has no arbitrary Safety URL and no authority field.

For a mutation, Portal follows:

```text
Human click
-> native Human confirmation
-> durable local pending request_id
-> main IPC
-> Workstation POST
-> Workstation response parse
-> GET /v1/safety
-> exact state + generation recheck
-> UI update
```

There is no optimistic Safety state. A lost POST response is resolved by GET observation; Portal never assumes RUNNING or successful reset/resume.

## Header UI

The existing Header and 32-lane pulse remain. A compact Safety strip is placed adjacent to the Workstation pulse. It does not create a new dashboard or increase the canonical Header row.

Human-facing mapping:

| Workstation state | Display | Human controls |
|---|---|---|
| `RUNNING` | RUNNING | DRAIN, EMERGENCY STOP |
| `DRAINING` | DRAINING | RESUME, EMERGENCY STOP |
| `ESTOP_LATCHED` | E-STOP | RESET |
| `RESET_READY` | RESET READY | RESUME |
| unavailable/unknown | UNKNOWN / OFFLINE or UNKNOWN | none |

E-STOP uses a distinct danger treatment. DRAIN/RESET/RESUME are visually separate ordinary Safety actions. RESET never means RESUME.

All four state-changing controls require Human confirmation. EMERGENCY STOP and RESUME confirmation text explicitly describes the latch/recovery implications.

## Restart and offline

On Portal bootstrap, Portal calls `GET /v1/safety`. Local display state is never the authority. Therefore a Workstation that restarts or remains `ESTOP_LATCHED` is redisplayed as E-STOP after Portal restart.

If Workstation is unreachable, Portal shows UNKNOWN / OFFLINE, exposes no successful Safety action, and never substitutes RUNNING.

## Dispatch / Evidence interaction

When an authoritative online Safety observation is not RUNNING, Dispatch Bay disables new `APPROVE + DISPATCH` actions. The main reconciler also refuses new Workstation registrations until it has an exact RUNNING observation. A `SAFETY_STATE_REJECTED` registration error remains retryable PENDING rather than becoming a permanent BLOCKED artifact.

Already-registered jobs continue through the status/Evidence observation path while stopped. Evidence retrieval and Evidence ACK remain independent Control Plane operations, matching Workstation's `observation_plane=ALIVE` and `evidence_return_plane=ALIVE` contract.

## Explicit non-goals

No Workstation production mutation. No Hard Kill. No arbitrary PID/process control. No HTTP APPLY/VERIFY/ROLLBACK. No automatic E-STOP release, RESET, RESUME or VRA re-run. No browser response DOM scrape. No Session Portal layout redesign.
