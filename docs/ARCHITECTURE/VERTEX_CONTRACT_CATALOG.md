# Vertex Contract Catalog v0.1

## Purpose

This is a deliberately small, shared, read-only contract catalog.

It solves one specific failure mode:

- VERA/LLM forgets the canonical VRA issuance format.
- VERA/LLM later misreads Workstation Evidence state semantics.

The system must not depend on LLM memory for either task.

## Active contracts

### `vertex.vra.issue/1`

Defines how a canonical `vra/1` work request is issued.

It includes:

- canonical schema/routing authority,
- fresh identity requirements,
- immutable origin requirements,
- payload/copy/SHA256 rules,
- verification path alignment,
- lane-policy boundary,
- TEST guidance,
- a canonical shape example.

### `vertex.evidence.read/1`

Defines how Workstation Evidence is interpreted.

The most important distinction is:

`evidence_return_state=RETURN_QUEUED` is a transport workflow fact, not a statement that the Evidence is invisible in the Vera chat.

Transport state and chat visibility are separate observations.

## Responsibility boundary

This catalog is not:

- the Workstation scheduler,
- the Job Registry,
- the Return Router,
- a mutable LLM knowledge base,
- RAG.

It is only a tiny system contract source.

## Current implementation phase

Phase 1 adds only:

- shared catalog,
- active contracts,
- deterministic resolver.

Later phases may bind the resolver to VRA issuance and Evidence injection automatically.
