# VXS Job Intelligence Capability Pack 000020

Adds read-only durable Job navigation:

- `vxs jobs [1-100]`
- `vxs failures [1-100]`
- `vxs timeline <job-id>`

The module scans the existing Workstation persistent Job Registry, bounds the
scan, recursively extracts records carrying `job_id`, deduplicates them, and
sorts by the best available durable timestamp.

`jobs` lists recent durable Jobs.
`failures` filters failure/rejection/error/conflict/rollback states.
`timeline` shows lifecycle timestamp fields for one Job.

No retry, ACK, reexecution, HTTP POST, file mutation, process mutation, or
Human Gate bypass is performed.
