# 000058V1H1 — Dispatch Card Flicker + HTTP Routing Repair

## READ-ONLY finding 1: flicker

`VraDispatchLane.refresh()` replaced the complete Shadow DOM through `render()` after every
Workstation/state refresh. The Workstation reconciler continues to poll at 2500 ms.

That behavior remounted cards even when data was unchanged and therefore could reset:
scroll, native `<details open>`, hover/focus, and CSS animation state.

H1 keeps polling and changes renderer behavior to keyed reconciliation.

Stable key priority:

`job_id -> artifact_id -> capture card id`

After the initial shell mount, polling updates only dynamic fields such as:
status, allocated lane, approval, error, button enabled state, counts and notice.

Existing card nodes are moved/reused, not reconstructed.

## READ-ONLY finding 2: ROUTING_REQUIRED_FOR_HTTP_JOB_REGISTRATION

The Portal sidecar already persisted immutable routing fields, and the card displayed them.

However Workstation Final Wiring A does not accept the sidecar as the routing authority.
Its registration gate explicitly reads `manifest.json.routing` from the committed `.vra`.

Legacy `vra/1` artifacts generated without a top-level `routing` object therefore reached:

`ROUTING_REQUIRED_FOR_HTTP_JOB_REGISTRATION`

even though the Portal card/sidecar visibly contained Origin Vera/Session.

## H1 routing fix

At capture completion, before the staged artifact SHA is established, Portal now commits the
capture-time immutable routing identity into the actual staged VRA `manifest.json`.

Source of truth is only the capture owner:

- origin_vera
- origin_session
- origin_window

The renderer is never consulted.

Existing VRA routing values for job/project/lane hints are preserved where valid.
If an explicit origin already exists but conflicts with capture-time origin, capture fails closed.

The enriched staged VRA is rewritten via temp file + parse check + atomic rename.
Only after that commit is SHA-256 calculated.

Therefore one identical routed artifact is used by:
staging sidecar -> Human Approval -> atomic `_incoming` VRA -> `.meta.json` -> POST `/v1/jobs`.

`allocated_lane` is explicitly removed from the external routing envelope because allocation
remains Workstation authority.

## Human error

Internal registration errors remain durable and FAILED remains FAILED.

The collapsed card shows a short Human message, for example:

`新工場へ送れません · 発行元情報の登録が不完全です`

The original code such as:

`ROUTING_REQUIRED_FOR_HTTP_JOB_REGISTRATION`

is visible only in DETAILS / tooltip as `TECHNICAL ERROR`.

## Verification

Includes a 32.5-second-equivalent polling model at the real 2.5-second cadence (13 ticks) and
requires:

- CARD_REMOUNT_ON_UNCHANGED_DATA=0
- SCROLL_JUMP=0
- EXPANSION_RESET=0
- STATUS_UPDATE_PRESERVED=PASS

Also requires all requested 000058 regressions, TypeScript typecheck and production build.

Workstation production files are not modified.
