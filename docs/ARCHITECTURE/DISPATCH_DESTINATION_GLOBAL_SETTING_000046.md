# Dispatch Bay Global Destination Setting 000046

## Human request

Dispatch Bay must own one global VRA destination setting. It is not a per-card and not a per-Vera setting.

A settings button is injected immediately to the right of the existing Dispatch Bay Reload / Refresh control.

## Behavior

- Click the settings button.
- Electron opens a native folder picker.
- Selected folder becomes the global VRA Dispatch destination.
- Setting is persisted under Electron `userData`, so moving the portable EXE does not silently move the destination.
- Default remains the legacy Works Receiving Bay:
  `G:\Vertex_Project\Development\_incoming`
- Every VRA dispatch uses the same selected destination.
- No per-card destination is introduced.
- No per-session destination is introduced.

## Packaging

Because the currently-running portable EXE may lock DLLs in `release\current`, 000046 packages a side-by-side build under:

`G:\Vertex_Project\Development\vertex_session_portal\release\next\VertexSessionPortal-next-win-x64\Vertex Session Portal.exe`

This avoids terminating the current Session Portal automatically.

After validating the new build, it can later replace/promote `release\current`.
