# Root Workstation EXE + Horizontal Scrollbar Retirement 000083V5

## Workstation launch

Portal-managed Workstation startup no longer needs a persistent Cargo/CMD console.

On an explicit Human START/REPLACE action:

1. Resolve the real `vertex_workstation` root.
2. If `vertex-workstation.exe` is missing or older than Workstation source inputs,
   build the current headless binary with Cargo `--release`.
3. Build output is isolated under `runtime/portal-managed-release-target`.
4. Publish the finished binary to:
   `G:\Vertex_Project\Development\vertex_workstation\vertex-workstation.exe`
5. Launch that root EXE directly with:
   `workstation serve --bind 127.0.0.1:47832 --root ...`
6. Both the build and server spawn use `windowsHide=true`, `shell=false`,
   and no inherited stdio.

The CLI remains a normal console-capable Rust binary when the user launches it
manually. We do NOT change Rust `windows_subsystem`, because that would damage CLI use.

Publication uses `.next` / `.previous` replacement with fail-closed restoration.

## Session Portal horizontal scrollbar

Main-frame auto-fit remains unchanged.

Chromium's horizontal scrollbar chrome is hidden on the host/main/session viewport.
The horizontal layout mechanics remain intact, so no content-width contract is removed.
This specifically prevents pointer traversal across an overlay scrollbar from causing
the visible flicker reported after auto-fit.

## Safety

- no blind process kill
- validated legacy replacement preserved
- Workstation bind remains 127.0.0.1
- Human START action is required to build/publish the root EXE
- VERIFY does not compile/publish the Workstation EXE
- VERIFY does not mutate Workstation production source
- existing Cargo-run fallback remains as last-resort compatibility
