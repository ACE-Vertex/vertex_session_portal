# Session Portal + Workstation Server Process Control 000067V5

## Adopted topology

Session Portal does **not** absorb the Workstation execution core.

```text
Vertex Session Portal.exe
    |
    | Human: START WORKSTATION
    v
Vertex Workstation Server (separate OS process)
    |
    +-- 127.0.0.1:47832 control plane
    +-- Persistent Registry
    +-- Scheduler / Lane authority
    +-- Target Lock
    +-- APPLY / VERIFY / Evidence
```

The Portal owns the **launch/control surface and packaged runtime slot**.
Workstation remains a distinct process and remains the execution authority.

## Lifecycle

- If Workstation is already healthy, Start is idempotent and does not create a duplicate process.
- If offline, Portal resolves the embedded runtime first.
- Development fallback uses the sibling `vertex_workstation` release/debug binary, or Cargo only when no binary exists.
- Child process is started detached, `shell:false`, with stdio detached, then `unref()`.
- Closing Session Portal does not kill Workstation.
- No Stop/Kill IPC is added in this pass.

## UI

Dispatch Bay header:
- OFFLINE -> `START WORKSTATION`
- STARTING -> `WORKSTATION STARTING`
- ONLINE -> mint `WORKSTATION ONLINE`

The existing Workstation health observation remains authoritative for Dispatch availability.

## Embedded runtime slot

`resources/workstation-server/` is the release-owned Workstation Server slot.
A release package can place `vertex.exe` there.

`scripts/stage_workstation_server_runtime_000067V5.py` is a release-staging helper.
It is **not** run by VERIFY and therefore does not mutate production as a verification side effect.

## Boundaries preserved

- 127.0.0.1 only
- no HTTP direct APPLY / VERIFY / ROLLBACK
- Human Gate preserved
- Workstation lane allocation authority preserved
- Safety / E-STOP preserved
- exact-origin Evidence Return / ACK preserved
- Shift-range card delete preserved
- Session Portal and Workstation are not one process
