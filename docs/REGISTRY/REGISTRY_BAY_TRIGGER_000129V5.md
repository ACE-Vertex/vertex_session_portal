# BAY Trigger Adapter Foundation 000129V5

Purpose:
Create the boundary between Registry READY_FOR_BAY state and Dispatch Bay.

This adapter only emits a durable trigger intent.

Flow:
Registry
 -> READY_FOR_BAY
 -> BayTriggerEvent

Not included:
- Workstation job submission
- Lane allocation
- APPLY execution
- Evidence ACK

Ownership:
Registry owns identity.
Dispatch Bay owns presentation.
Workstation owns execution.
Human owns approval.
