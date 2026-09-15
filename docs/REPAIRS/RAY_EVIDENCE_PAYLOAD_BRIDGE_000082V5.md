# Ray Evidence Payload Bridge 000082V5

## What 000081 exposed

Ray V4 successfully observed the live machine and Workstation produced a VERIFIED
Evidence file, but the exact-origin return message contained only the immutable
Evidence envelope and `evidence_path`.

That means Vera receives proof that Ray looked, but not yet what Ray actually saw.

This is an observation transport gap, not a Ray execution failure.

## Repair

Session Portal now enriches the exact-origin return payload locally by reading the
Workstation verification Evidence file referenced by `evidence_path`.

Safety boundary:

- canonical `realpath`
- file must remain below `vertex_workstation/runtime/lanes`
- relative/path escape fails closed
- JSON only
- regular file only
- maximum 256 KiB
- READ ONLY
- no Workstation contract change
- no Workstation production source change
- original immutable Evidence envelope remains unchanged
- bounded body is appended after the envelope
- Human Gate remains mandatory

This turns the Workstation Evidence path from a pointer into a usable Vera observation
channel while preserving the existing evidence identity and return contract.
