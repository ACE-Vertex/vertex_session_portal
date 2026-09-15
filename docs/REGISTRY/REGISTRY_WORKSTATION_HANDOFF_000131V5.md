# VRA Registry Workstation Handoff Adapter Foundation 000131V5

Purpose:
Create the final boundary contract between Session Portal Registry and Vertex Workstation.

Flow:
Registry
 -> BayTrigger
 -> Human Approval
 -> Workstation Handoff Intent

Included:
- identity binding
- job binding
- artifact binding
- handoff envelope foundation

Not included:
- POST /jobs
- lane allocation
- execution
- APPLY
- Evidence mutation

Ownership:
Registry owns lifecycle identity.
Workstation owns execution.
Human owns approval.
