# Runtime Probe 000013H1 — Electron launcher repair

## Evidence from 000013

The first runtime probe failed before Electron startup because the verifier assumed
that the runnable Electron command would exist as one of:

- `node_modules/electron/dist/electron.exe`
- `node_modules/.bin/electron.exe`

The second path is not a reliable Windows npm layout assumption, and direct executable
discovery is unnecessary because the Electron npm package provides `cli.js`.

## Repair

000013H1 launches the project through:

`node node_modules/electron/cli.js .`

This lets Electron's own package CLI resolve the packaged executable.

If the package exists but the downloaded Electron binary is missing, the verifier performs:

`npm rebuild electron`

once, then verifies that `node_modules/electron/dist/electron.exe` exists before launch.

No Session Portal product architecture, renderer, SQLite model, pane sizing, CSS, or
Virtual ARD behavior is changed by this repair.

The runtime probe still verifies the original 000013 requirements and uses the same
screenshot / JSON Evidence paths.
