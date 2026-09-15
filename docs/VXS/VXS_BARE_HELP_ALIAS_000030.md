# VXS Bare Help Alias 000030

## Observed behavior

Inside the Session Portal VXS prompt:

- `--version` is accepted as a bare VXS meta command.
- `vxs --help` is accepted by the VXS Command Registry.
- bare `--help` falls through to `pwsh.exe` and PowerShell raises a parser error.

## Cause

`VertexShellService.execute()` contains a dedicated bare alias for `--version`,
but `--help` was passed unchanged to the normal registry/pwsh routing path.

The Command Registry itself is healthy; `vxs --help` returns the complete
registry with `backend=VXS_COMMAND`.

## Repair

Before `executeVxsCommand(...)`, normalize only the exact bare alias:

`--help` -> `vxs --help`

The original typed command remains unchanged for history/redaction.

No other non-VXS command changes routing, so PowerShell compatibility behavior
is preserved.

## Expected behavior

Both forms must return the same VXS registry without spawning PowerShell:

- `--help`
- `vxs --help`

Expected result backend:

`VXS_COMMAND`

## Build boundary

VERIFY remains read-only with respect to production runtime output and performs
type checking only.

After Workstation APPLY + VERIFIED, rebuild the Session Portal from PowerShell:

```powershell
cd G:\Vertex_Project\Development\vertex_session_portal
npm.cmd run build
.\VERTEX_SESSION_PORTAL_CURRENT.cmd
```

This is required so `out/main/index.js` matches the newly applied source.

## Source hashes

Baseline 000029 service SHA256:
`f227c2a168fa79b97e8abdc3bc6cf67c4bc8cd957e95b171068f6c7b5f8f899c`

000030 service SHA256:
`90e08991e40f77c86b1ff7b9c6605e4c3b3e186f145cea2982e4e2a245eba2a0`
