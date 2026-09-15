# Vertex System Policy Layer — Phase 1

Status: Foundation

## Responsibility boundary

- System Policy Registry: rules authority
- Vertex VRA Registry: responsibility / identity / lifecycle ledger
- Vertex Workstation: execution authority
- VRA: transport ticket
- Evidence: proof
- VERA: reasoning / proposal
- Human: final authority

## Active baseline

Policy:

`vertex.vra.issue/1.0.0`

Resolved canonical source:

`G:/Vertex_Project/Development/vertex_workstation/runtime/lanes/lane-06/temp/stage-vertex-vra-canonical-manifest-store-000151V5-1789223261693-72/apply-prepared/VRA_CANONICAL_MANIFEST_vra-1_000150V5.json`

Existing Contract Catalog identity:

`vertex.vra.issue/1`

## Phase 1 scope

Phase 1 is read-only. It intentionally does not provide:

- Policy Resolver IPC
- Deterministic VRA Validator
- Deterministic VRA Builder
- Policy Change Proposal flow
- Policy Registrar
- Policy activation writer
- migration engine
- System Change Gate

The System Policy Registry remains logically separate from the VRA Registry.
