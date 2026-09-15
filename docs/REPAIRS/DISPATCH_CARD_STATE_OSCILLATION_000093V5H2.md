# Dispatch Card + Production Lane Snapshot Oscillation Repair 000093V5H2

## Observed symptom

After 000093V5H1, the Human UI still visibly alternated between snapshots:
- upper Workstation production-lane / 00/32 ACTIVE area flickered;
- a dispatched card alternated between `要確認` with its red error band and `発注済み`
  without that band.

Frame analysis showed actual content removal/reappearance, not a CSS opacity pulse.

## Root cause

There are two periodic entry points into the same Workstation reconciliation path:

1. `startWorkstationReconciler()` in the Electron main process, every 2500 ms.
2. the 000076 renderer Evidence Return pull-through poll, whose IPC path calls
   `refreshState()`, which also calls `reconcileWorkstation()`.

Before H2, only `reconcileWorkstationCard()` had a per-card `workstationInFlight`
guard. The reconciliation cycle itself was not single-flight.

Therefore a renderer `refreshState()` could enter while the main timer cycle was
already running. Its card calls could be skipped by the per-card guard and
`refreshState()` could return a snapshot taken from the middle of the other cycle.
The later push/event then supplied the completed snapshot.

## Repair

`reconcileWorkstation()` is now service-wide single-flight:
- timer and renderer pull-through reuse the same active Promise;
- `refreshState()` waits for the currently active cycle to complete;
- the in-flight slot clears only after the cycle settles;
- existing per-card guards remain as a second layer.

No renderer file is changed. No Workstation file is changed.
Human Gate, exact-origin routing, Evidence ACK order, H2 Observability Tap,
000082 Ray Evidence bridge, and 000093V5H1 sticky error semantics are preserved.
