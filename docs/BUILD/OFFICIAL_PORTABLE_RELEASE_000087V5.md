# Vertex Session Portal — Official Portable Release 000087V5

Target project:

`G:\Vertex_Project\Development\vertex_session_portal`

This job creates a formal Windows x64 portable build from the **current source**.

## Output

`G:\Vertex_Project\Development\vertex_session_portal\release\official\VertexSessionPortal-000087V5-win-x64\Vertex Session Portal.exe`

The directory is a self-contained Electron portable package. The EXE must remain with
its sibling DLL/resources files; it is not a single-file executable.

## Build sequence

1. `npm run build`
   - TypeScript typecheck
   - electron-vite production build
2. Copy the installed Electron Windows runtime.
3. Rename `electron.exe` to `Vertex Session Portal.exe`.
4. Package current `out/`, `package.json`, lock file, and production Node modules.
5. Verify native `better-sqlite3` `.node` module is present.
6. Write build manifest and EXE SHA256.
7. Smoke-start for 5 seconds using isolated `--user-data-dir`.
8. Only after smoke PASS, publish into `release/official/...`.
9. Write `release/official/CURRENT.txt`.

Production source files are not edited by this build.
