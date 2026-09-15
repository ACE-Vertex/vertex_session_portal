# Dispatch Card Visible Remove 000064V5

## Human request
Make Dispatch Bay order cards directly removable.

## Change
The existing remove path is preserved and moved from the hidden DETAILS section to a visible `×` control in the card header.

- Every Dispatch Card exposes a small visible remove control next to the factory-state badge.
- Clicking it still requires Human confirmation.
- Removal only removes the Portal Dispatch Bay card.
- It does not cancel, stop, rollback, or delete the Workstation Job/execution.
- The existing `window.vertexPortal.removeVraCard(cardId)` route is reused.
- No new backend execution shortcut is introduced.
- The hidden duplicate REMOVE CARD action is removed from DETAILS to avoid two delete controls.

## Preserved
- 工場へ発注 / Human Gate
- EXPORT to Old Vertex Works
- immutable origin routing
- Evidence return / ACK
- Workstation lane allocation authority
- Safety / E-STOP integration
- Path hidden
- no direct HTTP APPLY / VERIFY / ROLLBACK
- Workstation production mutation = zero
