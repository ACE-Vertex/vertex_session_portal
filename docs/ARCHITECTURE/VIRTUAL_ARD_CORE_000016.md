# Virtual ARD Core 000016

> 三人寄れば文殊の知恵 — by 自作自演

This stage turns the Session Portal's three Main Vera panes into a real
**mission-projected Virtual ARD substrate** without fixing permanent identities
onto the sessions.

## What is added

Workstation SQLite gains four local tables:

- `ard_mission`
- `ard_projection`
- `session_message`
- `ard_handoff`

The three Main Vera sessions remain generic. For each mission, roles are projected:

- Architect
- Developer
- Reviewer

A later mission may project those roles onto different Vera sessions.

## Typed self-play flow

`Vera 01 / Architect`
→ PLAN handoff
→ `Vera 02 / Developer`
→ IMPLEMENTATION handoff
→ `Vera 03 / Reviewer`

Each session has an independent message ledger. The handoff is explicit and typed;
one Vera does not silently mutate another Vera's context.

Search Vera remains outside the ARD role triangle as the retrieval / archive helper.

## What 000016 does NOT claim

This stage does not yet connect a real LLM provider. The probe uses deterministic
diagnostic messages to verify the storage, isolation, UI projection and handoff
mechanics.

The next provider stage can connect each Vera session to an actual model while
preserving this separation.

## Safety / architecture

- Roles are mission-projected, not hard-coded into Vera identities.
- Self-handoffs are rejected.
- Handoffs are append-only records.
- Workstation persistence is SQLite-local.
- VCR/VCA remain external canonical/archive systems, not duplicated into Portal DB.
