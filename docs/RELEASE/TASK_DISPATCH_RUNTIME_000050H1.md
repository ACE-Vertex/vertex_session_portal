# Task Dispatch Runtime Publish 000050H1

000050 failed in its first verification command before the runtime publish reached its later verification steps. Its first command reused the old 000047 publisher, which carries old exact source-marker preflight assumptions.

000050H1 does not reuse that brittle publisher.

It:
1. verifies only the already VERIFIED 000049 Task Dispatch source contract,
2. builds the current Session Portal source,
3. copies the existing verified Electron runtime shell read-only,
4. replaces only the packaged renderer output in a side-by-side build,
5. smoke-runs that build for five seconds,
6. publishes to:
   `G:\Vertex_Project\Development\vertex_workstation\SESSION_PORTAL_BUILDS\000050H1`,
7. atomically updates:
   `G:\Vertex_Project\Development\vertex_workstation\START_SESSION_PORTAL_LATEST.cmd`.

The currently running `SESSION_PORTAL_LATEST` directory is not mutated, avoiding Windows file-lock conflicts.

After VERIFY, close the current Session Portal and relaunch via `START_SESSION_PORTAL_LATEST.cmd`, then perform the VERA2 -> VERA1/3/4/5 TASK runtime test.
