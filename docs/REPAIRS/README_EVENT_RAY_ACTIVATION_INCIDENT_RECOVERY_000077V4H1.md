# Event Ray Activation / Incident Recovery 000077V4H1

000077V4 failed with runner exit 2. In that runner, exit 2 means no
`focus-scroll-event-ray.jsonl` was found.

Therefore the reported incident was NOT captured.

H1 is read-only and intentionally runs before restarting Session Portal. It
distinguishes:

1. Running Portal process predates H2 -> H2 source was VERIFIED but not loaded
   into the current Main Process. Restart is required.
2. Running Portal process started after H2 but no log exists -> runtime/build/
   entrypoint mismatch; a simple restart is not enough evidence.
3. Event Ray log exists elsewhere -> discovery bug in 000077V4; capture can be
   retried against the resolved path.
4. Portal process cannot be resolved -> diagnose process/entrypoint ownership.

H1 recursively searches APPDATA and LOCALAPPDATA to a bounded depth and compares
Portal process creation time with the H2 diagnostic module mtime.

No production source, process, or Event Ray log is mutated.
