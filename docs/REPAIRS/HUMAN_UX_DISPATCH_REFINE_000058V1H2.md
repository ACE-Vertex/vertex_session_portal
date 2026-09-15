# 000058V1H2 — Safety Rebase

000058V1H1's feature repairs were structurally green, but TypeScript/build failed because
`vra-dispatch-service.ts` was reconstructed from the older Final Wiring B service and therefore
overwrote the later VERIFIED 000057V1H1 Workstation Safety methods.

Observed compiler errors:

- `getWorkstationSafety` missing
- `performWorkstationSafetyAction` missing

This was a production-baseline collision, not a flicker/routing failure.

H2 rebases the service onto the VERIFIED 000057V1H1 Safety implementation first, then reapplies
only the immutable routing-manifest commit.

Therefore H2 contains BOTH:

Safety:
- durable Workstation safety observation
- GET safety
- Human safety actions
- POST then authoritative GET reverify
- safety registration hold/retry behavior
- fail-closed safety parsing

Routing:
- capture-time immutable origin
- route embedded into actual staged `manifest.json`
- origin conflict fail-closed
- atomic VRA rewrite
- SHA only after routing commit
- `allocated_lane` excluded from external routing

Renderer:
- H1 keyed card reconciliation
- polling preserved
- scroll/details/focus DOM identity preserved
- short Human error + technical error under DETAILS

Workstation production remains untouched.

H2 verification explicitly reruns 000057V1H1 Safety verification plus typecheck and production
build, so the exact H1 regression cannot pass unnoticed again.
