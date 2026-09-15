# UI Control Channel 000015

000014 proved that human clicks can move Priority between Vera panes,
switch PROJECT/VCR/VCA, and persist Workstation state through SQLite.

000015 activates the separate **Vera/Agent → UI Control Channel** that was
already part of the Session Portal architecture.

## Important boundary

Visible conversation text is **not** parsed for magic UI commands.

The flow is:

`Vera / Session Manager`
→ `Electron Main authority validator`
→ serialized `portal:control` IPC
→ secure Preload bridge
→ Chromium Renderer
→ local `PortalControlChannel`
→ `VertexMainFrame`

The initial command vocabulary is intentionally UI-only:

- `SIDEBAR_SWITCH`
- `SESSION_FOCUS`
- `SESSION_EXPAND`
- `VCR_OPEN`
- `VCA_SEARCH`
- `PROJECT_REVEAL`

This channel cannot:

- execute shell commands,
- mutate project files,
- write canonical VCR/VCA data,
- delete data,
- send external messages.

Those capabilities belong to separate gated authority paths.

## 000015 probe

The diagnostic run sends commands from Electron Main as a stand-in for a
future Vera/Agent producer and verifies:

1. Focus Vera 03.
2. Switch sidebar to VCA.
3. Open `VERTEX.VRA` in VCR.
4. Search VCA for `超絶採用`.
5. Reveal `src/main/index.ts` in PROJECT.
6. Expand Search Vera.
7. Reload and verify SQLite preserves Search Vera Priority and PROJECT.
8. Attempt an unsupported `SHELL_EXECUTE` command and verify rejection.
9. Capture JSON + screenshot Evidence.

This is the first real "Vera can point at the UI" infrastructure.
It is still not a real LLM connection.
