# Vertex Session Portal — Current Five-Window Portable Build 000044

## Purpose

Produce one unambiguous Windows executable from the current verified Session Portal source after Five Vera Window Scaler 000043H2.

Canonical launch path after verification:

`G:\Vertex_Project\Development\vertex_session_portal\release\current\VertexSessionPortal-current-win-x64\Vertex Session Portal.exe`

## Build strategy

This does not rely on the previously failed beta packager assumptions.

1. Verify the five-window source markers.
2. Run the current `npm run build`.
3. Ensure the installed Electron runtime exists.
4. Copy the Electron Windows runtime to a clean `release\current` staging directory.
5. Put the current compiled `out` and `package.json` in `resources\app`.
6. Discover production Node modules with `npm ls --omit=dev --parseable --all`.
7. Copy production modules, explicitly retaining `better-sqlite3`.
8. Accept the observed better-sqlite3 13.x Windows native layout at `prebuilds\win32-x64.node` as well as legacy `build\Release\better_sqlite3.node`.
9. Rename Electron's executable to `Vertex Session Portal.exe`.
10. Write build manifest + SHA256.
11. Launch with an isolated smoke-test user-data directory, verify the process stays alive for five seconds, then terminate it.

## Why this differs from 000041/H1

The old beta builder assumed `better-sqlite3\build\Release\better_sqlite3.node`.
Ray evidence later showed the installed better-sqlite3 13.0.3 uses prebuilt native binaries including `prebuilds\win32-x64.node`.

000044 packages the actual observed runtime layout rather than assuming an older binding layout.
