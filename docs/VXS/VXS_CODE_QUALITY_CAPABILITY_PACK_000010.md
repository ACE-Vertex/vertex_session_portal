# VXS Code Quality Capability Pack 000010

Adds safe developer-facing commands:

- `vxs workspace`
- `vxs scripts`
- `vxs check`
- `vxs format --check`

Routing:
- Node `vxs check` -> `typecheck` then `check` package script
- Rust `vxs check` -> `cargo check`
- Python `vxs check` -> `python -m ruff check .`
- Node format check uses only explicit check-style package scripts
- Rust format check -> `cargo fmt --all -- --check`
- Python format check -> `python -m ruff format --check .`

`vxs format` without `--check` fails closed. This pack does not add a formatting mutation command.

Previously VERIFIED Vertex commands remain intact:
`vxs ray`, `vxs vra`, `vxs workstation`, `vxs evidence`.
