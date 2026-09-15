# VXS Change Intelligence Capability Pack 000014

Adds read-only change/context intelligence:

- `vxs changed`
- `vxs diffstat`
- `vxs refs <symbol>`
- `vxs todo [path]`

Behavior:
- `changed` uses `git status --short --untracked-files=normal`
- `diffstat` uses `git diff --stat` and `git diff --cached --stat`
- `refs` searches bounded source files for a symbol
- `todo` searches TODO/FIXME/HACK/XXX markers

Safety:
- no Git mutation commands
- no filesystem writes/deletes
- source search max 5000 files / 120 hits
- path-scoped TODO search cannot escape the detected workspace
