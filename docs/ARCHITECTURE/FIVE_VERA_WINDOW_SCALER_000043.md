# VERTEX Session Portal — Five Vera Window Scaler 000043

## Mission

Add a Human-controlled mechanism to expand the Session Portal from the canonical three Vera browser windows up to five, using the open space in the MainFrame header.

## Behavior

- Default remains 3 Vera windows.
- Header exposes compact `3 / 4 / 5` controls.
- The selected count is persisted locally.
- `VERA 04` and `VERA 05` are created only when requested.
- Reducing the count removes only the dynamically-added windows.
- Each `vera-browser-session` keeps its existing per-session URL and width persistence.
- VRA Dispatch Lane remains after Vera browser windows.
- Search Vera remains retired.
- Browser DOM scraping is not introduced.
- Peer Relay target IDs are extended from Vera 01–03 to Vera 01–05.

## Safety

The apply script patches only two existing source files:

- `src/renderer/src/components/MainFrame/MainFrame.ts`
- `src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts`

It performs a full `npm run build`. If the build fails, those two files are restored to their exact pre-apply contents before returning failure.

The new scaler component is independently copied by Works and is removed by ordinary Works rollback if verification fails.
