# Vertex Shell Toggle + Tabs + Resize 000080V4E

## Human controls

- Ctrl+Alt+Space: Vertex Shell visibility ON/OFF
- Ctrl+B: Session Portal always-on-top OFF while Vertex Shell is visible
- Ctrl+F: Session Portal always-on-top ON while Vertex Shell is visible
- `+`: create a new Vertex Shell tab workspace
- bottom-right grip: resize width/height
- right click anywhere inside Vertex Shell: paste OS clipboard
- COPY: copy current tab's last command/result

## Tabs

Tabs keep independent UI state:
- CWD
- command text
- output buffer
- command history

The current pwsh compatibility backend remains single-flight:
only one PowerShell command executes at a time across all tabs.
This preserves the existing safety boundary.

## Resize

The panel can be resized in both dimensions.
The last width/height are stored in host-renderer localStorage and restored.

## Scope

Only `src/main/shell/vertex-shell-host-bridge.ts` is changed in production source.
No Session Portal main index, preload, MainFrame, VRA Dispatch, Human Gate,
Workstation, or Vertex Shell service mutation.
