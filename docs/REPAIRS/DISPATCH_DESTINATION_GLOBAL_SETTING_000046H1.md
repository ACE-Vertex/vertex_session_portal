# Dispatch Bay Global VRA Destination — 000046H1

## Root cause of 000046 failure

000046 attempted to patch `vra-dispatch-service.ts` by locating `_incoming` / receiving-path ownership there.

The Works evidence showed no such service candidate at all:

`SERVICE_CANDIDATES_BEGIN`
`SERVICE_CANDIDATES_END`

Therefore the apply script correctly failed closed and rolled the existing files back.

The destination bug belongs to the Electron browser download boundary, not to the VRA dispatch-service copy layer.

## H1 design

The Dispatch Bay owns one global VRA download destination.

- UI: one settings button immediately after the Dispatch Bay Reload / Refresh button.
- Default: `G:\Vertex_Project\Development\_incoming`
- Storage: Electron `userData/vra-dispatch-destination.json`
- Scope: all VRA downloads.
- Not per VRA card.
- Not per Vera session.
- Moving the portable EXE cannot change the destination.
- Electron `will-download` sets the VRA save path.
- H1 re-binds its download listener after WebContents load so it is placed after older path handlers.
- A completed-download relocation fallback moves a VRA into the configured destination if an older listener still overrode the path.

## Candidate executable

The running current EXE may hold DLL locks. H1 therefore packages side-by-side:

`G:\Vertex_Project\Development\vertex_session_portal\release\candidates\000046H1\VertexSessionPortal-000046H1-win-x64\Vertex Session Portal.exe`

Do not treat the `release\next` executable produced by failed 000046 as the feature build. 000046 had already rolled source changes back before that package step ran.
