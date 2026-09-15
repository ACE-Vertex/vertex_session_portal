# Vertex Shell Right-Click Paste 000080V4DH2

H2 corrects the H1 verifier false negative.

Observed H1:
- all right-click paste checks PASS
- Electron clipboard await fix PASS
- TypeScript typecheck PASS
- only COMPOUND_COMMAND_PRESERVED failed

Root cause:
The H1 verifier looked for a UI hint string in the Host Bridge.
Actual compound-command behavior lives in `vertex-shell-service.ts`.

H2:
- keeps the H1 right-click paste implementation unchanged
- verifies compound-command preservation against the real service contract:
  `hasCommandSeparator` + standalone cd/set-location matcher
- reruns full Session Portal typecheck

No change to:
- Vertex Shell service
- main index
- preload
- MainFrame
- VRA Dispatch
- Human Gate
- Workstation
