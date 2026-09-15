# VRA Registry Foundation 000124V5

This pass establishes the Session Portal-side Registry domain without wiring it
into the Dispatch Bay yet.

Invariants:

- Normal/manual VRA path remains unchanged.
- Registry intake is AUTO-only.
- Registry keeps immutable origin/session/window/return route.
- Registry does not own lane allocation. `requestedLane` is advisory only.
- Workstation HUMAN_APPLY remains authoritative.
- Registry stores normalized job/event memory, not full VRA card history.
- VLog is append-only and designed for SQLite durability.
- VLog has no unscoped `listAll`; reads require Query Gate reason + identity scope.
- Observer consumes state transitions directly. It does not continuously scan VLog.
- BAY receives only a readiness trigger in the next adapter pass.
- Evidence return is tracked by Registry states but actual Portal ACK flow remains unchanged.
