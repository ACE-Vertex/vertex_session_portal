# Vera Auto Task Dispatch + Vertex UI 000051

This release advances Task Dispatch from Human-click delivery to optional automatic Vera-to-Vera dispatch.

## Runtime controls

Each Vera pane receives:

- `TASK` — manual dispatch with a custom Vertex confirmation HUD.
- `AUTO` — per-pane auto arming. `AUTO●` means armed.

AUTO is OFF after every Session Portal launch. It is deliberately not persisted across application restarts.

## Automatic dispatch contract

Automatic delivery requires all of these conditions:

- complete `[VERTEX_TASK_DISPATCH/1] ... [/VERTEX_TASK_DISPATCH/1]` block,
- schema `vertex-task-dispatch/1`,
- `delivery: "AUTO"`,
- source_session exactly matching the real source Vera pane,
- target is one of vera-01 ... vera-05,
- self target forbidden,
- at most four targets,
- the source answer is not currently generating,
- the same dispatch_id is stable for two polling passes,
- dispatch_id + target receipt has not already been sent.

When AUTO is armed, the envelope is automatically routed to the target composers and the send buttons are activated. No per-dispatch native confirmation dialog is used.

## Replay safety

When AUTO is armed, any task envelope already visible in the source pane becomes the baseline and is not sent automatically. Only a newer `delivery=AUTO` envelope is eligible.

## Vertex visual language

Native browser `confirm()` / `alert()` are retired from this Task Dispatch path.

The new HUD uses the Vertex palette:

- Deep Background `#070B10`
- Panel `#0C121A`
- Raised Panel `#111923`
- Border `#26394B`
- Vertex Blue `#168CFF`
- Bright Blue `#3AB8FF`
- Success `#55D69E`
- Error `#FF6F7C`

The manual TASK flow uses a Vertex-styled dispatch panel; AUTO uses Vertex toasts/status and a blue glow on the armed button.


## 000051H1 repair

000051 failed before build/publish because its preflight verifier searched the TypeScript source for the rendered HTML spelling `data-vertex-task-auto`.

The actual implementation correctly creates the control with the DOM dataset API:

`autoButton.dataset.vertexTaskAuto = '1'`

Therefore the feature code was not the failure. The verifier token was wrong.

H1:
- reapplies the AUTO bridge that Workstation correctly rolled back,
- verifies the canonical `dataset.vertexTaskAuto` source form,
- replaces brittle minified-JavaScript syntax probes with durable semantic markers,
- publishes side-by-side to `SESSION_PORTAL_BUILDS\000051H1`,
- atomically points `START_SESSION_PORTAL_LATEST.cmd` to 000051H1,
- keeps AUTO OFF on application start.
