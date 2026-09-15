# Dispatch Bay Global VRA Destination 000046H2

## H1 failure

H1 reached TypeScript build and failed in `src/main/index.ts` around lines 77–84 with parser errors.

The H1 patcher located the "last single-line import" and inserted registration calls after it. The current `src/main/index.ts` contains multiline imports, so the insertion point could land inside an unfinished import declaration.

The transaction rollback succeeded, which is why the later static verifier correctly reported that the existing entry files were unchanged.

## H2 repair

H2 no longer edits any import list and does not insert executable calls into `index.ts`.

Instead:

- `src/main/index.ts` gets one complete side-effect import as its first line.
- `src/preload/index.ts` gets one complete side-effect import as its first line.
- `MainFrame.ts` gets one complete side-effect import as its first line.

The actual registration lives in separate modules.

This is safe with single-line or multiline imports and is idempotent.

## Feature

Dispatch Bay owns one global VRA save destination.

- settings button immediately after Reload/Refresh
- native folder picker
- default `G:\Vertex_Project\Development\_incoming`
- persists in Electron userData
- not per VRA card
- not per Vera session
- independent of portable EXE location
- Electron `will-download` policy plus completed-download relocation fallback

## Candidate executable

After verification:

`G:\Vertex_Project\Development\vertex_session_portal\release\candidates\000046H2\VertexSessionPortal-000046H2-win-x64\Vertex Session Portal.exe`
