# Correlation Binding + Human Incident Marker 000079V4B

This pass deliberately avoids direct mutation of the VRA dispatch write path.

## Correlation binding

The existing VRA dispatch service already durably stores:
- job_id
- correlation_id
- origin_vera / origin_session / origin_window
- requested_lane / lane_policy
- allocated_lane
- Human Approval / dispatch phase
- Workstation registration/job/evidence states

000079V4B adds a read-only durable-ledger observer under the VERA4-owned
Observability layer. It watches the existing `vra-dispatch/ledger.json` and
records transitions into the Observability Black Box with the card's existing
correlation_id.

Observed milestones include:
- capture/staged
- Human Approval durable commit
- atomic `_incoming` publication
- Workstation registration/job state
- Workstation lane allocation
- Evidence return / return-state transitions

This is an observational binding, not a write-path hook. Human Gate,
STAGING_FIRST, atomic publish, lane allocation authority, and Workstation code
are unchanged.

## Human MARK INCIDENT

The existing Event Ray observer adds a small host-Portal-only `MARK INCIDENT`
button when `vertex-vra-dispatch-lane` exists. It is not injected into Vera /
ChatGPT webcontents.

Click:
Event Ray `page:human_incident_marker`
→ Observability Core Event Ray bridge
→ automatic Incident Evidence Packer
→ flight recorder + Event Ray tail frozen under userData/observability/incidents.

No prompt text, page text, IME composition text, or input values are captured.

## Verification

VERIFY is read-only with respect to production source. It runs TypeScript
typecheck only. Session Portal restart is required after VERIFIED apply.
