# VERTEX SESSION PORTAL — COMPOSER CLEARANCE + FOCUS 000027

## Scope
Single-scope repair for Vera 01 / 02 / 03 chat sessions only.

## Problems repaired
1. With no `roleBar`, CSS grid auto-placement moved `.body` and `.composer` one row upward. The composer therefore occupied the flexible body row instead of the dedicated final row and could visually cover the last chat message.
2. Sending with Enter rebuilt the Shadow DOM, so keyboard focus left the composer.
3. A full re-render during history reload could also discard a draft typed while the model was working.

## Repair
- Explicit grid placement: chrome=1, header=2, optional roleBar=3, body=4, composer=5.
- Preserve the 000026 compact/expanded sizing contract unchanged.
- Keep a local draft buffer across renders.
- Avoid the intermediate history re-render during a send turn.
- Restore textarea focus after submit/state re-render and after provider completion.
- Keep the textarea usable while the model is thinking; send remains guarded while busy.

## Deliberately NOT modified
- MainFrame widths / 600px sizing
- Search Vera
- Explorer / AI settings
- Provider selection / credentials
- SQLite / VCR / VCA
- Local LLM process launching

Expected marker: `VERTEX_SESSION_PORTAL_COMPOSER_CLEARANCE_FOCUS_000027=PASS`
