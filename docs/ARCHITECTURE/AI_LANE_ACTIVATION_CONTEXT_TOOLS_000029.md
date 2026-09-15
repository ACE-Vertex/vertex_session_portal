# AI Lane Activation + Composer Context Tools 000029

This patch closes two UI gaps without touching the dedicated Project Tree or the upcoming VCR card/modal work.

## AI lane activation

- Five configurable AI lanes are now mapped one-to-one to `vera-01` through `vera-05`.
- Existing installations are migrated with `vera-04` and `vera-05` inserted as inactive MAIN sessions.
- Search Vera is kept separate at position 6 and uses Vera Default rather than stealing lane 5.
- AI Settings shows `ACTIVE LLM LANES n/5` and an `⊕ ADD LANE` control until five MAIN lanes are active.
- Each click activates the next inactive MAIN lane while preserving its independent lane configuration and Vera fallback semantics.

## Composer utility buttons

The two previously ambiguous buttons now have explicit behavior and tooltips.

- `＋` — **Attach local text context**. Opens a native file picker. Text/code/log files up to 256 KiB are attached to the next request only. Up to five attachments are kept in the composer as removable chips.
- `◎` — **Context Target**. Chooses whether local retrieval is SESSION ONLY, PROJECT, EVIDENCE, or PROJECT + EVIDENCE. The selected scope is visible as a chip.

Attached text is supplied to the LLM as user-selected context. It is never claimed to have been executed or modified. Binary files are rejected by this text-context path.

## Boundary

- VCR card creation/modal editing is not implemented here; it remains dedicated to 000030.
- Project Explorer Tree reconstruction is not modified here; it remains dedicated to 000031.
- Existing composer compact/expanded behavior from 000026/000027 is preserved.
