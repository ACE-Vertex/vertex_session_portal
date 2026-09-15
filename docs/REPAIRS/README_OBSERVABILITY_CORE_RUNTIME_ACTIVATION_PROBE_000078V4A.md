# Observability Core Runtime Activation Probe 000078V4A

Run only after a full Session Portal restart following VERIFIED install of
000078V4.

Read-only activation proof requires a recent Black Box containing:
- runtime_start
- observability_generation = 000078V4
- event_ray_bridge_started
- runtime_sample

It also reports:
- runtime_fingerprint
- automatic incident pack count

No source, process, Black Box, or Event Ray mutation is performed.

On ACTIVE, the next integration pass is:
000079V4_CORRELATION_BINDING_AND_HUMAN_INCIDENT_MARKER
