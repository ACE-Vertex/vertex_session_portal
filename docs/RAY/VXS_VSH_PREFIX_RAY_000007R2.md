# VXS VSH Prefix Ray 000007R2

R1 failed inside the observation harness. R2 hardens output handling for
Windows Workstation redirected logs:

- stdout/stderr forced to UTF-8 where supported
- every source-context line is ASCII-safe escaped before printing
- UI glyphs cannot trigger a UnicodeEncodeError
- production source remains read-only

Targets:
- current vertex-shell-host-bridge.ts
- current vertex-shell-service.ts
- renderer shell unit TS/CSS
- broad src legacy-literal sweep
- built main bundle literal counts

Expected use:
Identify the exact current source anchor that still generates `VSH` for new
terminal output, then issue a SHA-guarded minimal repair.
