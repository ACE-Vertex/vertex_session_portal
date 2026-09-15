# VERTEX SESSION PORTAL — 000025H1 verification contract repair

## Cause

000025 implemented `openai-compatible` as a `ProviderKind` contract and exposed it in the provider settings / Explorer UI. `ConfiguredProvider` intentionally routes every non-Ollama OpenAI-style provider through the generic `openAiCompatibleStatus(cfg.provider, ...)` path.

The 000025 verifier incorrectly required the literal string `'openai-compatible'` to exist inside `configured-provider.ts`. The implementation is valid, but that literal lives in the canonical provider contract/settings/UI definitions rather than the generic transport implementation.

## Repair

No application topology or runtime source is changed.

The verifier now proves OpenAI-compatible support at the correct boundaries:

- `src/shared/contracts.ts` contains `openai-compatible` in `ProviderKind`.
- `provider-settings-store.ts` maps it to the formal label `OpenAI Compatible`.
- `Explorer.ts` exposes it as a selectable provider.
- `configured-provider.ts` routes the selected provider through the generic OpenAI-compatible status path.

All existing 000025 checks remain, including the three-pane layout invariant, 270–900px composer contract, SQLite VCR/VCA, encrypted provider credentials, footer status and production build.

## Scope invariant

This repair does **not** modify Vera 01 / Vera 02 / Vera 03 layout, Search Vera, pane sizing, CSS, SQLite schema, provider runtime, or any application feature source.
