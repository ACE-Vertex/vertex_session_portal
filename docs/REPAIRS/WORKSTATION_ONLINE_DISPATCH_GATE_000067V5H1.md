# Workstation Online Dispatch Gate 000067V5H1

## Root cause

000067V5 correctly introduced a direct Workstation process-health observation for the
Dispatch Bay header.

However, `workstationDispatchBlockReason()` still used only the older
`VraDispatchState.workstationOnline` flag.

That created two online authorities:

- Header: direct process health + dispatch-state health
- Dispatch gate: dispatch-state health only

Result: the header could show `WORKSTATION ONLINE` while `工場へ発注` remained disabled
as `WORKSTATION OFFLINE`.

## Fix

The dispatch gate now calls the same `workstationOnline()` aggregation used by the header.

Safety remains a separate mandatory gate:
- Safety observation must be online.
- Safety state must be `RUNNING`.
- Human approval dialog remains mandatory.

No Workstation production source is modified.
