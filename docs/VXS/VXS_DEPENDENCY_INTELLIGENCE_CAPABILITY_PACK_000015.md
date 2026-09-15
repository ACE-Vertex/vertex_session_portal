# VXS Dependency Intelligence Capability Pack 000015

Adds lightweight read-only dependency intelligence:

- `vxs imports <path>`
- `vxs dependents <path>`
- `vxs impact <path>`

`imports` detects static ES imports/exports, CommonJS require(), and dynamic import().
`dependents` scans bounded source files for direct import references to the target.
`impact` summarizes import count, dependent count, file metadata, and a LOW/MEDIUM/HIGH
static impact hint.

Safety:
- workspace path confinement
- source files <= 2 MiB
- scan max 5000 files
- dependent hits max 120
- no filesystem mutation
- impact is explicitly labeled as a heuristic, not an execution guarantee
