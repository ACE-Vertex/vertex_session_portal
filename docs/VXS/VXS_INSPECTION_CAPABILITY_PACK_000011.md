# VXS Inspection Capability Pack 000011

Adds a separate inspection module instead of expanding the command registry with
implementation details.

Commands:
- `vxs env` — safe environment summary; never dumps environment values
- `vxs which <tool>` — resolve executable paths
- `vxs tree [1-4]` — bounded workspace tree, max 300 entries
- `vxs deps` — local package.json dependency inspection

All commands are read-only.

Heavy/generated directories are omitted from tree output:
`.git`, `node_modules`, `target`, `dist`, `out`, `coverage`, `.vite`,
`__pycache__`, `.venv`, `venv`, `runtime`.

Previously VERIFIED development and Vertex commands are preserved.
