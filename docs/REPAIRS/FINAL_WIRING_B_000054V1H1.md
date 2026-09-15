# FINAL WIRING B 000054V1H1 — TypeScript Compatibility Repair

## Scope
This is a narrow repair over `vertex-session-portal-final-wiring-b-000054V1`.
No Workstation production file is changed and no Final Wiring B routing, ACK,
Evidence delivery, Prompt Relay, display title, lane pulse, Human Gate, or
Dispatch Bay production implementation is replaced.

## Root cause 1 — clipboard IPC return type
`register-vra-dispatch-ipc.ts` declared the clipboard handler as returning
`string`, while the installed Electron type surface resolves the operation as
`Promise<string>`. The handler is now explicitly async and awaits
`clipboard.readText()`. The renderer still receives `Promise<string>` through
the preload boundary. Paste-only behavior is unchanged and there is no auto-send.

## Root cause 2 — Project Tree contract regression
The 000054V1 replacement of `src/shared/contracts.ts` omitted four pre-existing
Project Tree exports. They are restored exactly from the VERIFIED
`vertex-session-portal-workspace-tree-active-neon-000039` contract:

- ProjectTreeNodeKind = DIRECTORY | FILE | SYMLINK | OTHER
- ProjectTreeNode
- ProjectTreeBreadcrumb
- ProjectTreeListing

The Project Tree service itself is not modified.

## Verification
The H1 verifier:
1. checks both repairs;
2. reruns the parent 000054V1 verifier in READ-ONLY static mode;
3. runs `npm run typecheck`;
4. runs `npm run build`;
5. verifies source hashes remain unchanged during VERIFY;
6. verifies the read-only Workstation reference files remain unchanged.

Production mutation remains VRA APPLY only.
