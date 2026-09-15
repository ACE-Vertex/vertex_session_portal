# Dispatch Bay Empty State Layout 000065V5

## Root cause

The Session Portal Dispatch Bay grid used auto-placement:

header / notice / queue / worksDrop / footer

When `.notice` was `hidden`, it no longer participated in auto-placement.
That shifted `.queue` upward and placed `.worksDrop` into the `minmax(0,1fr)` row.

Result:
`NEW WORKSTATION · HUMAN DISPATCH`, its arrow, and its explanatory text were spread vertically across a huge empty block.

## Repair

The lane now uses explicit CSS grid areas:

- header
- notice
- queue
- drop
- footer

A hidden notice can no longer move the queue/drop/footer into the wrong row.

## Empty BAY behavior

When VRA card count is zero:

- the Human Dispatch drop-zone is hidden;
- the large meaningless dashed block disappears;
- the center of the Bay shows a quiet `BAY READY` / VRA waiting state;
- footer counters remain visible.

When at least one VRA card arrives:

- the Human Dispatch drop-zone automatically reappears;
- drag/drop dispatch remains available;
- 工場へ発注 / Human Gate remains unchanged.

## Preserved

- visible card remove
- EXPORT
- exact-origin Evidence return
- Evidence ACK
- Human Gate
- Workstation lane authority
- no direct HTTP APPLY / VERIFY / ROLLBACK
- Workstation production mutation = zero
