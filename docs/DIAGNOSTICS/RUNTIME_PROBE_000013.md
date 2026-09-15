# Runtime Probe 000013

This stage performs the first real Electron runtime inspection of VERTEX Session Portal.

It does not add product features. It adds a controlled diagnostic mode that:

1. builds the application,
2. starts the actual Electron main process,
3. creates the actual Workstation SQLite state,
4. loads the production renderer,
5. inspects the rendered Shadow DOM topology,
6. verifies 3 Main Vera + 1 Search Vera,
7. checks normal pane width (~600px minimum),
8. checks one Priority pane (~1200px target),
9. captures a real runtime screenshot,
10. writes a machine-readable runtime probe JSON.

Evidence is written locally under:

`EVIDENCE/RUNTIME_PROBE_000013/`

Normal application startup is unchanged when `VERTEX_RUNTIME_PROBE` is not set.
