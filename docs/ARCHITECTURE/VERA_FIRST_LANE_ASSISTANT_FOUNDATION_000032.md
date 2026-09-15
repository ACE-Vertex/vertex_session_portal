# Vera-First Lane + Dedicated Assistant Foundation 000032

## Canonical direction

Vertex Session Portal is a **Vera-dedicated session browser**, not a generic multi-LLM switcher.

- The five main lanes are Vera Session 01..05.
- Vera remains the primary identity in every lane.
- The primary transport target is the user's logged-in ChatGPT browser session.
- Each Vera lane may optionally carry one dedicated AI Assistant.
- External/local models (Ollama, LM Studio, OpenAI API, OpenAI-compatible, raw local model) belong to the Assistant layer only.
- Removing or leaving an Assistant empty means **NO ASSISTANT**; it never means substituting Vera with qwen3:8b or another model.
- Existing provider-backed chat is explicitly labeled **LEGACY CHAT ENGINE** during the migration and is not the identity of Vera.

## Scope of 000032

This is the first renovation foundation. It changes canonical contracts and the Explorer/Status UI semantics so later runtime work cannot repeat the `VERA DEFAULT = model` mistake. It does **not** yet replace the legacy provider-backed chat transport with embedded logged-in ChatGPT browser sessions. That transport migration is a separate follow-up patch.

## Reserved work

Project Explorer Tree remains reserved for dedicated patch **000031** and is not modified here.

## Memory architecture

VCR/VCA/VMB memory convergence, VCA weighting/Memory Gravity, Memory Clock synchronization, and ARD multi-Vera relay are intentionally not implemented by this patch. They remain first-class follow-up work after the Vera-first transport foundation.
