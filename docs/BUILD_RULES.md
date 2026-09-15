# Build Rules

1. `src/` is truth. Never patch generated `out/` / `dist/`.
2. Keep CSS/JS/TS readable; no hand-maintained minified source.
3. Split by responsibility/change boundary, not arbitrary file count.
4. Shared CSS = design DNA; local CSS = component identity.
5. Shadow DOM contains local styles.
6. Small duplication is cheaper than hidden coupling.
7. Main process owns privileged OS/DB capabilities.
8. Renderer uses preload + typed IPC; `nodeIntegration` stays off.
9. SQLite = Workstation local state, not Canonical truth.
10. Default = 3 Main Vera + Search Vera. Max active = 5.
11. Pane min = 600px; Priority ≈ 1200px; no max.
12. View-control permissions and world-mutation permissions are separate.
13. Build the skeleton before fine correction.
