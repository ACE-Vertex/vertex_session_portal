# Auto Task Send Commit Repair 000052

## Observed live symptom

The VERA-to-VERA AUTO dispatch wrote the complete task body into each target ChatGPT composer, but the message remained unsent.

That observation proves the source routing, target webview selection and composer-write stages were already functioning.

## Root cause

The 000051H1 injector dispatched the input event and immediately searched for an enabled send button in the same synchronous JavaScript turn.

ChatGPT updates its composer/send-control state asynchronously. The body can therefore appear in the composer and the blue send control can become enabled shortly afterward, after the old injector has already returned `TARGET_SEND_BUTTON_NOT_FOUND`.

## Repair

000052 converts the target injection to an async transaction:

1. write task body,
2. dispatch input/change,
3. wait for the UI state transition,
4. retry the send-control lookup for approximately three seconds,
5. prefer explicit ChatGPT send selectors,
6. allow only a form-scoped enabled `button[type=submit]` as fallback,
7. click send,
8. return `SEND_COMMIT_CLICKED`,
9. only then may the outer dispatch layer persist its dispatch_id+target receipt.

No arbitrary enabled button is selected, so voice and attachment controls are not used as fallback.

The Vertex HUD/AUTO behavior from 000051H1 is preserved.
