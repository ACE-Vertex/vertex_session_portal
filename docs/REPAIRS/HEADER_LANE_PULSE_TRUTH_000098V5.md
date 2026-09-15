# Header Lane Pulse Truth Repair 000098V5

## Symptom

After the three-lane 000097 stress test the numeric header correctly returned to:

`WORKSTATION 00/32 ACTIVE`

but two of the 32 lane cells remained illuminated.

## Root cause boundary

000096V5 normalized `workstationSafety.metrics.activeLanes` to current machine-work
states and makes `activeJobs == 0` an absolute empty list.

However `state()` still projected a second renderer-visible array:

`workstationSafety.lastTransition.activeLanes`

from durable Safety transition history.

That history is valid for audit/recovery semantics, but it is not current lane
activity and must not be a Header Pulse authority.

## Repair

000098V5 changes only the renderer projection inside
`src/main/vra/vra-dispatch-service.ts`.

- internal durable Safety history is unchanged;
- current `metrics.activeLanes` remains the single lane-activity authority;
- renderer-visible `lastTransition.activeLanes` is projected from current
  `metrics.activeLanes`, or `[]` when current metrics are unavailable;
- therefore `activeJobs == 0` makes both renderer lane arrays empty;
- no renderer source mutation;
- no Workstation production mutation;
- Evidence FIFO, Observability, Human Gate, exact-origin and reconcile
  single-flight remain unchanged.

Absolute UI contract:

`00/32 ACTIVE => 0 illuminated lane cells`
