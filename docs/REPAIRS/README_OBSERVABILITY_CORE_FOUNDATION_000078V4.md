# Vertex Session Portal Observability Core Foundation 000078V4

This pass implements a hidden Control Plane / Observability Core, not a visible
GUI.

Implemented:
- Runtime Lifecycle Black Box
- Runtime fingerprint hashes
- Correlation Trace API
- State Transition Journal
- 5-minute in-memory Performance Flight Recorder
- event-loop lag + process memory samples
- process crash / render-process-gone / child-process-gone observation
- Event Ray incident bridge
- automatic Incident Evidence Packer
- JSONL rotation

Automatic incident triggers currently consume Event Ray candidates:
- focus_authority_violation_candidate
- ime_composition_focus_loss_candidate
- ime_submit_collision_candidate
- ime_enter_during_composition
- scroll_backlash_candidate

Runtime files after Session Portal restart:
- `<userData>/observability/black-box.jsonl`
- `<userData>/observability/incidents/<incident_id>/incident-evidence-pack.json`
- `<userData>/observability/incidents/<incident_id>/flight-recorder.jsonl`
- `<userData>/observability/incidents/<incident_id>/event-ray-tail.jsonl`

Not wired in this pass:
- actual VRA Dispatch -> Workstation correlation binding
- Workstation Evidence -> Portal correlation binding
- Human MARK INCIDENT button
- renderer UI

Those are deliberately deferred until this Core is VERIFIED, so existing VRA,
Human Gate, Vera1-5 layout, and Workstation integration files do not collide
with other parallel Vera work.

Observability never auto-repairs or auto-applies.
