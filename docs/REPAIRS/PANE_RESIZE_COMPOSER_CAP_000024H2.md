# Pane Resize + Composer Cap 000024H2

000024H1 fixed the textarea height correctly. Evidence showed:

- composer before input: 66px
- composer after long input: 86px
- textarea: 72px

The remaining failure was the manual pane-width verifier.

## Root cause

The width contract itself was correct, but the host still animated:

```css
transition:
  flex-basis 240ms ...,
  min-width 240ms ...,
  width 240ms ...;
```

The probe intentionally measured 80ms after each width change. Therefore it was
observing an in-flight animation, not the final width:

- requested 850px -> observed 828px
- requested/clamped 600px -> observed 848px
- reset -> observed 848px

This also makes drag-resizing feel laggy because the pane trails the pointer.

## Repair

Remove transitions from layout geometry:

- `flex-basis`
- `min-width`
- `width`

Keep only visual effects such as box-shadow transitions.

Manual pane resizing is now immediate and deterministic. The original 000024 verifier
is re-run unchanged.
