# Vertex Shell Limited Session Portal Wiring 000080V4B

V4A proved the foundation and captured current production anchors.

V4B avoids modifying high-conflict Portal files:
main/index.ts, preload/index.ts, shared/contracts.ts, MainFrame.ts,
VRA Dispatch, Human Gate, and Workstation.

It uses the VERA4-owned Event Ray main-process bootstrap to load a dedicated
Vertex Shell Host Bridge.

The bridge accepts commands only from a real BrowserWindow host WebContents.
Guest Vera/ChatGPT webviews are not shell authorities.

Human UX:
- floating/dockable shell inside Session Portal
- drag to float, double click to re-dock
- native resize
- CWD, RUN, STOP, CLEAR
- Up/Down command history
- IME composition Enter guard
- PIN toggles Session Portal Always-On-Top
- FRONT brings Portal forward
- Ctrl+Alt+Space globally summons Portal + Shell

This generation is direct-human only.
PowerShell remains the compatibility organ.

After VERIFIED:
1. npm.cmd run build
2. fully restart Session Portal
3. test Ctrl+Alt+Space and PIN
4. optional: python scripts\probe_vertex_shell_runtime_000080V4B.py
