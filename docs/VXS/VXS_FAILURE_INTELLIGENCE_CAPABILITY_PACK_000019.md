# VXS Failure Intelligence Capability Pack 000019

Adds:

- `vxs triage <job-id>`

The command reads existing durable state only:

1. Session Portal VRA dispatch metadata
2. Workstation persistent Job Registry
3. Workstation Evidence JSON under headless/lane runtime

It classifies a Job into useful first-pass states including:

- INSPECTOR_REJECT
- SHA_MISMATCH
- APPROVAL_REJECT
- ROUTING_REJECT
- IDENTITY_CONFLICT
- REGISTRATION_ERROR / REGISTRATION_BLOCKED
- REGISTERED
- ALLOCATED / EXECUTING
- VERIFY_FAILED
- SUCCEEDED
- RETURN_QUEUED / RETURNED
- NOT_FOUND

No POST, ACK, retry, reexecution, process control, file mutation, or Human Gate
bypass is performed. This is a bounded local diagnostic layer intended to turn
Evidence-return troubleshooting into one VXS command.
