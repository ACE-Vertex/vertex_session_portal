# VCA Memory Inbox + Session Clock Bridge 000036

## Purpose

000036 installs the explicit boundary between a Vera ChatGPT browser session and Vertex-owned memory.
It does **not** scrape ChatGPT DOM content and it does **not** pretend that ChatGPT internal Memory is writable by Vertex.

The boundary records:

- Vera session identity (`vera-01` ... `vera-05`)
- current ChatGPT thread URL / thread key
- Human / Vera / Mutual / Unknown actor label
- capture time and source
- SHA-256 duplicate fingerprint
- VCA promotion event id
- PENDING / CURATED state
- logical Memory Clock relation to the Canonical Memory Frontier

## Flow

```text
Vera ChatGPT Browser Session
        |
        | navigation metadata only
        v
Vera Session Thread Binding
        |
        | explicit memory capture
        v
VCA MEMORY INBOX
        |
        | fingerprint dedupe
        v
Vertex VCA Memory Event
        |
        | deterministic seed
        v
12B-class Dedicated VCA Curator (when configured)
        |
        v
Append-only Weight Revision
        |
        v
INBOX = CURATED
```

## Status semantics

- `PENDING`: the memory has already been promoted into Vertex VCA, but no AI Curator revision has completed for the inbox item yet.
- `CURATED`: the configured dedicated AI Assistant appended a Curator weight revision.
- duplicate submissions are not copied; the existing inbox row increments `duplicate_hits`.

## Thread mapping

The browser lane reports only the current `https://chatgpt.com/...` navigation URL to the Portal. This lets Vertex bind a logical memory clock and captured memories to the correct Vera session / ChatGPT thread without reading page content.

No external browser cookies are imported. No `executeJavaScript` or ChatGPT DOM extraction is introduced.

## Relation foundation

`vca_memory_relation` is installed as an append-only relation surface for later Curator work. 000036 does not invent semantic relations without evidence; future Curator passes can use this table to bundle memories that belong to the same topic or design line.

## Project Tree

The Project Explorer Tree rebuild remains a dedicated work item and is intentionally not implemented by 000036.
