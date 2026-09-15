# Search Vera Retrieval Core 000018H1 — Node Dirent type repair

## Evidence

000018 applied, but TypeScript node typecheck failed in:

`src/main/retrieval/local-retrieval-service.ts`

with `Dirent<string>[]` vs `Dirent<NonSharedBuffer>[]` overload/type incompatibility.

## Cause

`ReturnType<typeof readdirSync>` is unsafe for an overloaded Node API. With the
current Node type definitions, `ReturnType` selected a Buffer-oriented overload,
while the actual call uses the normal string-name `withFileTypes: true` form.

That made `entry.name` appear as a buffer type downstream.

## Repair

Replace the overloaded-function `ReturnType` declaration with the actual contract
used by this call:

```ts
import type { Dirent } from 'node:fs'

let entries: Dirent<string>[]
```

No Search Vera retrieval behavior, scope, model provider, SQLite schema, UI,
security boundary, or dependency policy is changed.

The original `verify_search_vera_retrieval_core_000018.py` verifier is re-run
unchanged.
