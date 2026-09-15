# VXS Workstation Read Adapter — First Wiring 000055

This change wires only the existing VXS `workstation` and `evidence` commands
to the `VxsWorkstationReadAdapter` introduced by 000053.

## Changed
- `vxs workstation status|health`
- `vxs workstation safety`
- `vxs workstation job <job-id>`
- `vxs evidence <job-id>`

## Not changed
- `vxs jobs`
- `vxs failures`
- `vxs timeline`
- `vxs trace`
- `vxs triage`
- `vxs ray`
- `vxs vra`
- Workstation Server/Core
- Evidence Return / ACK
- Human Gate
- lane allocation authority
- pwsh compatibility

The Adapter remains OBSERVE-only and loopback-only.

No direct APPLY / VERIFY / ROLLBACK route is exposed.

## Runtime generation
This VRA changes source only and runs `npm.cmd run typecheck` from the
read-only verification process. It does not build or relaunch Session Portal.
Runtime promotion must be a separate APPLY step so Source / Build / Runtime
generation remains explicit and auditable.
