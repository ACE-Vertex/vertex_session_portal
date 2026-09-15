# VERA 600 DRAG + SEARCH RETIRE 000037H1

## Cause

000037 was authored against the 000036 VCA Memory Inbox + Session Clock Bridge source line. The Works ledger shows 000036 was inspected but was not staged/applied before 000037. As a result, the merged `VeraBrowserSession.ts` called `window.vertexPortal.updateVeraSessionThread(...)` while the installed `VertexPortalApi` contract/preload still reflected the older 000035 line.

TypeScript therefore failed with:

`Property 'updateVeraSessionThread' does not exist on type 'VertexPortalApi'.`

## Repair

This H1 restores the missing 000036 prerequisite surface without reverting the already-applied 000037 layout work.

It installs the 000036 VCA Inbox / Vera thread bridge contract, DB, IPC, preload, curator relay, Explorer UI, documentation and verifier while deliberately leaving the 000037 merged Vera browser file in place.

The intended combined state is:

- 000036 VCA Memory Inbox + Session Clock Bridge present.
- 000037 Vera lane canonical 600 px / drag resize / width persistence present.
- Search Vera window retired from MainFrame.
- Browser thread metadata reporting compiles against the installed API contract.
- Project Explorer Tree remains reserved for dedicated 000031 work.

## Verification

The H1 verifier checks the missing bridge contract/runtime path plus the 000037 width/search-retirement contracts and then runs the full project build once.
