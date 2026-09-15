# WORKSTATION DISPATCH CARD 000052V1H3

Verifier-only repair for 000052V1H2.

## Root cause
The H2 owner scanner used raw substring matching across every TypeScript file.
`vra-download-destination-policy.ts` intentionally contains negative documentation stating that the module MUST NOT register `will-download` and MUST NOT call `DownloadItem.setSavePath()`. Those documentation tokens were incorrectly counted as executable ownership.

## Repair
- No production capture/render/dispatch logic is changed.
- Owner detection now masks TypeScript comments before looking for `session.on/once/addListener('will-download', ...)`.
- Save-path ownership masks both comments and string bodies before looking for executable `.setSavePath(...)` calls.
- The destination policy is explicitly verified as a non-owner even if its negative documentation still contains the raw tokens.
- Existing H2 markers, immutable origin, STAGING_FIRST, Human Approval, atomic `_incoming` publish, vra-routing/1 vocabulary, Path suppression, VERA1-5 layout, no DOM scrape and no auto apply remain mandatory.
- Verification remains read-only and uses `npm run typecheck` with before/after source hashes.

## Scope
Session Portal only. `vertex_workstation` is not modified.
