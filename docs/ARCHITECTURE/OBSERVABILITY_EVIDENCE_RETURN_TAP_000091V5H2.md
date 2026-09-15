# Hidden Observability Core — Evidence Return Tap 000091V5H2

H2 wires the VERIFIED H1R5 Observability Core into the existing Session Portal Workstation Evidence pickup path.

## Runtime order

Workstation GET Evidence -> existing immutable identity/origin/HUMAN_APPLY gates -> hidden Observability Tap -> existing Evidence cache -> existing exact-origin delivery -> existing durable DELIVERED receipt -> existing ACK -> RETURNED.

The Tap is explicitly non-authoritative. It cannot allocate lanes, Apply, Verify, ACK, reroute Evidence, change Human approval, or choose the Vera destination.

## Hidden cache

Analysis is persisted below the Portal-owned staging root at `observability/evidence/<sha256(evidence_id)>.json`. This is not renderer state and no UI is added. Duplicate pickup of the same immutable Evidence identity reuses the same analysis record.

## Safety

- Ray remains READ ONLY and is scoped to `vertex_workstation/runtime/lanes` for Evidence stdout/stderr hydration.
- Up to 16 command logs, 64 KiB tail each, as defined by H1R5.
- Common API key/token/password patterns are redacted before hydrated logs enter Judge/Black Box/persistent analysis.
- Tap degradation never blocks Evidence return.
- Workstation production source is untouched.
- Human Gate, exact origin, Evidence identity, RETURN_QUEUED/RETURNED ACK contract and no-auto-rerun remain authoritative elsewhere.
- No renderer component, DOM scrape, BrowserWindow or `executeJavaScript` is introduced.

## Source baseline

`src/main/vra/vra-dispatch-service.ts` is based on the exact VERIFIED 000082V5 content restored by VERIFIED recovery artifact 000089V5. H1R5 did not modify this service file.
