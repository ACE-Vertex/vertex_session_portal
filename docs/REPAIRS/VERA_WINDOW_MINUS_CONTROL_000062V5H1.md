# VERA Window Minus Control 000062V5H1

H1 repairs the verifier false-negative from 000062V5.

Root cause:
- 000062V5 VERIFY depended on the prose substring `exact-origin Evidence sink`.
- The current MainFrame contains the same meaning split across a line break, so the feature was incorrectly marked FAILED.
- This was a verifier defect, not evidence of a functional MainFrame failure.

H1:
- Reapplies the intended MainFrame idempotently.
- Keeps `− VERA` presentation-only.
- Minimum 3 visible Vera windows.
- Hides the right-most visible Vera first.
- Keeps the canonical VeraBrowserSession mounted.
- Preserves `vera-01..vera-05`, browser state, durable hidden state, routing identity and exact-origin return.
- Replaces prose-comment matching with semantic source checks.
- Runs typecheck and production build.
- Workstation production mutation = zero.
