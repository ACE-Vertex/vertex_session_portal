# Dispatch Card State Oscillation Repair 000093V5H1

## Symptom
After Session Portal restart, one dispatched card alternates between `発注済み` and `要確認`.

## Root cause
`reconcileWorkstationCard()` cleared `workstationLastError` immediately after a successful
`GET /v1/jobs`, before the downstream Evidence pickup phase completed. A deterministic or
transient Evidence pickup failure then restored the error in the same reconcile cycle.
On the next poll, GET success cleared it again, producing a Human-visible oscillation.

## Repair
Treat Workstation reconciliation as one transaction for Human-facing error state:
- apply authoritative job state;
- perform required Evidence pickup;
- only after the full cycle succeeds, clear `workstationLastError`;
- on failure, retain the same sticky error without emitting duplicate state changes.

No renderer/UI change. No Workstation change. Human Gate, exact-origin routing, ACK,
H2 Observability Tap, and the 000082 Ray Evidence bridge are preserved.
