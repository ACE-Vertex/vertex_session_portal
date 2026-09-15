# VXS Clipboard Normalization 000027

Purpose:
Eliminate the Presentation / Clipboard divergence where the visible VXS
transcript is canonicalized to `VXS` while the COPY button can still expose
legacy `VSH` transcript prefixes.

Observed baseline:
- `src/main/shell/vertex-shell-service.ts`
- SHA256 `5887d1be1857706fb06833b851ab098871c3e459ab8a97e7059b317ff3f0a860`

Repair:
- Preserve the internal transcript model.
- Preserve the existing COPY handler.
- Add a VXS-shell-scoped bubble-stage COPY normalizer.
- On the shell button whose label is exactly `COPY`, take the visible output
  text, pass it through the existing canonical VXS branding normalizer, then
  write that canonical transcript to `navigator.clipboard`.
- Do not intercept `COPY PATH` or Explorer behavior.
- Do not touch Observation / Return Bus, ACK, routing, registry lifecycle,
  Human Gate, or Workstation lane authority.

Patched service SHA256:
`e0bbba6057097005857527953a8470f5dde41cf876ac6a5bb16737d327f66b2e`

Runtime note:
This patch updates production source. A running Electron main process must load
the new build/runtime generation before the changed injected script can take
effect.
