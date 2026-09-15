# VERTEX Session Portal — Architecture Baseline

## Position

VERTEX Session Portal is Vera's dedicated multi-session Agent System / Virtual ARD workspace.

It is the Workstation-side container, traffic controller, visual workspace and capability
surface in which multiple independent Vera sessions can coexist.

Mall metaphor:

- Session Portal = building / shared facilities / traffic flow
- Main Vera sessions = specialist stores
- Search Vera = information desk / archive runner
- Optional fifth Vera = temporary event space

## Session topology

Default active:

- Vera 01 — Main
- Vera 02 — Main
- Vera 03 — Main
- Search Vera — dedicated retrieval / excavation

Max simultaneous active Vera sessions: 5.

Roles are mission-projected, not permanently bound to slots. This enables Virtual ARD
(Architect → Developer → Reviewer, etc.) while preserving independent contexts.

## Session sizing

- Normal minimum: 600px
- Priority target: ~1200px
- Maximum: none
- Preserve pane width; use horizontal movement/reflow instead of crushing a pane.

## Sidebar

- PROJECT — local project reality
- VCR — canonical definitions / history / relations / Evidence
- VCA — conversation archive / context excavation

Session Portal references these systems; it does not own them.

## Local SQLite

Workstation-local state only:

- session state
- pane priority/layout
- local preferences
- future cache/index/queue/capability state

SQLite is not a second VCR.

## UI Control Channel

Visible conversation text and Workstation control are separate channels.

Initial typed intents:

- SIDEBAR_SWITCH
- SESSION_FOCUS
- SESSION_EXPAND
- VCR_OPEN
- VCA_SEARCH
- PROJECT_REVEAL

This enables Vera-driven viewpoint guidance without executable strings in chat content.

## MSSQL boundary

Session Portal does not require its own MSSQL database. Current MSSQL stores are temporary
hosts during the pre-Vertex-DB-Core phase.

## CSS / component principle

> Consistency by DNA, identity by component.

Shared tokens define the design DNA. Each component owns minimal local CSS inside Shadow DOM.
Some duplication is acceptable when it protects local reasoning, editability and user identity.

Never hand-edit generated/minified output.

## DOM failure prevention

The old factory DOM-collapse failure must not repeat.

Construction order:

1. shell / state model
2. major components
3. working skeleton
4. behavior verification
5. visual refinement
