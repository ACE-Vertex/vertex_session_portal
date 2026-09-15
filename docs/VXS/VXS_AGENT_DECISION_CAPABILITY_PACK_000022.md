# VXS Agent Decision Capability Pack 000022

Adds deterministic, read-only agent decision helpers:

- `vxs readiness`
- `vxs readiness --json`
- `vxs recommend`
- `vxs recommend --json`

Architecture:
- 000021 `AgentContextSnapshot` and its builder are exported and reused.
- Decision logic does not duplicate observation I/O.
- `readiness` classifies current state as READY / ACTIVE / ATTENTION and emits
  a bounded 0..100 score plus explicit signals.
- `recommend` emits existing VXS commands only; it never executes them.

Typical recommendations:
- recent failure -> `vxs triage <job-id>`
- Workstation not confirmed -> `vxs runtime`, `vxs workstation status`
- Git changes -> `vxs verify-plan changed`, `vxs verify changed`
- clean tree -> `vxs preflight`
- untyped workspace -> `vxs ray`

Schemas:
- `vxs-agent-readiness/1`
- `vxs-agent-recommendations/1`

No file mutation, process control, HTTP mutation, retry, reexecution, or Human
Gate bypass is added.
