# Root Workstation EXE Migration — 000083V5H1

## Confirmed logic defect in 000083

The root EXE was not generated because `startInternal()` checked Workstation health first.

If an already-running Workstation was compatible, the function immediately returned
`ONLINE` before `ensureRootReleaseBinary()` was reached.

At the same time, the renderer hid the START button whenever Workstation was ONLINE.

Therefore an old-but-compatible Workstation could keep running forever while the new
root release build path remained unreachable.

## H1 behavior

When Workstation is ONLINE and `vertex_workstation/vertex-workstation.exe` does not
exist, the Portal now exposes:

`MIGRATE ROOT EXE`

That is an explicit Human action.

On click:

1. Build/publish the current headless release to the project root.
2. If the current listener is already that exact root EXE, leave it alone.
3. Otherwise validate PID + executable path + command line using the existing
   fail-closed listener identity gate.
4. Stop only that validated Workstation listener.
5. Launch the new root EXE directly with `windowsHide=true`.
6. The old visible Cargo/CMD-backed server is retired.

No blind kill is introduced.

Expected root file:

`G:\Vertex_Project\Development\vertex_workstation\vertex-workstation.exe`
