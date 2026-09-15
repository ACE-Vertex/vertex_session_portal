# Vertex Session Portal Official Portable Release 000087V5H1

## Root cause seen in the user's video

The official portable package itself became the Project Explorer root:

`VertexSessionPortal-000087V5-win-x64`

The Explorer displayed Electron runtime files such as `locales`, `resources`,
`chrome_100_percent.pak`, DLLs, and the packaged EXE.

That means the portable Electron process inherited the package directory as its
process working directory. Development launch had used
`G:\Vertex_Project\Development\vertex_session_portal`, so the Project Tree's existing
workspace boundary contract saw a different root after packaging.

The project-tree feature itself was not lost. The launch context changed.

## H1 repair

The canonical clickable file remains `Vertex Session Portal.exe`, but it is now a
small Windows GUI launcher. The actual Electron runtime is
`Vertex Session Portal.runtime.exe`.

The launcher resolves the real workspace root by:

1. `VERTEX_SESSION_PORTAL_WORKSPACE_ROOT`, if valid
2. walking ancestors for the real source markers
3. `workspace-root.txt` created by the official build
4. package directory only as a fail-soft fallback

It then starts the Electron runtime with the real workspace root as process cwd.

This preserves the current Project Tree code and avoids patching Explorer logic merely
to compensate for packaging.

The smoke test deliberately starts from the wrong package cwd and confirms the runtime
survives for five seconds.

Production source mutation: zero.
