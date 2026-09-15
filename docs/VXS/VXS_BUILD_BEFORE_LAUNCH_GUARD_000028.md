# VXS Build-Before-Launch Guard 000028

Evidence-derived cause:

- `package.json.main` is `./out/main/index.js`.
- `package.json.scripts.build` is `npm run typecheck && electron-vite build`.
- Current `src` contains the new VXS capability source.
- Current `out` does not contain the new VXS preparation schema.

Therefore the running Electron generation can be older than production source
when Session Portal is launched without rebuilding `out`.

This pack adds:

`VERTEX_SESSION_PORTAL_CURRENT.cmd`

Behavior:

1. resolve the project root from `%~dp0`
2. run `npm.cmd run build`
3. fail closed if build fails
4. require `out/main/index.js`
5. launch `node_modules/.bin/electron.cmd .`

Important:

- VERIFY does not run the build and does not mutate `out`.
- The launcher performs the build only when the human explicitly launches it.
- It does not kill existing Electron processes.
- It does not touch Observation / Return Bus, ACK, Registry lifecycle, VRA
  routing, Human Gate, or Workstation lane allocation.
- Close the currently running Session Portal before using the launcher, so the
  newly built runtime is the only Session Portal generation in use.
