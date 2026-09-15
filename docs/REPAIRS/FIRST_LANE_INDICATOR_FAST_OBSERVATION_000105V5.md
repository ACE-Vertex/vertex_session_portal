# First Lane Indicator Fast Observation 000105V5

## Symptom

The first dispatched Job can sit briefly as:

`QUEUE 01 / ACTIVE 00 / no lane lamp`

even though subsequent Jobs appear to light quickly.

The Portal already performed an immediate per-card reconcile after dispatch.  The
remaining delay was the Header's authoritative `/v1/safety` observation: Scheduler
lane truth could change before the normal 2500 ms observation tick.

## Repair

After a Human dispatch:

1. publish remains atomic and Human-approved;
2. the new card crosses Workstation Control Registration;
3. Session Portal performs a short, coalesced safety-observation burst for 1600 ms;
4. the Header receives real `active_jobs / active_lanes` as soon as Workstation reports them;
5. the existing 2500 ms periodic reconciler remains as the normal steady-state path.

Rapid A/B/C/D/E dispatches extend one shared observation deadline.  They do not create
five independent polling storms.

## Important safety property

No optimistic lane is invented.  Portal never assigns `allocatedLane`, never turns a
lamp on from `QUEUE`, and never claims BUSY before Workstation reports it.

Production mutation: `src/main/vra/vra-dispatch-service.ts` only.
