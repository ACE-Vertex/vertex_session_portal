# VXS Vertex Capability Pack 000009

Adds the first Vertex-native observation/control-plane commands to VXS.

## Commands

### vxs ray [pattern]

Read-only workspace observation.

- structural summary without a pattern
- bounded textual anchor search with a pattern
- ignores .git, node_modules, target, out, runtime and other heavy/generated trees
- no writes

### vxs vra ...

Aliases the existing Session Portal Native VRA command path.

- `vxs vra list`
- `vxs vra dispatch <artifact-id|card-id|filename>`

The renderer rewrites `vxs vra ...` to the already-existing `vra ...` command
before the Host's Native VRA handler runs.

No second dispatch implementation is created.
Human dispatch semantics remain owned by the existing Portal Human Gate.

### vxs workstation ...

Read-only Workstation HTTP control-plane access:

- `vxs workstation status` -> GET /v1/health
- `vxs workstation safety` -> GET /v1/safety
- `vxs workstation job <job-id>` -> GET /v1/jobs/{job_id}

Loopback endpoint is fixed to `http://127.0.0.1:47832`.

### vxs evidence <job-id>

Read-only:

- GET /v1/jobs/{job_id}/evidence

No ACK is exposed by this pack.

## Explicitly absent

- HTTP direct APPLY
- HTTP direct VERIFY
- HTTP direct ROLLBACK
- Evidence ACK
- safety state mutation
- lane allocation mutation
- auto dispatch

VXS remains an observation and Human-command entry layer; Workstation retains
execution and lane authority.
