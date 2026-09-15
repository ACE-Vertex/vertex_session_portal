# Real LLM Session Core 000017

000016H1 proved the Virtual ARD mechanics with deterministic diagnostic text:
three independent Main Vera contexts, mission-projected A/D/R roles, typed handoffs,
SQLite persistence and UI projection.

000017 places an actual local LLM provider behind those three Vera sessions.

## Dependency principle

No new npm runtime or model SDK is added.

Electron/Node native `fetch` talks directly to the already-existing Ollama HTTP API.
This follows the VERTEX rule:

**Unitize behavior, consolidate infrastructure.**

Three Vera session units do not create three runtimes.

## Components

- `SessionAgentStore`
  - local SQLite conversation ledger per session
- `OllamaProvider`
  - local provider discovery / chat over native fetch
- `SessionAgentService`
  - session isolation
  - current Virtual ARD role projection
  - typed incoming handoff injection
- `SessionAgent IPC`
  - provider status
  - read conversation
  - send message
- `VeraSession`
  - real textarea/send path
  - persisted USER / ASSISTANT history

## Diagnostic self-play

A real local model is asked to run:

Architect Vera
→ real response
→ typed PLAN handoff

Developer Vera
→ real response using incoming typed handoff
→ typed IMPLEMENTATION handoff

Reviewer Vera
→ real response using incoming typed handoff

The verifier checks each session has exactly its own USER + ASSISTANT pair.

This is real model execution, but it does not claim the local model is GPT-5.6 or the
hosted ChatGPT Vera. It is the first real provider mounted into the Session Portal
Vera-session architecture.
