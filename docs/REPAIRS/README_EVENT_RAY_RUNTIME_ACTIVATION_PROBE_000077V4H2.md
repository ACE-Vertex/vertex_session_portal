# Event Ray Runtime Activation Probe 000077V4H2

Run after a full Session Portal restart.

This is a read-only runtime activation probe. It does not modify Session Portal
production code, running processes, focus behavior, IME behavior, scroll
behavior, or the Event Ray log.

Activation is confirmed only when:
- a recent `focus-scroll-event-ray.jsonl` exists, and
- the log contains `event_ray_started`.

Observer/IME event counts are also returned when present.

Possible classifications:
- EVENT_RAY_RUNTIME_ACTIVE
- EVENT_RAY_LOG_PRESENT_BUT_RUNTIME_ACTIVATION_NOT_CONFIRMED
- EVENT_RAY_RUNTIME_NOT_ACTIVE_NO_LOG
