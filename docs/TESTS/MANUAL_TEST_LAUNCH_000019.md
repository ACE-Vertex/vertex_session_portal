# Session Portal Manual Test Launch 000019

This artifact does not modify Session Portal product source.

It starts the already-built Electron application in normal user-visible mode so Katsu
can manually inspect and operate the current Session Portal.

## Launch mode

- normal Electron application
- no diagnostic probe environment flags
- Chromium/Electron GPU acceleration remains at default policy
- detached process so Works can finish verification while the Portal window stays open

## Evidence

The launcher writes:

`EVIDENCE/TEST_LAUNCH_000019/launch.json`

plus stdout/stderr logs.

A PASS means the Electron process stayed alive for at least 2.5 seconds after launch.
It does not claim that every manual UI interaction is correct; this stage is explicitly
for human test operation.
