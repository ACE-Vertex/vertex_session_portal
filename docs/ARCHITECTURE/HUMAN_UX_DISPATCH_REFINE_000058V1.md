# Vertex Session Portal — Human UX / Dispatch Refinement 000058V1

## Scope

Portal only:

`G:\Vertex_Project\Development\vertex_session_portal`

`vertex_workstation` is READ-ONLY reference. This VRA has no Workstation operation.

## READ-ONLY source findings

The latest VERIFIED Portal contracts already expose:

- canonical session state objects with `active`;
- `activateNextMainLane()`;
- preload bridge `workstation:activate-next-main-lane`;
- VRA source registration tied to each real `session-id`;
- immutable origin mapping for `vera-01 ... vera-05`;
- Workstation `workstationOnline` and Safety observation;
- Final Wiring B dispatch route through `window.vertexPortal.dispatchVraCard`;
- separate Human Export through `window.vertexPortal.exportVraCard`;
- Prompt Relay absolute target buttons 1–5;
- durable `display_title`;
- exact-origin Evidence return;
- Evidence ACK;
- 32-lane pulse.

No new session architecture is required.

There is no Human-facing deactivation API in the Portal API surface used by MainFrame. Therefore
window close is implemented as a presentation-only hide rather than inventing a destructive
session lifecycle call.

## + VERA

MainFrame now shows a clear `[ + VERA ]` control.

Behavior:

- start with the currently active visible canonical Vera windows;
- if a canonical active window was presentation-hidden, `+ VERA` restores that window first;
- otherwise `activateNextMainLane()` activates the next existing canonical MAIN lane;
- maximum is `vera-05`;
- `vera-06` is never generated;
- at five visible Vera windows the button disables.

The existing fixed/minimum Vera width is preserved. The implementation does not squeeze five
ChatGPT windows into one viewport.

## Window close

The red window dot is now a presentation hide control.

Hide:
- adds `presentation-hidden`;
- persists the presentation preference;
- does not delete/deactivate the canonical session;
- keeps the `vera-browser-session` element mounted;
- keeps exact-origin Evidence listener and routing identity alive.

`+ VERA` restores a hidden window before activating a new one.

## Dispatch Bay title

Removed:

`Dispatch Bay INTEGRATION · VERA05`

New fixed title:

`VRA / WORKSTATION LOGISTICS`
`DISPATCH BAY`

Origin Vera is shown only inside each VRA card.

## Compact Dispatch Card

Collapsed card is intentionally dense and horizontal:

- Origin Vera
- Project
- Status badge
- one-line Job Title
- Lane Policy
- Requested Lane
- Allocated Lane
- Human Approval
- primary `工場へ発注`
- `EXPORT`
- `REMOVE`
- `DETAILS`

Artifact ID, Origin Session/Window, full title, Job ID and Correlation ID are moved into the
`DETAILS` disclosure.

No local/transport path is rendered.

## New Workstation dispatch

Primary Human action is:

`工場へ発注`

The button does not create a new execution path. It still calls the existing:

`window.vertexPortal.dispatchVraCard(cardId)`

Therefore Final Wiring B remains the route:

Human Approval -> durable commit -> temporary copy -> SHA256 -> atomic `_incoming` publication
-> sidecar durable commit -> POST `/v1/jobs` -> Workstation registration.

An explicit Human confirmation dialog is required before dispatch.

System states such as DISPATCHED are shown as badges, never as a fake action button.

## Old Works EXPORT

`EXPORT` is preserved as the manual Human route for Old Vertex Works.

It calls only the existing Human Export API. It never invokes Workstation dispatch/registration.

Workstation OFFLINE does not disable EXPORT.

## Online / Offline

`工場へ発注` requires:

- `workstationOnline === true`
- Workstation Safety observation online
- Safety state `RUNNING`

OFFLINE / UNKNOWN / Safety hold disables new Workstation dispatch and displays the reason near
the card.

EXPORT remains available.

## Verification

000058V1 verifies:

- 3 -> 4 -> 5 presentation path from existing canonical session activation
- no VERA06
- presentation-only hide and re-show
- `vera-04 -> VERA04`, `vera-05 -> VERA05` immutable origin mapping
- fixed Dispatch Bay title
- compact card structure and detail disclosure
- no Human path rendering
- online/offline dispatch gating
- Human confirmation
- Final Wiring B dispatch API reuse
- Human Export separation
- status badge semantics
- Prompt Relay 1–5
- display_title durability
- exact-origin Evidence return + ACK
- Safety UI
- 32 Lane Pulse
- Project Tree API
- latest Safety/Final Wiring B regression verifiers
- TypeScript typecheck
- production build
- zero Workstation production mutation

## Expected merge classification

BLUE:
- MainFrame presentation controls
- compact Dispatch Card
- explicit dispatch/export separation

YELLOW only if a newer Portal source revision after 000057V1H1 has independently changed one of
the same four renderer files. Works backup/rollback remains authoritative.

RED:
- none expected from the current VERIFIED baseline.
