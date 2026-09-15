# Virtual ARD Core 000016H1 — MainFrame TypeScript parse repair

## Evidence

000016 applied successfully but failed during TypeScript web typecheck:

`src/renderer/src/components/MainFrame/MainFrame.ts(321,8): error TS1109: Expression expected.`

## Root cause

The non-null assertion operator for `shadowRoot` was split across a newline:

```ts
this.shadowRoot
  !.querySelector<VertexExplorer>(...)
```

TypeScript parses `!.` as part of the preceding expression, so separating it after the
line break produces a syntax error.

## Repair

Keep the assertion attached to the expression:

```ts
this.shadowRoot!.querySelector<VertexExplorer>(...)
```

No Virtual ARD architecture, SQLite schema, IPC contract, UI behavior, role projection,
handoff logic, or security boundary is changed.

The original `verify_virtual_ard_core_000016.py` verifier is re-run unchanged.
