# AI LANES + EXPLORER 365 — 000028

## Scope

This patch changes only the Session Portal Explorer / AI provider configuration path and the provider routing needed to make five independent AI lanes real.

## Explorer

- Canonical Explorer width: 365px.
- Horizontal overflow is suppressed; form controls are constrained to the Explorer width.
- Scrollbars are visually hidden while vertical wheel/trackpad scrolling remains available when content exceeds the viewport.

## AI lanes

Five independent lanes are persisted:

- LANE 1 -> `vera-01`
- LANE 2 -> `vera-02`
- LANE 3 -> `vera-03`
- LANE 4 -> `vera-search`
- LANE 5 -> reserve / future optional Vera session

Each lane can override Provider, Endpoint, Selected LLM, API Key, and Local Raw LLM source.

An empty lane is not disconnected. Removing / leaving the lane override empty resolves that lane to **VERA DEFAULT**. The pre-existing singleton provider profile is preserved as the Vera Default backend so existing installations migrate without losing the currently working provider configuration.

## Local provider

`local` is a first-class provider configuration option. Selecting it exposes `LOCAL LLM SOURCE` and a native file picker for `.gguf`, `.bin`, `.safetensors`, or another explicitly selected file.

The raw file path is persisted per lane. 000028 intentionally does not invent a raw-model runtime. If a local raw model is selected, its source is valid configuration/evidence, while actual inference requires a later runtime bridge (for example a llama.cpp/Runtime Factory binding). Explicit local selection therefore does not silently masquerade as Vera Default.

## Model selection

`SELECTED LLM` is a combo input backed by a datalist. `LIST` asks the configured provider for available model IDs:

- Ollama -> `/api/tags`
- OpenAI / LM Studio / OpenAI-compatible -> `/v1/models`
- Local -> selected raw model filename

Manual entry remains possible when an endpoint does not publish a model list.

## Credentials

Per-lane API keys are encrypted with Electron `safeStorage` and stored separately from provider metadata. Empty lanes use Vera Default credential resolution.

## Non-goals

- No VCR card/modal implementation in this patch.
- No session pane-width 600px behavior change.
- No PowerShell flicker repair.
- No change to the 000026/000027 composer behavior.
