# Dispatch → Registration → Pre-Allocation Ray 000092V5

Purpose: determine why an APPROVED Session Portal VRA card reaches ERROR while Workstation still reports no allocated lane.

This artifact is investigation-only.

It traces:
1. Portal atomic publish / commit sidecar.
2. Portal Workstation HTTP registration.
3. Durable card/sidecar fields including workstation_last_error.
4. `_incoming` presence for the target artifact.
5. Workstation runtime/registry references to the target artifact.
6. GET-only `127.0.0.1:47832` health/job probes.
7. Workstation job intake / manifest gate / scheduler source anchors.

The Ray emits a `FAILURE_BOUNDARY` classification but always treats a discovered application failure as a successful observation.

Safety:
- Production source is READ ONLY.
- HTTP is GET only.
- No Browser DOM scraping.
- No Workstation mutation.
- No Apply/Verify/rollback endpoint calls.
- Human Gate unchanged.
