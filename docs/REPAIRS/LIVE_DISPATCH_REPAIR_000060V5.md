# VERTEX SESSION PORTAL — LIVE DISPATCH REPAIR 000060V5

## Scope
Hot-update-safe repair for the running Session Portal. No Workstation production file is modified.

## Repairs
1. Stops the 2.5-second `BLOCKED -> REGISTERING -> BLOCKED` registration retry loop. A 4xx/403/409 registration rejection remains durably fail-closed instead of repainting the card every poll.
2. Removes Human-visible internal contract badges from the Dispatch Bay while preserving STAGING_FIRST, immutable origin, Human Gate, atomic `_incoming`, and Workstation lane authority in production logic.
3. Makes successful EXPORT visually quiet. EXPORT failures remain visible.
4. Moves destructive REMOVE from the primary action row into DETAILS and requires Human confirmation. Removal is explicitly described as a Portal-card operation, not Workstation Job cancellation.
5. Replaces the large empty-state VRA glyph/explanation with a compact quiet state.
6. Preserves keyed card DOM identity, scroll, DETAILS expansion, Evidence routing/ACK, Safety UI, +VERA, Human Export, and Path-hidden contract.

## Important retest rule
A card that was already `BLOCKED` before this repair stays FAILED after hot update by design. It is no longer auto-retried. Remove that old card with the new confirmation flow, then capture a fresh smoke VRA for the new-factory E2E retest.

## VERIFY
VERIFY is read-only with respect to production source. It runs static contract checks, the existing Safety verifier, TypeScript typecheck, and production build.
