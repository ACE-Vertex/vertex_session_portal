# Vertex Target-Aware Roundtrip Task Bus 000053

000053 promotes Vera Task Dispatch from one-way delivery into a target-aware roundtrip task bus.

## 1. Per-target readiness queue

A destination Vera may already be generating a response, may not have a composer yet, or may contain a Human draft.

Each target now has its own FIFO queue.

States observed before send:

- TARGET_BUSY_GENERATING
- TARGET_WEBVIEW_NOT_READY
- TARGET_COMPOSER_NOT_FOUND
- TARGET_COMPOSER_DISABLED
- TARGET_COMPOSER_OCCUPIED
- TARGET_READY_EMPTY
- TARGET_READY_STAGED

A busy destination is not treated as failure. The task stays queued and is sent automatically when that specific destination becomes ready.

The composer occupied guard prevents overwriting a Human draft.

## 2. Selective routing

`targets` is sparse. Only listed sessions receive a task.

Example: send only to VERA1 and VERA4.

```json
"targets": {
  "vera-01": "Boot layerを調査してください",
  "vera-04": "Integration境界だけ監査してください"
}
```

VERA3 and VERA5 receive nothing.

## 3. Different prompt per destination

Each `targets[session]` value is independent.

A single dispatch may therefore send four completely different prompts to VERA1, VERA3, VERA4 and VERA5.

## 4. Structured automatic result return

Every delivered task is automatically wrapped with a return contract.

The target Vera is instructed to finish its answer with:

```text
[VERTEX_TASK_RESULT/1]
{
  "schema": "vertex-task-result/1",
  "dispatch_id": "...",
  "source_session": "vera-01",
  "return_to": "vera-02",
  "status": "DONE",
  "message": "発信元が把握すべき結果"
}
[/VERTEX_TASK_RESULT/1]
```

Session Portal does not scrape arbitrary response prose. It polls only for this explicit marked block for a task it is already awaiting.

The result contract is validated against:

- dispatch_id
- actual target/source session
- return_to origin session
- non-empty result message

After capture, the result is queued back to the original Vera. If the original Vera is currently generating or its composer is occupied, the result waits until it becomes sendable.

Thus:

`VERA2 -> VERA1 task -> VERA1 result -> VERA2`

is automatic in both directions.

Target AUTO does not need to be armed for result return. AUTO arming controls whether that Vera's own newly emitted task envelopes are allowed to fan out.


## 000053H1 repair

000053 failed before npm build. The inherited source preflight still required the
old manual HUD label `VERTEX // TASK DISPATCH`, while 000053 intentionally renamed
that surface to `VERTEX // TARGET ROUTER`.

The roundtrip queue/routing implementation was therefore rolled back before it
was compiled.

H1 corrects that preflight and also repairs a second brittle verifier that expected
a nonexistent `task: row.task` spelling. The implementation intentionally maps
each sparse `targets` entry with object shorthand `task,` and later consumes the
independent prompt as `row.task`.

No routing design is weakened:
- per-target readiness FIFO
- busy/draft hold
- selective sparse targets
- distinct prompt per target
- structured result return
- marker-bounded result capture
all remain required.


## 000053H2 repair

000053H1 advanced beyond its repaired source preflight and reached the build/output
verification stage. The remaining failure was in the verifier itself.

The publisher searched the compiled Vite renderer for proof strings that existed
only as TypeScript comments:

- TARGET_READINESS_QUEUE_IS_NATIVE
- SELECTIVE_TARGET_ROUTING_IS_NATIVE
- DISTINCT_PROMPT_PER_TARGET_IS_NATIVE
- STRUCTURED_RESULT_RETURN_IS_NATIVE

Those comments are not a valid runtime contract because Vite/esbuild may remove
comments while producing the renderer bundle.

H2 replaces comment-dependent compiled checks with semantic strings that are part
of the executable behavior and survive minification:

- TARGET_BUSY_GENERATING
- TARGETS:
- target_session=
- VERTEX TASK RESULT RETURN
- VERTEX_TASK_RESULT/1
- VERTEX // RESULT CAPTURED

Source-level verification still explicitly proves sparse target routing,
independent per-target prompts, FIFO readiness holding, and structured result
return. Runtime verification now checks durable behavior markers rather than
build-tool comment preservation.
