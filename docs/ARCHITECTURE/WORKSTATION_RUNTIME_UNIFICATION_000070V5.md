# Session Portal / Workstation Runtime Unification 000070V5

Session Portal and Workstation remain separate OS processes.

Portal now accepts a reachable Workstation as executable ONLINE only when `/v1/health` reports:

- `runtime_contract = vertex-workstation/headless-server-1`
- `recovery_contract = estop-failed-write-recovery-1`

It displays `runtime_generation` in the Dispatch Bay header.

A legacy server on 127.0.0.1:47832 is fail-closed as:

`WORKSTATION LEGACY · RESTART REQUIRED`

and is not treated as dispatch-capable.

Launch policy is now:

1. embedded packaged runtime under `resources/workstation-server/`
2. otherwise current `vertex_workstation` source via Cargo

Direct fallback to possibly stale `headless/target/release/vertex.exe` or
`headless/target/debug/vertex.exe` is retired.

Development Cargo output is isolated under:

`vertex_workstation/runtime/portal-managed-cargo-target`

Portal does not blind-kill a reachable legacy server and never starts a second server on the same port.
Human Gate, Safety Gate, Evidence routing/ACK and Workstation lane authority remain intact.
