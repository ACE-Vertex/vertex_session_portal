# Vertex Session Portal — Publish Latest to Vertex Workstation 000047

## Canonical human-facing location

After verification, always launch:

`G:\Vertex_Project\Development\vertex_workstation\SESSION_PORTAL_LATEST\Vertex Session Portal.exe`

Root launcher:

`G:\Vertex_Project\Development\vertex_workstation\START_SESSION_PORTAL_LATEST.cmd`

## Rules

- Current Session Portal source must still contain max 5 Vera windows.
- Dispatch Bay global VRA destination setting must still exist.
- Default VRA destination remains `G:\Vertex_Project\Development\_incoming`.
- Current source is rebuilt before packaging.
- Staged portable build is smoke-launched for 5 seconds.
- Previous latest build is retained as `SESSION_PORTAL_PREVIOUS`.
- Human no longer needs to remember release/current, release/next, or candidates paths.
