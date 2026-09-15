# Vertex Session Portal — Workspace Tree + Active Neon 000039

## Purpose

000039 converts the real Project Tree from a project-root cage into a read-only Vertex workspace navigator, while preserving the dedicated tree UI and the VRA / Works logistics lane.

The canonical project still opens first. From there the operator can move upward to the Vertex workspace boundary, use Explorer-style breadcrumbs, enter sibling projects, and return home without filesystem mutation.

## Workspace navigation

- Initial root: current canonical project (`process.cwd()`).
- Workspace boundary: when the canonical project lives under a `Development` directory, the boundary becomes that directory's parent (`Vertex_Project`). Otherwise the boundary is the canonical project's direct parent.
- Up button moves to the parent folder until the workspace boundary.
- Home button returns to the canonical project root.
- Breadcrumb buttons re-root the tree at any visible ancestor.
- Folder disclosure arrow keeps lazy inline expansion.
- Double-click / Enter on a directory opens that directory as the tree root.
- Right-click adds `OPEN AS TREE ROOT`.
- Directory-first sorting, symlink non-traversal, selection, refresh, open/reveal/copy remain.
- No delete, rename, move, write, create, or filesystem mutation APIs are introduced.

## Vera window visual focus

Focus no longer changes pane width. A Vera lane only receives a water-cyan neon frame when it is the visually active chat lane. Other lanes remain on the normal Vertex border treatment.

The visual-active event is renderer-only and does not change backend priority, ARD role, model selection, or stored lane width.

## ChatGPT lower white-line repair

The ChatGPT webview host no longer exposes a white backing surface at the bottom edge. The browser body and webview backing are black, the webview fills the browser body absolutely, and no white fallback pixel is available during fractional layout rounding.

## Preserved boundaries

- VRA / Works Dispatch Lane remains mounted.
- Search Vera remains retired.
- 600px Vera lane design token and manual drag resize remain untouched.
- ChatGPT persistent account partition remains untouched.
- VCA / VCR / Thread Bridge remain untouched.
