# Vertex Contract Catalog API

Read-only Portal bridge for the active shared contract catalog.

Renderer access:

- `window.vertexContractCatalog.resolve('vertex.vra.issue/1')`
- `window.vertexContractCatalog.resolve('vertex.evidence.read/1')`
- `window.vertexContractCatalog.list()`

This API does not mutate Registry, Workstation, Evidence, VRA files, Human Gate, or routing state.

Its only purpose is to make canonical contract truth retrievable instead of reconstructed from LLM memory.
