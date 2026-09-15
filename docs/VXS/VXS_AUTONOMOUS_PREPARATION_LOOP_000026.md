# VXS Autonomous Preparation Loop 000026

Goal:
Vera uses VXS to autonomously prepare development and humans see only the
existing approval point.

Adds:
- `vxs prepare`
- `vxs prepare --plan`
- `vxs prepare --json`
- alias: `vxs prep`

Default `vxs prepare` pipeline:

1. run VXS registry/authority self-test in-process
2. load the autonomy policy
3. build the bounded agent context snapshot
4. assess readiness and recommendations
5. build a changed-scope verification plan (quick fallback outside Git)
6. execute only the policy-approved verification pipeline
7. emit `VXS_APPROVAL_POINT/1` only if safe verification completes successfully

Fail-closed behavior:
- self-test failure -> stop
- policy disallows safe preparation -> stop
- verification-plan failure -> stop
- verification failure -> shell exits before approval packet
- changed work with no safe verification pipeline -> stop

Authority invariants:
- arbitrary `vxs run` is never auto-executed by prepare
- VRA is never auto-dispatched by prepare
- Human Gate is never bypassed
- Workstation remains final Lane Allocation Authority
- Observation remains additive/non-authoritative
- no new ACK path, Return Queue, Evidence Router, Registry lifecycle, or transport
- no production mutation is added to VERIFY

Schemas:
- `vxs-preparation-plan/1`
- `vxs-autonomous-preparation/1`
- `vxs-approval-point/1`
