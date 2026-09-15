# Search Vera Retrieval Core 000018

000017 proved three real local-model Vera sessions can execute the Virtual ARD
Architect → Developer → Reviewer self-play with isolated contexts and typed handoffs.

000018 makes the fourth seat, Search Vera, a real information desk.

## Runtime / dependency rule

No search library, vector database, embedding runtime or new npm dependency is added.

Search Vera uses:

- Node built-in filesystem APIs,
- a bounded read-only local text retriever,
- the existing Workstation SQLite,
- the already-mounted Ollama provider.

This follows the same rule:

**Unitize behavior, consolidate infrastructure.**

## Initial live adapters

- PROJECT — LIVE
- EVIDENCE — LIVE

The retriever is project-root confined and excludes dependency/build directories such as
`node_modules`, `.git`, `out`, `dist` and backup areas.

## Explicitly not faked

- VCR — EXTERNAL
- VCA — EXTERNAL

Those systems remain separate. This stage does not pretend local file retrieval is VCR/VCA
access. Read-only adapters for those backing systems can be mounted later.

## Search Evidence

Each Search Vera query stores the latest retrieval hit set in Workstation SQLite:

- source
- relative path
- line range
- snippet
- score

The UI shows both the real local-model answer and the concrete retrieval Evidence.

## Probe

The probe searches for `三人寄れば文殊の知恵`.

It must physically retrieve:

`docs/ARCHITECTURE/VIRTUAL_ARD_CORE_000016.md`

and show the source hit after renderer reload, proving retrieval persistence and Search Vera UI.
