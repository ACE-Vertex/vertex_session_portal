# One-click Human Dispatch 000104V5

The `工場へ発注` button itself is now the explicit Human Gate.

Flow:

`Human click -> existing safety/block checks -> durable Human Approval -> atomic _incoming publish -> Workstation`

The extra `工場へ発注しますか？` confirmation dialog is retired.

Preserved:
- Human Gate (the physical dispatch button click)
- existing Workstation safety/block checks
- busy/double-click guard
- durable approval and atomic publish in main process
- TEST-only RE-RUN gate from 000102V5
- remove/delete confirmation dialog
- no automatic Apply

Production mutation: `VraDispatchLane.ts` only.
