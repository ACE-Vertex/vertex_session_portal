# VXS Orchestration Capability Pack 000017

Adds a compact development decision/orchestration layer:

- `vxs preflight`
- `vxs verify quick`
- `vxs verify full`

`preflight` is observation-only and summarizes:
- workspace type/markers
- Git branch and changed/untracked row count
- local Workstation listener observation on 127.0.0.1:47832
- core tool availability
- detected package scripts

`verify quick` creates a fail-fast verification pipeline from detected ecosystems.

Node candidates:
- typecheck or check
- lint
- explicit format-check script
- test

Rust:
- cargo check
- cargo fmt --all -- --check
- cargo test

Python:
- ruff check
- ruff format --check
- pytest

`verify full` adds available build/deeper validation steps:
- Node build
- Cargo clippy + cargo build
- Python build for pyproject projects

No process kill, restart, Git mutation, or source-format mutation is added.
