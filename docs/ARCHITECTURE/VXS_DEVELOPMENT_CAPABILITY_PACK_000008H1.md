# VXS Development Capability Pack 000008

## Phase transition

VXS moves from foundation work into development capability growth.

The key design rule is:

> VXS decides *what capability should run*; the existing execution engine owns
> process lifecycle, streaming, single-flight and STOP.

This avoids blocking the Electron main process with long-running synchronous
build/test operations.

## Commands

### `vxs build`

Auto-detect route:

- Node: detected package manager + `build` package script
- Rust: `cargo build`
- Python package: `python -m build`

### `vxs test`

- Node: detected `test` package script
- Rust: `cargo test`
- Python: `python -m pytest`

### `vxs lint`

- Node: detected `lint` package script
- Rust: `cargo clippy --all-targets`
- Python: `python -m ruff check .`

### `vxs run <script>`

Runs only a script that is actually present in the detected Node
`package.json`. Script names are validated before routing.

### `vxs git ...`

Initial Git pack is deliberately read-only:

- `vxs git status`
- `vxs git diff`
- `vxs git staged`
- `vxs git branch`
- `vxs git log`
- `vxs git help`

Commit / add / reset / checkout / push are not introduced in this pack.

## Runtime route

For routed commands VXS emits:

- capability
- workspace root
- adapter
- exact execution command

Then the existing PowerShell compatibility execution engine performs the
actual child process.

Therefore existing behavior remains available:

- stdout / stderr streaming
- output byte cap
- single-flight execution
- STOP
- command history
- existing VXS semantic colors

## Next packs

The architecture can now grow with dedicated capability modules for:

- Ray
- VRA
- Workstation jobs / lanes
- Evidence
- DB
- environment / runtime
- package / dependency operations


## H1 verification correction

000008 implementation was rolled back because VERIFY incorrectly required a
literal `npm` token inside the generic Node adapter.

The implementation intentionally routes through the detected
`workspace.packageManager`, allowing npm, pnpm, or yarn.

000008H1 changes the VERIFY contract only:

- require generic `workspace.packageManager` routing
- require `packageExecutable(workspace.packageManager)`
- do not require the literal string `npm`

Production capability code is unchanged from 000008.
