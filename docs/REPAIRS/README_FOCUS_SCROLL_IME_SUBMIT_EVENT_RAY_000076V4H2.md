# Focus / Scroll / IME / Submit Event Ray 000076V4H2

New observed symptom:
- focus may be stolen while the Human is typing in another Vera lane,
- Japanese IME conversion may be interrupted,
- an Enter intended to confirm conversion may be interpreted as submit,
- the message may be sent unexpectedly.

This is not yet proven. H2 adds passive event correlation to prove or reject it.

New passive events:
- compositionstart / compositionupdate / compositionend
- beforeinput / input
- sanitized keydown classification
- submit
- button click metadata

Derived candidates:
- ime_enter_during_composition
- ime_composition_focus_loss_candidate
- ime_submit_collision_candidate

Privacy correction from H1:
- actual key characters are NOT logged,
- `event.code` is NOT logged,
- IME composition text is NOT logged,
- input values and page text are NOT logged,
- only key class, IME state, input type, metadata and lengths are logged.

H2 does not alter send handlers or IME behavior. It is observation-only.
A behavioral repair should be applied only after evidence identifies the exact
submit/focus path. A likely future guard, if confirmed at the actual send
handler, is to reject submit while `event.isComposing` or IME keyCode 229 is
active, but H2 intentionally does not assume that contract yet.
