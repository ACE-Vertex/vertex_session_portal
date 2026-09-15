# E-STOP Safety UI 000057V1H1

Narrow compatibility repair over `vertex-session-portal-estop-safety-ui-000057V1`.

The 000057V1 physical build and TypeScript typecheck passed. Its only failure was the legacy Final Wiring B static verifier's `D_OFFLINE_APPROVAL_PRESERVED` source-shape check. Safety integration had introduced an additional retryable `SAFETY_STATE_REJECTED` branch around the same semantics.

H1 preserves Safety behavior while restoring the previously verified Final Wiring B expression shape for ordinary HTTP failures:

- `SAFETY_STATE_REJECTED` -> `PENDING` (retryable Safety hold)
- HTTP 400/403/409 non-Safety failures -> `BLOCKED`
- transport/offline/response loss -> `PENDING`
- approved VRA remains durable and is not deleted/revoked

No Workstation production files are changed. No UI, routing, Evidence, ACK, Prompt Relay, display title, lane pulse, Human Gate, or DOM behavior is changed.

VERIFY calls the complete parent 000057V1 verifier, which itself reruns Workstation Safety Ray and Final Wiring B H2 regression, including typecheck/build.
