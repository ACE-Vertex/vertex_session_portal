# Observability Runtime Startup Error Diagnosis 000078V4C

Read-only follow-up after 000078V4B established:
- source contains Observability Core,
- built out/main/index.js contains Observability Core and Event Ray,
- runtime Black Box is absent.

This pass checks:
- current Electron main-process creation time,
- out/main/index.js modification time,
- whether the active bundle is newer than the current process,
- activation call / app.whenReady / start markers in the built bundle,
- node --check syntax,
- userData / observability / Event Ray paths,
- userData ACL snapshot,
- recent runtime logs.

Important classification:
RUNNING_MAIN_PROCESS_PREDATES_CURRENT_OBSERVABILITY_BUNDLE
means a restart is sufficient before deeper mutation.

If activation is definitely present in a bundle older than/equal to the current
process and no Black Box exists, the next pass is a minimal bootstrap sentinel
plus exception capture around Observability startup.

No production/process/build/userData/Event Ray mutation.
