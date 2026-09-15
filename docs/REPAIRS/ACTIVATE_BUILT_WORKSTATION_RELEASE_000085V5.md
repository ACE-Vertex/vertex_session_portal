# Activate Built Workstation Release 000085V5

000084V5 successfully built the current headless Workstation.

Canonical release executable:

`G:\Vertex_Project\Development\vertex_workstation\release\vertex-workstation.exe`

This patch makes Session Portal treat that binary as the preferred managed runtime.

When Portal is restarted and the old compatible Cargo/CMD-backed Workstation is still
ONLINE, the UI exposes `ACTIVATE RELEASE EXE`.

That explicit Human action:

1. confirms the release binary is present/current,
2. validates the current loopback Workstation listener,
3. retires only that validated listener,
4. launches `release\vertex-workstation.exe` directly,
5. uses `windowsHide=true`, `shell=false`, and detached/no inherited console semantics.

No Rust `windows_subsystem` change is made, so manual CLI use remains intact.

The existing 000083 horizontal scrollbar retirement remains in production and is not
modified by this patch.
