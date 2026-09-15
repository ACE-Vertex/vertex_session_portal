# Vertex Session Portal — Dispatch Bay Staging + Human Export Repair 000050

Canonical VRA flow is fixed as:

`ChatGPT browser download -> Portal-owned staging -> Dispatch Bay card -> Human choice`

Human then chooses `EXPORT` to copy the staged VRA to the folder shown in `VRA Save Path`, or `SEND TO WORKS` to copy it to Works Receiving Bay. Export never bypasses Dispatch Bay and never automatically applies anything.

000046H2 / 000048 introduced a second `will-download` owner that could overwrite the staging `setSavePath()`. 000050 makes `VraDispatchService` the only TypeScript owner of both `will-download` and VRA `item.setSavePath()`; the destination policy is passive. The verifier scans the whole TypeScript tree and fails if another owner appears.

The accidental `PRIMARY ENTRY` UI button from 000049 is completely removed. The existing single launcher remains an internal packaging rule only.

The currently selected Vertex V mark is preserved and the top-left balance is tightened. No synthetic replacement logo is introduced in this repair.

Acceptance: download a VRA from any VERA lane; confirm a Dispatch Bay card appears first; choose a VRA Save Path; press EXPORT; confirm the file is copied there and the card remains; optionally SEND TO WORKS and confirm that separate copy path.
