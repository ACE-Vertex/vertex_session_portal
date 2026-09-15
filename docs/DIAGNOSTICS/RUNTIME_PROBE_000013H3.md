# Runtime Probe 000013H3 — sandboxed preload format repair

## What H2 proved

H2 successfully:

- materialized Electron's Windows executable,
- built Main / Preload / Renderer,
- launched Electron,
- loaded the production renderer,
- rendered the MainFrame and Explorer.

But all Vera sessions remained at zero.

The renderer's initial state is intentionally empty until the preload bridge calls the
main-process Workstation IPC bootstrap. Therefore this pattern points at the preload
bridge, not at the SQLite seed or Session component layout.

## Root cause

The BrowserWindow is intentionally sandboxed.

Electron's ESM documentation states that sandboxed preload scripts cannot use ESM imports.
The current build emitted `out/preload/index.mjs`, so the preload bridge was not a valid
format for the chosen sandboxed renderer model.

## Repair

Keep the security model:

- `sandbox: true`
- `contextIsolation: true`
- `nodeIntegration: false`

Change only the preload build to CommonJS:

- output: `out/preload/index.cjs`
- Main points BrowserWindow preload to `index.cjs`

The runtime probe now explicitly checks `window.vertexPortal` as `PRELOAD_BRIDGE=PASS`
before accepting the four-session topology.

This preserves the Session Portal architecture and strengthens the runtime Evidence.
