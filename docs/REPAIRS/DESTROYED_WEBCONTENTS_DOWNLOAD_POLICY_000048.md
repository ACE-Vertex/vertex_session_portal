# Session Portal — Destroyed WebContents Main Process Repair 000048

## Observed error

Electron showed:

`TypeError: Object has been destroyed`

from an `Immediate.<anonymous>` callback in the main process.

## Root cause

The 000046H2 VRA download policy registered this pattern:

`setImmediate(() => bindAsLastListener(contents.session))`

`web-contents-created` can be followed by destruction of that WebContents before the queued `setImmediate` runs. Accessing `contents.session` after destruction throws `TypeError: Object has been destroyed`, and because the callback was not guarded it became an uncaught main-process exception.

The same risk existed in the later `did-finish-load` callback.

## Repair

000048 captures `contents.session` synchronously while the WebContents is alive, then queues only the already-captured `Session` reference.

It also wraps delayed binding in a try/catch so a failed policy refresh can never crash the Electron main process.

The VRA save destination behavior from 000046H2 is preserved.

## Publish target

After source verification, the existing 000047 publisher is run again so the repaired build is placed at the single canonical location:

`G:\Vertex_Project\Development\vertex_workstation\SESSION_PORTAL_LATEST\Vertex Session Portal.exe`

The root launcher remains:

`G:\Vertex_Project\Development\vertex_workstation\START_SESSION_PORTAL_LATEST.cmd`
