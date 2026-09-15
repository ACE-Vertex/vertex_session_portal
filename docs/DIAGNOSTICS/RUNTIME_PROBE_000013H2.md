# Runtime Probe 000013H2 — scoped Electron binary install repair

## Evidence from H1

The Electron npm package itself exists and contains `cli.js`, but its binary payload
`node_modules/electron/dist/electron.exe` is still absent.

H1 also proved:

- `npm rebuild electron` exits successfully;
- npm emits an `allowScripts` warning;
- the executable remains missing afterwards.

This means a package-level rebuild is not sufficient in this environment because the
Electron download/install script is not being materialized through the npm policy path.

## H2 repair

H2 does not disable npm security policy globally and does not use `--force` or
`--legacy-peer-deps`.

Instead, only when Electron's local binary is missing, it explicitly invokes the already
installed Electron package's own local script:

`node node_modules/electron/install.js`

with the Electron package directory as its working directory.

That operation is scoped to this project and exists only to materialize Electron's runtime
binary. After that, the original build + runtime probe + screenshot + topology checks run
unchanged.

No Session Portal product behavior, CSS, SQLite schema, MSSQL boundary or Virtual ARD
architecture is changed.
