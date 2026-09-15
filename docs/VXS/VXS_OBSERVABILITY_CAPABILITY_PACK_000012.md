# VXS Observability Capability Pack 000012

Adds read-only local observability:

- `vxs logs [portal|workstation] [10-300]`
- `vxs trace <job-id>`

`vxs logs` tails a bounded number of lines from recent readable log-like files.

`vxs trace` searches recent Portal/Workstation logs plus durable Workstation
job-registry JSON for exact Job ID matches.

Safety:
- no writes
- no deletes
- bounded file tail reads
- bounded hit counts
- validates Job ID characters
- generated-heavy directories are not recursively traversed

This directly addresses Evidence returns that expose only local stdout/stderr
paths while keeping the Human UI minimal.
