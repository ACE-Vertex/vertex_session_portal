# VCR Card Browser + Modal Editor 000030

## Scope

This patch is intentionally limited to the VCR user interface inside the existing 365 px Vertex Explorer.

It does **not** redesign the Project Explorer Tree, AI Lane settings, session panes, chat composer, provider routing, SQLite schema, or VCA.

## VCR interaction

- VCR results render as cards.
- A persistent bottom `⊕ ADD VCR` card/button remains visible even when the result set is empty.
- Double-clicking a VCR card opens a viewport modal.
- Enter also opens a keyboard-focused VCR card.
- The modal opens with a short fade + scale animation and closes with a short fade.
- Click outside the modal, press Escape, use the subtle `×`, or use `CLOSE` to dismiss it.
- New cards receive a generated canonical key which can be edited before first save.
- Existing canonical keys are read-only in the editor to preserve revision lineage.
- TITLE / CATEGORY / STATUS / CONTENT can be reviewed and edited.
- Existing VCR writes use the already-installed `upsertVcrEntry` contract. The SQLite VCR remains append-only: editing creates the next revision instead of mutating an earlier revision.

## Canonical separation

`projectTree()` remains unchanged in this patch. Project Tree accuracy/rebuild is reserved for the dedicated 000031 patch.

Expected verification marker:

`VERTEX_SESSION_PORTAL_VCR_CARD_MODAL_000030=PASS`
