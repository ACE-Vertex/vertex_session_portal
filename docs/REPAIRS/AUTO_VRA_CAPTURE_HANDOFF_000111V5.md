# AUTO VRA Capture Handoff — 000111V5

## Root cause

`VraDispatchService` only creates Dispatch Bay cards from Electron
`will-download` events. A Vera generating a `.vra` attachment in its ChatGPT
answer does not itself trigger a download. Without a click:

VRA generated
→ no `will-download`
→ no immutable Capture
→ no STAGED card
→ 000109 AUTO execution scan sees zero cards.

## Repair

AUTO tasks now carry an explicit VRA artifact handoff contract.

When a Vera generates a VRA it emits a strict marker block:

`[VERTEX_VRA_ARTIFACT/1] ... [/VERTEX_VRA_ARTIFACT/1]`

Session Portal reads only those explicit marker blocks, validates:

- active Human AUTO authority;
- exact source session;
- delegated task context for child sessions;
- exact artifact id;
- basename-only `.vra` filename;
- task dispatch id where delegation is used;
- `auto_dispatch=true`.

It then clicks exactly one matching VRA link inside the same assistant message
using Electron user-gesture execution. That intentionally triggers the existing
`will-download` owner. All immutable origin Capture, STAGING_FIRST, SHA, routing,
Human approval derivation, atomic publish, Workstation registration and Lane
Allocation continue through existing trusted paths.

No arbitrary conversation prose is read and no general link automation exists.

## Old artifact safety

When Human arms AUTO, every allowed session gets a baseline of already-visible
VRA artifact markers. Existing artifacts are never downloaded automatically.

## BLOCKED Result semantics

A BLOCKED Task Result is now a progress return. It is returned once to the
originating Vera but does not clear AwaitingResult or AUTO task context.
DONE/FAILED remain terminal and close the task context.

This allows:
VRA generated → BLOCKED while waiting → VRA auto Capture/dispatch → Evidence
→ later DONE.
