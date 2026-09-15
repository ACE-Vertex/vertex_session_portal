# VERTEX SESSION PORTAL — BETA BUILD REPAIR 000041H1

000041 reached a clean source build, but packaging failed at the native runtime layer:

- source build: PASS
- compiled main/preload/renderer: PASS
- `better-sqlite3` source package: present
- packaged `better_sqlite3.node`: missing

Root issue addressed by H1:
`npm ls --omit=dev --parseable --all` is no longer used as the authoritative packaging list.

H1 instead:
1. verifies/rebuilds the Electron-ABI `better_sqlite3.node` in the source tree if needed;
2. resolves the runtime dependency graph from package.json/package package.json files;
3. copies the actual runtime package directories, including native binary contents;
4. explicitly verifies packaged `better_sqlite3.node`;
5. smoke-starts the packaged beta EXE for six seconds;
6. emits portable folder, ZIP, manifest and SHA-256 receipt.

Application source is not modified. This is a beta packaging/build repair only.
