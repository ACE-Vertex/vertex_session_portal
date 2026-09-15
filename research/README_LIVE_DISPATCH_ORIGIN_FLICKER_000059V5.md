# LIVE DISPATCH ORIGIN + FLICKER RAY 000059V5

Purpose: inspect current Session Portal production source read-only after a live VERA05 dispatch failure.

Observed live symptoms:
- Card visibly shows VERA05 / vera-05.
- Human Approval is APPROVED.
- Dispatch fails with human message that origin registration is incomplete.
- After Human dispatch, the card visibly flickers.

This probe performs no production source mutation.
It inspects current routing gate, display fallback/combination behavior, polling/reconcile logic,
and card DOM identity/rebuild signals.

Expected next step:
Use the returned Works Evidence to author a narrowly anchored repair VRA.
