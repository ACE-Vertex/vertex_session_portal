# Vertex Shell Ctrl+N New Tab 000080V4F

Adds one keyboard shortcut to the existing Vertex Shell V4E UI.

## Shortcut

`Ctrl+N` while Vertex Shell is visible:
- prevents the normal host default
- creates a new Vertex Shell tab
- inherits the current tab CWD
- activates the new tab
- focuses the command input

The existing `+` button remains unchanged.

## Guard

When Vertex Shell is hidden, Ctrl+N is not intercepted by this host UI handler.

## Preserved

- Ctrl+Alt+Space show/hide toggle
- Ctrl+B always-on-top OFF
- Ctrl+F always-on-top ON
- resizable shell panel
- right-click paste
- COPY
- IME guard
- single-flight pwsh backend
- Human-only authority
