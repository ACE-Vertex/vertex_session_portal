# VXS Formalization 000002

This change formally brands the embedded Session Portal shell as:

- VXS
- Vertex eXecution Shell
- Version 0.1.0

Supported identity commands:

- `--version`
- `vxs --version`

Compatibility intentionally preserved:

- internal `VertexShell*` TypeScript contracts
- `window.api.vertexShell`
- `vertex-shell-unit` custom element
- existing shell history/evidence schema
- current PowerShell compatibility backend
- existing host bridge (not modified by this VRA)

Canonical VXS concept, details, and component manifest are stored separately under:

`G:\Vertex_Project\Development\vertex_manifest\vxs`

No VRA schema, Workstation, Lane authority, Human Gate, Registry, or Evidence contract changes are included.
