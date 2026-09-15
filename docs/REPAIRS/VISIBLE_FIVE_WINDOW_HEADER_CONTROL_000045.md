# Five-window header control visibility repair 000045

The five-window mechanism already exists in source and verifies logically, but the control is not visible in the running Session Portal UI.

This repair makes the existing `VeraWindowScaler` viewport-fixed in the open top-header area, independent of MainFrame header grid sizing or overflow.

Behavior remains:
- default 3 Vera windows
- selectable 3 / 4 / 5
- selection persists
- Vera 04 / 05 are dynamic
- current portable EXE is rebuilt after verification

Canonical executable:
`G:\Vertex_Project\Development\vertex_session_portal\release\current\VertexSessionPortal-current-win-x64\Vertex Session Portal.exe`
