# FINAL WIRING B 000054V1H2 — Project Tree API Bridge Repair

H1 proved the Final Wiring B static contract and node typecheck, but web typecheck exposed that the Final B replacement of `src/preload/index.ts` and `VertexPortalApi` had dropped the pre-existing Project Tree renderer API.

This repair restores only the previously VERIFIED Project Tree surface from artifact `vertex-session-portal-project-tree-real-000031` / later workspace-tree baseline:

- `listProjectTree(path?: string): Promise<ProjectTreeListing>` -> `project-tree:list`
- `resolveProjectTreePath(path: string): Promise<string>` -> `project-tree:resolve`
- `openProjectTreePath(path: string): Promise<void>` -> `project-tree:open`
- `revealProjectTreePath(path: string): Promise<void>` -> `project-tree:reveal`
- `copyProjectTreePath(path: string): Promise<void>` -> `project-tree:copy-path`

`PROJECT_TREE_CONTRACT` is also restored as the existing REAL_FILESYSTEM / read-only / lazy / no-symlink-traversal contract. No Project Tree service logic is changed.

Final Wiring B ACK, exact-origin Evidence return, Prompt Relay paste-only behavior, display title persistence, header lane pulse, Dispatch Bay, Human Gate, capture/staging/export, and Workstation production remain unchanged.

VERIFY first checks this bridge statically, then executes the H1 verifier, which reruns the complete Final B static gates and real `npm run typecheck` + `npm run build`.
