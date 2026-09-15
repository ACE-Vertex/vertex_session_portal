# VERTEX Session Portal — VCA Curator Assistant 000035

## Purpose

000035 turns the VCA weighting foundation from 000034 into an operational memory-curation path. The curator is not Vera and never replaces Vera. It is one dedicated AI Assistant selected from the five Vera lanes and used only to evaluate VCA memory gravity.

## Canonical rules

- Five primary lanes remain Vera browser sessions.
- The VCA Curator uses one explicitly configured lane Assistant.
- No configured Assistant means no curator run. There is no fallback to the legacy default provider and no model is allowed to impersonate Vera.
- Human and Vera memories are peer inputs. The curator is explicitly instructed not to privilege either speaker by identity.
- Age alone never lowers memory gravity.
- Curator writes are append-only `vca_weight_revision` rows. Existing deterministic or previous AI judgments remain in history.
- The default curator route is `lane-4`, but the user can select any lane 1–5.
- Recommended starting size is around 12B, but no parameter count is hard-coded.

## Runtime flow

1. A VCA event is stored and receives the deterministic seed weight from 000034.
2. The event remains `PENDING` while its latest curator is `DETERMINISTIC_SEED` / `UNWEIGHTED`.
3. If AUTO CURATE is enabled, a new memory schedules the curator.
4. The curator first verifies that the selected Vera lane really has a dedicated Assistant override.
5. It checks that Assistant provider/model is ready.
6. A bounded batch is sent to that Assistant with canonical VCR and high-gravity VCA references.
7. The Assistant returns strict JSON dimensions: Human, Vera, Mutual, Purpose, Implementation, Recurrence, Novelty and Confidence.
8. Vertex validates/clamps the dimensions and appends a new weight revision.
9. `RUN PENDING` processes deterministic-seed memories. `RE-EVALUATE` lets the user deliberately revisit already weighted memories later.

## UI

The VCA tab gains a `VCA MEMORY CURATOR` panel with:

- Assistant lane selector (1–5)
- Batch size
- AUTO CURATE NEW VCA MEMORY
- Provider/model/readiness/pending status
- SAVE CURATOR
- RUN PENDING
- RE-EVALUATE

## Important boundary

000035 does not scrape the ChatGPT browser DOM and therefore does not yet make every ChatGPT browser conversation automatically appear in VCA. It curates memory events that have already entered the Vertex-owned VCA layer.

Project Explorer Tree remains reserved for the dedicated tree rebuild and is not redesigned here.
