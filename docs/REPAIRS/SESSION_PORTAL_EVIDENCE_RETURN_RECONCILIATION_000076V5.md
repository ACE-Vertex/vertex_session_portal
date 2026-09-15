# Session Portal Evidence Return Reconciliation 000076V5

## Live failure proven by 000074

Workstation 000075V5 successfully completed the dispatched 000073 job:

- runtime_generation = 000075V5
- allocated_lane = lane-06
- job state = SUCCEEDED
- Evidence = AVAILABLE
- evidence_return_state = RETURN_QUEUED
- verified = true

But the Portal `_incoming` sidecar remained at the older snapshot:

- allocated_lane = null
- workstation_job_state = REGISTERED
- workstation_evidence_state = NONE
- workstation_evidence_return_state = NOT_QUEUED

Therefore the forward path and factory execution are healthy. The remaining gap is
Portal reconciliation / Evidence return pickup after Workstation has advanced.

## Repair

1. `VraDispatchService.refreshState()` performs a pull-through Workstation reconcile
   before returning Dispatch state.
2. `workstation:vra-dispatch-state` awaits `refreshState()`.
3. Dispatch Bay polls that pull-through boundary every 2500 ms and coalesces overlapping
   refresh requests.
4. `_incoming` metadata may mirror `allocated_lane` only after Workstation has returned
   the authoritative allocation. Portal still never allocates a lane.
5. Existing exact-origin Evidence delivery and durable DELIVERED-before-ACK contract
   remain unchanged.

Expected live progression after Portal restart:

`RETURN_QUEUED`
→ Portal pulls Evidence
→ exact `vera-05`
→ durable DELIVERED receipt
→ ACK
→ Workstation `RETURNED`
→ Portal card `清算済み`

No Workstation production source is modified.
