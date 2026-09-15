# Workstation Handoff Envelope Foundation 000132V5

Purpose:
Define the receiving-side contract for Session Portal -> Workstation handoff.

Flow:
Registry
 -> BayTrigger
 -> Human Approval
 -> Handoff Envelope
 -> Workstation Receiving Gateway (future)

Included:
- envelope identity
- registry binding
- job binding
- artifact binding
- correlation binding

Not included:
- POST /jobs
- execution
- lane allocation
- APPLY
- evidence mutation

Ownership:
Registry owns lifecycle identity.
Workstation owns execution.
Human owns approval.
