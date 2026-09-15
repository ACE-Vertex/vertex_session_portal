# VXS 000009 Registration Failure Ray 000009R2

Target failed card:
- artifact_id: `vertex-session-portal-vxs-vertex-capability-pack-000009`
- job_id: `job-vera03-vxs-vertex-capability-42f4e345-e5ec-4506-affd-79778057c607`
- expected artifact SHA256: `4219224c24b4644d57f8446d374b99e93a4f5b80478029b54181eef7ca208212`

Observed UI state before this Ray:
- Human Approval: APPROVED
- Allocated Lane: NOT ALLOCATED
- System Status: FAILED

This means the failure is before normal lane execution.

The Ray checks, read-only:
1. Workstation `/v1/health`
2. `GET /v1/jobs/{job_id}`
3. `GET /v1/jobs/{job_id}/evidence`
4. `_incoming` presence and exact VRA SHA256
5. sidecars/logs/state files containing the artifact/job/hash
6. likely boundary classification

No POST, APPLY, VERIFY, rollback, safety transition, ACK, or production mutation.
