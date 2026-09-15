# H2 Production Source Rollback 000089V5

Purpose: undo only the two production-source changes introduced by
`vertex-session-portal-self-contained-bundled-workstation-000087V5H2`.

Restored files:

- `src/main/workstation/workstation-process-controller.ts`
  - exact VERIFIED owner: `000085V5`
  - expected SHA256: `64867a16c01db0138ca93cc91746224f566b04db71ef5e8ec3c80b657b76490e`

- `src/main/vra/vra-dispatch-service.ts`
  - exact VERIFIED owner: `000082V5`
  - expected SHA256: `8c5ba1e625c9bb44dc4ce72993e7f80b7094283cda3f5e72fb4bcd866a2b2653`

This does **not** delete release folders, Workstation executables, build scripts,
documentation, or H2 packaging outputs. Those are left inert so recovery is minimal
and reversible.

After APPLY, verification requires:

- exact pre-H2 hashes
- H2 bundled-runtime hooks absent from production source
- 000085 validated Workstation launch/replacement contract preserved
- 000082 Evidence payload bridge preserved
- Workstation HTTP registration contract preserved
- Human approval and immutable origin markers preserved
- `npm run typecheck` PASS
- `npm run build` PASS

Workstation source is not modified.
