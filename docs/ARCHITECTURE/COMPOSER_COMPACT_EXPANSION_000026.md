# VERTEX SESSION PORTAL — Composer Compact Expansion 000026

## Scope
This patch changes only the Vera 01 / Vera 02 / Vera 03 composer behavior.
It does not alter pane topology, pane width, priority sizing, Search Vera, Explorer, provider settings, SQLite, VCR or VCA.

## Contract
- Compact/default composer starts at the same visual class as Search Vera: 52px shell / 38px textarea.
- Short input stays compact.
- After the textarea content height exceeds 150px, the composer enters expanded mode.
- Expanded mode has a 270px composer minimum and a 238px textarea minimum.
- Expanded content may grow to 900px composer / 850px textarea maximum.
- Deleting content below the trigger returns the composer to compact mode.
- Sending a message resets the composer to compact mode.

## Visual invariant
The existing three Vera panes and Search Vera layout must not move or change width in this patch.
