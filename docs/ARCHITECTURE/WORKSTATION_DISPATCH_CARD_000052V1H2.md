# Vertex Session Portal / Workstation Dispatch Card 000052V1H2

VERA1 H2 aligns Session Portal provenance/logistics with the latest VERA4 Integration boundary and the VERIFIED VERA3 `vra-routing/1` H2 contract.

## Ownership

- Session Portal owns Vera-window provenance capture, STAGING, Human Approval, Human Export, and atomic publication of a VRA file into `_incoming`.
- Workstation owns lane allocation, execution, locks, APPLY/VERIFY, job registry semantics, and Evidence.
- This artifact does not modify `vertex_workstation` and does not implement `POST /v1/jobs`.

## New Capture origin rule

`VeraBrowserSession` already registers its real `sessionId` (`vera-01` ... `vera-05`) with the VRA capture service through the existing webContents source map. H2 treats that map as a hard prerequisite.

If a new `.vra` download cannot resolve its `webContentsId` to a registered `vera-0N` session, the download is cancelled with `VRA_ORIGIN_UNRESOLVED` before a capture id, staging sidecar, or staging save path is created. No active-window fallback and no guest DOM scrape exists.

Only legacy ledger migration may consume an already-persisted `sourceSessionId`. New Capture cannot use that fallback.

## Durable routing sidecar

The existing `.meta.json` sidecar remains the durable Portal source of truth and uses VERA3 H2 vocabulary:

- `contract_version = vra-routing/1`
- `job_id`
- immutable `origin_vera`, `origin_session`, `origin_window`
- `return_channel`
- `project_id`, `project_name`
- `artifact_id`, `title`
- `requested_lane` (`lane_hint` accepted as VERA3 alias)
- `lane_policy = ANY | PREFER`
- `parallelism` in `1..=32`
- optional `worker_concurrency`
- `correlation_id`
- optional `allocated_lane` (Workstation fact only)

For routed VRA manifests, unsupported contract versions, missing `job_id`/`return_channel`, external lane policies other than `ANY`/`PREFER`, `PREFER` without `requested_lane`, invalid parallelism, or invalid worker concurrency are quarantined as routing errors rather than becoming healthy STAGED work.

Legacy `vra/1` without top-level routing remains accepted; Portal creates the durable routing envelope and generates a local job/correlation identity. Manifest `origin_*` values are never used to override Capture provenance.

## Requested vs allocated lane

`requested_lane` is only a hint from VERA. Session Portal transports/displays it. `allocated_lane` is never assigned by Session Portal. Workstation is the sole final Lane Allocation Authority.

## Human Dispatch transaction

The filesystem publish boundary is:

1. explicit Human action;
2. durable `human_approval=APPROVED` + `dispatch_phase=APPROVED` sidecar/ledger commit;
3. copy staged VRA to a same-directory hidden `.tmp` name under `_incoming`;
4. verify temporary-file SHA256 equals the immutable staged SHA256;
5. atomic rename to the final `.vra` name;
6. durable final sidecar commit with `dispatch_phase=PUBLISHED` / `status=DISPATCHED`.

A final `.vra` name is never exposed while bytes are still copying. If the Portal is killed after rename but before the final sidecar commit, startup/retry reconciles an APPROVED sidecar against the already-published file/hash and promotes it to PUBLISHED without a duplicate copy.

`POST /v1/jobs` remains intentionally absent until Final Integration. Filesystem publication is the data commit; future HTTP registration is the control-plane commit and must happen after the filesystem commit.

## Preserved invariants

Human Gate, STAGING_FIRST, Human Export, the existing single VRA capture owner, existing VERA1-5 layout, current preload/IPC bridge, no browser DOM scrape, no auto apply, and Human-facing Path suppression are preserved.

Production source mutation is performed only by normal `vra/1` copy operations. VERIFY performs source inspection plus TypeScript no-emit typecheck and compares source hashes before/after.
