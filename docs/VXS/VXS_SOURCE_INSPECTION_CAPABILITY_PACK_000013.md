# VXS Source Inspection Capability Pack 000013

Adds fast read-only source inspection without invoking full Ray:

- `vxs find <text> [path]`
- `vxs inspect <path> [start-line] [count]`
- `vxs hash <path>`
- `vxs stat <path>`

Safety boundaries:
- every requested path must remain inside the detected workspace
- text search skips heavy/generated directories
- search scans at most 4000 files and returns at most 120 matches
- search ignores files larger than 2 MiB
- inspect reads files up to 4 MiB and at most 400 lines per call
- hash reads files up to 128 MiB
- no filesystem mutation APIs are used

This is the lightweight source-navigation layer below full `vxs ray`.
