# Five Vera Window Scaler 000043H1 — Repair

## Root cause

The 000043 apply script called:

`Path.write_text(text, encoding="utf-8", newline="\n")`

The Python runtime used by Vertex Works does not accept the `newline` keyword on `Path.write_text`, so the first attempted MainFrame write failed before the source patch could be committed. The rollback path called the same unsupported API and therefore failed as well.

## Repair

- Replace only `scripts/apply_five_vera_window_scaler_000043.py`.
- Use UTF-8 `Path.write_bytes()` after LF normalization.
- Keep the transactional rollback behavior.
- Make the `MAIN_VERA_IDS` patch slightly more tolerant of source formatting.
- Preserve the existing 000043 component, CSS, and verifier.
- Re-run the repaired apply script and the original 000043 verifier.
