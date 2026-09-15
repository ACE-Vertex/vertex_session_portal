# Vertex Session Portal Observability Core — PRE-FLIGHT 000091V5

Purpose:
- Audit the current Session Portal source anchors before implementing the hidden Observability Control Plane.
- No human-facing UI is added.
- No production source file is modified by the verification script.
- The script writes only a research JSON report under `research/`.

Target architecture:
- Ray: READ-ONLY observation.
- Sensor: change/error/runtime signal collection.
- Judge: cause classification and next-action decision.
- Impact: pre-apply dependency/impact analysis.
- Guard: policy/human-gate/ownership boundary checks.
- Black Box: bounded logs, environment facts, execution context.
- Evidence Intelligence: compact Vera/LLM-readable failure/success summary.
- Observability Coordinator: internal control-plane orchestration.

Non-negotiable invariants:
- Preserve Human Gate and STAGING_FIRST.
- Do not scrape Vera browser DOM.
- Do not expose observability internals as Human UI.
- Workstation remains APPLY/VERIFY/ROLLBACK execution authority.
- Workstation remains Lane Allocation Authority.
- External lane policy remains ANY/PREFER.
- Ray remains read-only.
