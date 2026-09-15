# Session Portal Lane Truth + Evidence FIFO Repair 000096V5H2

## Why H1 failed

H1 did not reach TypeScript typecheck.

Its verifier searched the entire service for:

`basename(card.evidenceCacheName)`

and treated any occurrence as the old nullable bug.

That was a verifier false positive. The dangerous occurrence in
`cardForRenderer()` had already been replaced by explicit local narrowing.
A different method, `evidenceDeliveryOrderKey()`, legitimately retains
`basename(card.evidenceCacheName)` because it has an inline:

`if (!card.evidenceCacheName) return`

guard immediately before the call.

## H2

Production source is byte-for-byte the H1 design.

Only the verifier is corrected to inspect each owner method independently:

- `cardForRenderer()` must use the narrowed local string.
- `evidenceDeliveryOrderKey()` must prove its inline null guard.

The verifier then runs the real project:

- `npm run typecheck`
- `npm run build`

Functional design remains:

- activeJobs=0 => active lane cells all off
- terminal/Human-wait durable lane states do not illuminate ACTIVE cells
- Evidence visible only in RETURN_QUEUED
- one Evidence FIFO head per origin_session
- RETURNED Evidence cannot be re-exposed
- next queued Evidence advances after ACK
- Human Gate / exact origin / Observability / 000093 repairs preserved
