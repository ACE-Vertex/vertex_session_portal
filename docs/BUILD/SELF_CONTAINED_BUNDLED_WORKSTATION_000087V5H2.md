# Vertex Session Portal — Self-Contained Official Release 000087V5H2

The formal product boundary is now:

```text
VertexSessionPortal-000087V5H2-win-x64/
├─ Vertex Session Portal.exe
├─ Vertex Session Portal.runtime.exe
├─ resources/
│  ├─ app/
│  └─ workstation-server/
│     ├─ vertex-workstation.exe
│     ├─ BUNDLED_WORKSTATION.json
│     └─ runtime/
│        └─ lanes/
└─ ...
```

## Startup

`Vertex Session Portal.exe` is the only Human-facing start point.

On startup it checks `127.0.0.1:47832`.

- If a Workstation server is already listening, it does not create a duplicate.
- If the port is free, it starts the bundled `vertex-workstation.exe` hidden.
- It then starts the Electron Session Portal runtime.
- Closing Portal does not kill Workstation; the factory stays a separate OS process.

## Authority

Bundling does not merge the processes or authorities.

- Session Portal = observation / Human Gate / routing / UI
- Workstation = registry / scheduler / lane allocation / APPLY / VERIFY / Evidence
- Human Gate remains mandatory.
- Workstation remains lane allocation authority.
- v1 binds only to `127.0.0.1`.
- Max logical lanes = 32; default logical lanes = 5.

## Build

The release job builds the **current** Workstation headless source during packaging,
smoke-starts it on an isolated random loopback port, and only then places the binary
into the Session Portal release.

The Portal runtime is also built from current source and smoke-started before the
release is promoted to `release/official`.

## Evidence bridge

The read-only Evidence body bridge trusts both:

- Development Workstation lanes
- bundled `resources/workstation-server/runtime/lanes`

No arbitrary evidence path is accepted.
