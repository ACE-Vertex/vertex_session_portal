# Vertex Shell Native VRA Dispatch 000080V4G

## Goal

Use the embedded Vertex Shell as the human VRA dispatch cockpit without launching
PowerShell or CMD for the dispatch command itself.

## Native commands

```text
vra help
vra list
vra dispatch <artifact-id|card-id|filename>
```

`vra list` calls the existing Session Portal renderer API:
`window.vertexPortal.getVraDispatchState()`.

`vra dispatch ...` resolves exactly one existing card and calls:
`window.vertexPortal.dispatchVraCard(card.id)`.

The native VRA branch returns before the normal Vertex Shell `send('execute')`
path, so these VRA commands do not enter the pwsh compatibility organ.

## Authority

This does NOT create a second VRA publisher.

The existing Session Portal `VraDispatchService` remains the sole owner of:
- durable Human Approval
- staged metadata
- temporary publication
- SHA-256 verification
- atomic rename into Workstation incoming
- incoming commit sidecar
- Workstation job registration/reconciliation
- lane allocation authority handoff

The operator must explicitly type/paste `vra dispatch ...` and press Enter.
No timer or Vera/webview auto-dispatch is added.

## Flicker status

The Vertex Shell native VRA command itself does not spawn cmd.exe or pwsh.exe.
Whether all visible flicker is eliminated is a runtime question: another subsystem
could still launch a process window. Verify after build/restart with a real staged
VRA before declaring flicker eliminated.

## Runtime smoke

1. `vra list`
2. Confirm the list appears with no `RUN pwsh.exe` line.
3. With a staged test VRA:
   `vra dispatch <artifact-id>`
4. Confirm native result shows the actual returned dispatch state.
5. Confirm Workstation receives the VRA normally and returns Evidence.
6. Observe whether any external console flicker remains.
