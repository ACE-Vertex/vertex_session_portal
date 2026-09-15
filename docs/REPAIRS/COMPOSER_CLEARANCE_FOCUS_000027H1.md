# VERTEX SESSION PORTAL — COMPOSER CLEARANCE + FOCUS 000027H1

## Repair scope
Verification-contract repair only. No Session Portal UI, renderer behavior, provider, SQLite, VCR/VCA, widths, or process-launch code is modified.

## Failure observed
`000027` passed every functional/static contract before the build-output print step, then the verifier itself raised `UnicodeEncodeError` because Vite emitted Unicode `✓` while Python/Vertex Works stdout was CP932.

## Repair
- Keep build subprocess decoding as UTF-8.
- Convert captured stdout/stderr to the active console encoding with replacement only for characters that cannot be represented.
- Preserve the build return code as the verification authority.
- Add an H1 PASS marker.

## Expected result
- Existing 000027 contracts remain PASS.
- `npm run build` output can be reported without CP932 crashes.
- `BUILD=PASS` when the project build succeeds.
- `VERTEX_SESSION_PORTAL_COMPOSER_CLEARANCE_FOCUS_000027H1=PASS`.
