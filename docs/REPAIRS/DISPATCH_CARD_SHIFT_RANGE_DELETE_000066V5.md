# Dispatch Card Shift Range Multi Delete 000066V5

## Human UX

- Normal card-body click selects exactly one card and establishes the range anchor.
- Shift + click another visible card selects the entire contiguous visible range between anchor and target.
- Selected cards receive a thin Vertex Blue selection treatment.
- Footer shows the selected-card count.
- The × button on a selected multi-card range displays the selected count and removes the whole range.

## Delete confirmation

The previous native `window.confirm()` is retired.

A Session Portal themed Human Gate dialog now performs delete confirmation:
- single: `発注カードを削除しますか？`
- multiple: `N枚のカードを削除しますか？`
- ESC and backdrop click cancel.
- one confirmation covers the whole selected range.

## Safety contract

Batch delete reuses the existing `window.vertexPortal.removeVraCard(cardId)` backend route sequentially.
It only removes Dispatch Bay presentation/card records.

It does NOT:
- cancel a Workstation job;
- stop active execution;
- rollback target files;
- mutate Workstation production state.

Existing Human Dispatch, EXPORT, exact-origin Evidence Return, ACK, and Empty Bay behavior remain.
