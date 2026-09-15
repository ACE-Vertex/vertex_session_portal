# AUTO Registry Adapter Foundation 000128V5

Purpose:
Connect AUTO request intake to Registry only.

Flow:
AUTO Request
 -> Registry Register
 -> VLog REGISTERED
 -> READY_FOR_BAY trigger event

Not included:
- Dispatch Bay execution
- Lane allocation
- Workstation job POST
- Evidence ACK mutation

Ownership:
Registry owns identity.
Workstation owns execution and lane allocation.
Human Gate remains authoritative.
