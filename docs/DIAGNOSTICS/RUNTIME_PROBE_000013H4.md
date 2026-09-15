# Runtime Probe 000013H4 — renderer probe boundary hardening

## H3 Evidence

H3 proved:

- Electron binary exists,
- build passes,
- CommonJS preload build exists,
- Electron starts,
- production renderer reaches `did-finish-load`.

The failure changed from "0 sessions" to `UnknownVizError` immediately after renderer load.

Because the failure occurs while the Main process is requesting the renderer probe result,
H4 treats the cross-process result transport itself as the next suspect.

## H4 repair

The runtime probe no longer returns a nested JavaScript object directly from
`webContents.executeJavaScript`.

Instead the renderer returns one primitive JSON string:

`JSON.stringify({ ...probe... })`

The Main process parses that string locally.

This avoids structured-clone / V8 marshalling ambiguity at the Electron boundary and also
adds per-attempt diagnostics so the next Evidence will identify whether the bridge is
unavailable, the session bootstrap is delayed, or the probe script itself throws.

No Session Portal product behavior changes.
