# Visual Canonical SF 000020H1 — TypeScript template literal repair

## Evidence

000020 applied the Visual Canonical SF restoration files, but the verification build
stopped in `src/main/diagnostics/visual-canonical-probe.ts` with:

- TS1127 Invalid character
- TS1160 Unterminated template literal

## Root cause

The generated VRA accidentally preserved Python-source escaping in TypeScript template
literals. The emitted file contained forms such as:

```ts
console.log(\`VISUAL_...=\${attempt} PASS\`)
```

The backslashes belong only to the generator string and must not exist in the final
TypeScript source.

## Repair

Convert only the escaped template-literal syntax back to normal TypeScript:

```ts
console.log(`VISUAL_...=${attempt} PASS`)
```

No UI layout, color, CSS, interaction behavior, SQLite, Virtual ARD, UI Control,
provider, Search Vera, or retrieval logic is changed.

The original `verify_visual_canonical_sf_000020.py` verifier is re-run unchanged.
