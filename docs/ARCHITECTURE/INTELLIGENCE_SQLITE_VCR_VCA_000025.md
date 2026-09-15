# SESSION PORTAL INTELLIGENCE / SQLITE / VCR-VCA PATCH 000025

## Hard invariant
This patch MUST NOT alter the Session Portal topology: Explorer remains left, the three Vera session windows remain in their current order/structure, Search Vera remains the right-side retrieval surface, and the existing horizontal resize/priority behavior is preserved.

## Changes
- Bottom status bar now exposes active provider formal label, exact configured/attached model, connection state, and SQLite/VCR/VCA readiness/counts.
- Explorer gains an AI tab for Provider / Endpoint / API Key / selected LLM settings.
- API keys are never read back into renderer text and are stored per provider only with Electron safeStorage encryption; environment-key fallback remains supported.
- Provider runtime supports Ollama plus OpenAI-compatible endpoints (LM Studio, OpenAI, custom compatible endpoint).
- Workstation SQLite now owns an append-only VCR revision ledger and a VCA query surface over persisted session chat messages.
- VCR writes append a new revision instead of overwriting prior canonical state; searches resolve the current revision. VCA supports cross-session conversation search.
- Search Vera capability badges now report VCR/VCA as SQLite-backed instead of EXTERNAL; PROJECT/EVIDENCE retrieval behavior is otherwise unchanged.
- Vera 01/02/03 composer band minimum height is 270px, grows only after text exceeds the baseline, and caps at 900px.
- Readable UI text is increased roughly +2px, with tiny diagnostics/status/footer text retained at compact sizes.

## Non-goals
- Do not rearrange the four visible session/retrieval panes.
- Do not change current pane width rules, priority rules, or manual horizontal resize rails.
- Do not persist API keys in plaintext, VCA, VCR, localStorage, or chat history.
