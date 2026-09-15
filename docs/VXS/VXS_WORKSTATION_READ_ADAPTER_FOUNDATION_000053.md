# VXS Workstation Read Adapter Foundation 000053

## Purpose

Create one canonical **read-only** boundary between Vertex eXecution Shell (VXS)
and Vertex Workstation without changing any currently running VXS command.

This is intentionally a foundation step, not a gateway rewrite.

## Frozen architecture

### Official Control Plane

VXS read requests that have official Workstation API routes use:

`http://127.0.0.1:47832`

Current read routes:

- `GET /v1/health`
- `GET /v1/safety`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/evidence`

### Durable forensic observation

Commands that need information not currently exposed by a canonical HTTP read API
may continue to inspect bounded local durable state:

- `runtime/headless/job-registry`
- `runtime/headless/evidence`
- `runtime/lanes`
- Portal dispatch metadata / bounded logs

This is **observation**, not execution authority.

## Authority

Adapter authority class: `OBSERVE`.

The adapter MUST NOT:

- register or dispatch a job,
- acknowledge Evidence,
- allocate a lane,
- call APPLY / VERIFY / ROLLBACK,
- mutate filesystem state,
- become a second Return Queue,
- become a second Evidence Router,
- become a second ACK path,
- infer origin identity.

Human Gate and `HUMAN_APPLY` remain canonical for production mutation.

Workstation remains Lane Allocation Authority.

## External I/O direction

Future VXS External I/O remains Hybrid:

- bounded external reads may eventually use typed VXS `OBSERVE` capabilities,
- external mutation becomes a Workstation job under Human Gate,
- VXS does not become an unrestricted Agent shell.

Suggested future authority metadata:

- authority: `HUMAN_APPLY`
- side_effect_class: `EXTERNAL_MUTATION`

`EXTERNAL_MUTATION` never replaces Human approval.

## Next step

After this foundation verifies, wire the existing VXS read commands to this
adapter using current-source anchors, one capability family at a time.

Do not build a generic External Gateway yet.
