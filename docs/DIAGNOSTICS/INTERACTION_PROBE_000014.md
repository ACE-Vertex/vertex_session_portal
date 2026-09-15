# Interaction Probe 000014

000013H5 proved the VERTEX Session Portal runtime baseline:

- Electron production renderer loads,
- preload bridge is alive,
- Workstation SQLite bootstrap is alive,
- 3 Main Vera + 1 Search Vera exist,
- one Priority Vera is 1200px,
- normal Vera panes are 600px,
- screenshot Evidence works.

000014 moves from static runtime inspection to actual Workstation interaction.

## Probe sequence

1. Start from a fresh diagnostic Workstation SQLite database.
2. Confirm initial state:
   - Vera 02 is Priority.
   - PROJECT sidebar is active.
3. Click Vera 01.
4. Verify Vera 01 becomes the only Priority session and expands to ~1200px.
5. Click the VCR sidebar tab.
6. Reload the production renderer.
7. Verify SQLite restores:
   - Vera 01 as Priority,
   - VCR as the active sidebar.
8. Capture screenshot and JSON Evidence after restoration.

This is not yet real LLM connection or Search Vera retrieval.
It verifies the core "mall traffic control" behavior and local Workstation state persistence.
