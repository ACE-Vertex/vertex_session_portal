# VERTEX Session Portal — Dispatch Bay Publish Contract Repair 000050H2

## Purpose
000050H1 successfully restored the intended VRA flow and passed all live source/static checks, but canonical publication was blocked by the older 000047 publisher contract.

The obsolete publisher required `vra-download-destination-policy.ts` to contain `item.setSavePath(target)`. That requirement belongs to the retired direct-download design and conflicts with the current invariant.

## Canonical invariant

`ChatGPT VRA download -> Portal private staging -> Dispatch Bay card -> Human EXPORT to configured folder OR Human SEND TO WORKS`

- `VraDispatchService` is the only live owner of `will-download` and `DownloadItem.setSavePath()`.
- Browser downloads always save into Portal staging first.
- The configured VRA path is a Human EXPORT destination only.
- Export is non-destructive: the Dispatch Bay card remains after export.
- SEND TO WORKS is a separate Human action.
- No visible PRIMARY ENTRY UI is reintroduced.
- Existing external canonical launcher remains unchanged.

## Repair
- Retire `DISPATCH_WILL_DOWNLOAD_POLICY` marker from publisher 000047.
- Publish against three current markers: passive policy, staging capture, Human export.
- Add staging/export/capture-owner/flow fields to latest build metadata.
- Upgrade latest-build verifier to assert the new manifest and live-source invariants.
- Run the complete 000050H1 verification after migration.
