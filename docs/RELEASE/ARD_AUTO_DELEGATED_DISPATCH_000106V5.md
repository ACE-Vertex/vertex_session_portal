# ARD Auto Delegated Dispatch Foundation — 000106V5

## Vertex OS / ARD Runtime intent

This release turns Session Portal TASK/AUTO into a bounded execution-authority
foundation for the planned Vertex OS.

Flow:

Human clicks AUTO
→ Main Process grants a bounded AUTO Authority Lease
→ controlling Vera emits `vertex-task-dispatch/1`
→ target Vera sessions receive distinct TASKs
→ each child Vera may create its own VRA
→ immutable `origin_session` is captured normally
→ Session Portal revalidates AUTO authority in the trusted main process
→ eligible new VRA cards are dispatched without a second per-card Human click
→ Workstation remains lane allocation and execution authority
→ Evidence returns to the exact child origin session
→ structured TASK result returns to the controlling Vera

## Human Gate

AUTO button click itself is the Human Gate.

There is no extra confirmation dialog. While AUTO authority is active, eligible
VRA cards do not require a second card-level Human approval click.

The durable card still records `humanApproval=APPROVED`; this approval derives
from the Human-granted AUTO authority.

## Fail-closed boundaries

- Authority is revalidated by the main process, never trusted from renderer state.
- Only `vera-01` .. `vera-05` are valid.
- A card must have an exact immutable origin.
- A card captured before the AUTO authority grant cannot be auto-dispatched.
- Workstation must report that new work is allowed.
- AUTO OFF revokes the authority.
- Portal process restart revokes all ACTIVE authority.
- Authority expires after 12 hours even if not manually disarmed.
- Overlapping ambiguous controller authority fails closed in the renderer.
- Normal manual dispatch remains available.
- Workstation Lane Allocation Authority is unchanged.
- `HUMAN_APPLY` remains the execution authority contract.

## ARD identity

The TASK bus persists `parent_dispatch_id` context per delegated child session.
Auto-dispatch audit records include:

- authority_id
- controller_session
- card_id
- job_id
- origin_session
- parent_task_id
- result/error

Audit path:
`<Portal userData>/vra-dispatch/auto-authority-audit.jsonl`

## Preserved contracts

- target-aware roundtrip TASK bus 000053H2
- one-click manual Human dispatch 000104V5
- first-lane fast observation 000105V5
- immutable origin capture
- Evidence FIFO / exact-origin return
- TEST-only RE-RUN gate
- atomic `_incoming` publication
- Workstation Safety admission
- no DOM scraping for VRA origin
- no Workstation production changes

Production mutation is limited to three Session Portal files.
