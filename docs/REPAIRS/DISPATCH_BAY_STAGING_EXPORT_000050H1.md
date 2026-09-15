# Vertex Session Portal — Dispatch Bay Staging + Human Export Repair 000050H1

000050 reached a successful npm build, but its Python runner printed Vite's Unicode check mark through a CP932 Windows console. That raised `UnicodeEncodeError` before commit, so the transaction restored the dynamic patches. The follow-on verifier then inspected a hybrid/pre-000050 tree.

The original verifier also scanned `ROOT.rglob('*.ts')`, so historical TypeScript copies under `EVIDENCE` were incorrectly counted as active `will-download` owners.

Canonical flow is fixed as:

`ChatGPT browser download -> Portal private staging -> Dispatch Bay card -> Human decision`

Human then chooses either `EXPORT` to copy from staging into the configured VRA export folder, or `SEND TO WORKS` to copy separately into Works Receiving Bay. No destination setting may bypass Dispatch Bay. `VraDispatchService` is the sole live owner of VRA `will-download` and `item.setSavePath()`.

H1 hardening:
- CP932-safe subprocess output in both apply and verify scripts.
- Owner scan is limited to `src/**/*.ts`; Evidence and backups are excluded.
- Comment text is removed before ownership token scanning.
- PRIMARY ENTRY UI is removed; the external canonical launcher remains unchanged.
- The exact user-supplied Vertex SVG is installed at `src/renderer/src/assets/vertex-project-mark.svg` and used in the top-left brand block.
- Header spacing is rebalanced around the actual logo and VERA window controls.
- 000050 staging/export/Works separation source files are re-applied deterministically.

Manual acceptance after verification: download one `.vra` from any VERA lane; confirm a Dispatch Bay card appears first; select a VRA export folder; press EXPORT; confirm the file is copied while the card remains; optionally SEND TO WORKS.
