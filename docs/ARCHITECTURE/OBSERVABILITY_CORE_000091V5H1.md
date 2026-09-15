# Vertex Session Portal — Hidden Observability Core 000091V5H1

This foundation is intentionally **not human-facing UI**.

## Responsibility split

Session Portal:
- observe
- analyze
- classify
- route evidence
- preserve Human Gate

Vertex Workstation:
- lock
- allocate lane
- apply
- verify
- rollback
- execute

## Internal modules

- `RayCore`: bounded read-only tree/content/dependency inspection.
- `SensorCore`: derives signals from Ray and Workstation Evidence.
- `JudgeCore`: deterministic first-pass cause classification.
- `ImpactCore`: reverse dependency impact calculation from resolved imports.
- `GuardCore`: enforces Ray read-only and HUMAN_APPLY/Human Approval rules.
- `BlackBox`: bounded in-memory evidence/event journal with SHA256.
- `EvidenceIntelligence`: normalizes Workstation Evidence and discovers stdout/stderr log paths.
- `ObservabilityCoordinator`: hydrates bounded command logs through Ray and feeds Sensor/Judge.

## Invariants

- No renderer component is added or changed.
- No human-visible observability dashboard.
- No Browser DOM scrape.
- Ray does not write or execute.
- VERIFY may not mutate production source.
- Human Gate remains authoritative for mutations.
- Workstation remains execution and lane-allocation authority.
- Existing `vra-dispatch-service.ts` is untouched by H1.
- Existing return routing is untouched by H1.

## H2 integration target

H2 will attach this core to the existing Evidence-return backend path only after H1 typecheck/build VERIFY passes. H2 should instantiate read roots narrowly, including Session Portal and only the Workstation runtime/evidence roots required to hydrate returned command logs.


## H1R1 verifier hardening

H1R1 keeps the foundation modules unchanged and hardens only verification execution: Windows `.cmd` launch goes through `COMSPEC`, subprocess exceptions/timeouts are printed to stdout/stderr evidence, and every failure path returns a deterministic exit code.
