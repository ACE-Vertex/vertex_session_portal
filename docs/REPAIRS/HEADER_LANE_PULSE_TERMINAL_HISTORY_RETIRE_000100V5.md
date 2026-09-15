# Header Lane Pulse Terminal-History Visual Retirement 000100V5

## Proven root cause

The Header Pulse's numeric ACTIVE count includes only BUSY/RESERVED states.
However the 32-cell grid also retained FAILED/REJECTED card `allocatedLane`
history as red/pink cells.

Therefore the UI could truthfully display `00/32 ACTIVE` while still showing
two pink cells. Those cells were failure history, not current lane occupancy.

## Repair scope

Production mutation is limited to:

- `src/renderer/src/components/MainFrame/MainFrame.css`

MainFrame TypeScript, Workstation, VRA service, Scheduler, Evidence FIFO,
Human Gate, exact-origin routing, and card `allocatedLane` facts remain unchanged.

The CSS rule uses higher specificity than the inline Header rule and renders
`data-state="FAILED"` exactly like FREE:

- neutral free background
- no glow
- default cursor

BUSY and RESERVED current-occupancy visuals remain unchanged.

## Contract

The 32-cell Header grid is a current occupancy indicator.

Historical failure remains available on Dispatch Cards and Evidence, but it is
not shown as an active lane lamp.

`00/32 ACTIVE` => zero colored occupancy cells.
