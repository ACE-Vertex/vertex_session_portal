# VRA WORKS DISPATCH LANE 000038H1

Repair for `vertex-session-portal-vra-works-dispatch-lane-000038`.

## Cause

`VraDispatchLane` extends `HTMLElement`. The component declared a private method named `remove(cardId)`, which collided with the native `HTMLElement.remove(): void` method and made the custom element type incompatible with `HTMLElement` / `CustomElementConstructor`.

## Repair

- Rename the card action method from `remove(cardId)` to `removeCard(cardId)`.
- Update the REMOVE button handler to call `removeCard(cardId)`.
- Preserve VRA download capture, SHA-256 guard, Works receiving copy-only behavior, Human Apply boundary, Search Vera retirement, and Project Tree reservation.
