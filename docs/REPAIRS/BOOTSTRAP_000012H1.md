# VERTEX Session Portal Bootstrap 000012H1

## Repair

Initial bootstrap 000012 reached the project successfully but failed during `npm install`
with an npm ERESOLVE peer-dependency conflict:

- electron-vite 5.0.0 accepts Vite ^5 / ^6 / ^7.
- bootstrap 000012 pinned Vite 8.2.2.
- Vite is therefore pinned to 7.3.6 for this baseline.

This repair does not alter the Session Portal architecture, UI topology, MSSQL boundary,
SQLite policy, or component/CSS strategy.

Verification intentionally reuses `scripts/verify_bootstrap_000012.py` so the original
install -> typecheck -> build gate is exercised again against the repaired dependency tree.
