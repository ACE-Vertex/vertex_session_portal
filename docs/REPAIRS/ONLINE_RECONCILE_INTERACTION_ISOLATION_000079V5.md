# Online Reconcile / Card Interaction Isolation 000079V5

## Live observation

The supplied video establishes a clean state transition:

- Workstation OFFLINE: card hover/click/delete interaction works.
- Workstation ONLINE: the same card interaction becomes unresponsive.

This isolates the problem to the online reconciliation path, not generic CSS.

## Root cause

When Workstation is online, each 2.5 second reconciliation of an already-dispatched
card performs GET job and then calls `persistCardState(card)` even if no Workstation
fact changed. For AVAILABLE Evidence it can also re-fetch/cache/persist the same
Evidence repeatedly.

`persistCardState()` emits `vra-dispatch-changed`, waking the renderer. In addition,
000076 added a second renderer-side 2.5 second poll. With multiple historical cards,
the online server therefore creates repeated bursts of redundant card reconciliation.

That explains why the symptom starts exactly when the server comes online.

## Repair

- main service remains the single Workstation polling owner
- renderer duplicate 2.5 second poll is removed
- job state persistence/emission is edge-triggered on material changes only
- unchanged repeated errors do not emit
- cached immutable Evidence is not fetched again every poll
- 000078 keyed DOM stability, drag isolation, hover/focus/active and delete hardening
  are included in this VRA; 000079 supersedes 000078

Preserved:
- Human Gate
- Workstation lane authority
- exact immutable origin routing
- DELIVERED before ACK
- Workstation production source unchanged
