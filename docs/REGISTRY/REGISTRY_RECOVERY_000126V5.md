# Registry Recovery 000126V5

Purpose:
Verify that the Registry can recover durable identity after restart.

Checks:
- registry_id survives reload
- job_id remains unique
- artifact_id binding remains intact
- correlation_id remains queryable
- evidence_id remains attachable
- duplicate registration is rejected/idempotent
- VLog ordering remains append-only

Not included:
- AUTO -> BAY adapter
- POST /jobs
- Evidence ACK mutation
- Lane allocation

Ownership:
Workstation owns lane allocation.
Human Gate remains required.
