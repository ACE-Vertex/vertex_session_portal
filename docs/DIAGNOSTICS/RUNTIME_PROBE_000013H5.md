# Runtime Probe 000013H5 — Chromium Viz capture repair

## H4 proved the core

H4 returned:

- `bridge=YES`
- `sessions=4`

on the first probe attempt.

That proves the CommonJS preload bridge, Workstation IPC bootstrap and four-session renderer
topology are alive before the screenshot stage.

The remaining `UnknownVizError` occurs after that probe and is therefore isolated to the
Chromium/Electron screenshot surface-copy path (`capturePage`), not Session Portal state.

## H5 repair

H5 moves all topology/width logging and `runtime-probe.json` creation before screenshot
capture.

For screenshot Evidence it then:

1. disables background throttling for the diagnostic WebContents,
2. shows the BrowserWindow with `showInactive()` so focus is not intentionally stolen,
3. invalidates the WebContents to request painting,
4. waits for two `requestAnimationFrame` cycles,
5. waits briefly for compositor presentation,
6. retries `capturePage()` up to eight times.

Electron maps Chromium's CopyFromSurface `kUnknownVizError` to the string
`UnknownVizError`, so retrying only the screenshot stage is appropriate here.

No product UI, SQLite, session topology, security boundary, CSS architecture or Virtual ARD
behavior is changed.
