# VERTEX SESSION PORTAL — VCA MEMORY GRAVITY + MEMORY CLOCK FOUNDATION 000034

## Canonical intent

VCA is not a duplicate of ChatGPT Memory. VCA is Vertex-owned long-term experience memory.
Its job is to retain conversation-derived experience, preserve the weight of important ideas, and make forgotten but consequential memories easy to pull back into the active Vera sessions.

Human and Vera are peer sources. Neither side receives an inherent priority multiplier.
A memory may become heavy because the Human strongly adopted it, because Vera introduced a consequential connection, because both reinforced it, because it remains tied to the project purpose, because it affected implementation, or because later work repeatedly refers back to it.

Age alone does not decay Memory Gravity.

## 000034 scope

This patch introduces the storage and API foundation for:

- append-only VCA memory events with a monotonic `memory_revision`;
- append-only VCA weight revisions;
- Human / Vera / Mutual / Purpose / Implementation / Recurrence / Novelty / Confidence dimensions;
- equal Human and Vera signal coefficients in the deterministic gravity formula;
- `memory_gravity` ordered VCA retrieval;
- five Vera logical memory clocks;
- a Canonical Memory Frontier;
- compensation packet generation for lagging Vera sessions;
- explicit compensation acknowledgement;
- VCA Explorer visualization for frontier, lane lag and per-card gravity.

The deterministic seed is intentionally only a first pass. A local Assistant such as a 12B VCA Curator can later append a superior weight revision through `appendVcaWeightRevision` without rewriting history.

## Memory clock model

Each Vera lane has:

- `observed_revision`: newest Vertex memory revision that originated from / was directly observed by that Vera lane;
- `compensated_revision`: newest revision Vertex has explicitly compensated into that lane;
- `effective_revision = max(observed_revision, compensated_revision)`;
- `lag = canonical_revision - effective_revision`.

The Canonical Memory Frontier is the highest VCA `memory_revision` known to Vertex.

000034 creates the clock, delta query and acknowledgement primitives only. It does **not** silently inject compensation into ChatGPT web sessions yet.

## Browser capture boundary

000033 intentionally did not scrape ChatGPT DOM output. 000034 keeps that boundary.
The new `appendVcaMemoryEvent` API is the canonical ingestion point for future browser-session capture / user-approved bridge work. Therefore the memory engine is ready before the capture bridge is attached.

## Existing data migration

Existing `session_chat_message` rows are mirrored into `vca_memory_event` using their original message ids as stable source references. The legacy table is not deleted or rewritten.

## Project Tree isolation

The Project Explorer Tree remains reserved for its dedicated patch. 000034 does not rebuild or alter the Project tree implementation.
