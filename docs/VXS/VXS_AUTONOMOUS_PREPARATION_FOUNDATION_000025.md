# VXS Autonomous Preparation Foundation 000025

Goal:
Vera/agents autonomously prepare development while humans see only explicit
approval points.

Adds:
- `vxs selftest`
- `vxs selftest --json`
- `vxs policy`
- `vxs policy --json`

Schemas:
- `vxs-selftest/1`
- `vxs-autonomy-policy/1`

Self-test validates:
- unique canonical command names
- unique aliases
- no alias/canonical shadowing
- token/usage contracts
- capability catalog parity
- HUMAN_GATED contract
- VRA remains HUMAN_GATED
- arbitrary `vxs run` is not automatically executable

Autonomy policy:
- automatic observation: enabled
- automatic local verification: enabled
- allowlisted local preparation execution:
  check / lint / test / build / verify (only when registered)
- explicit auto-execution denylist:
  run / vra
- Human Gate bypass: forbidden
- Workstation remains Lane Allocation Authority
- Observation remains additive/non-authoritative
- VERIFY production mutation remains forbidden

This pack introduces policy and self-test only. It does not itself execute
development commands, dispatch VRA, create a new ACK/Return path, or modify the
Observation / Return Bus.
