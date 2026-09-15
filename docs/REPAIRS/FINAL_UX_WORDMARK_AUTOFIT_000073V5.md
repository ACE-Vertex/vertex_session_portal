# Session Portal Final UX Wordmark + Auto-Fit 000073V5

## Header

The existing topbar/header height is preserved.

The old small text brand is replaced by the approved `VERTEX SESSION PORTAL`
wordmark:
- VERTEX: pale white
- SESSION: cyan
- PORTAL: pale white

The SVG asset uses a tighter viewBox and a larger in-header presentation so the
brand reads clearly without increasing topbar height.

## Main window fit

The Electron outer window follows the visible internal layout only at layout
change boundaries:
- initial bootstrap
- + VERA
- - VERA
- session presentation hide
- canonical lane layout change

It does not continuously chase polling/status updates, so Human manual resize is
respected between layout changes.

The renderer can request only desired content width/height and reason. Main
process resolves the owning BrowserWindow from the IPC sender, preserves
maximized/fullscreen state, and clamps the result to the current display work
area. Renderer does not control x/y or an arbitrary window id.

Visible layout width is based on Explorer width plus sessionTrack.scrollWidth.
Because presentation-hidden Vera sessions are display:none, hidden canonical
sessions remain alive for routing/evidence while not contributing to visual fit.

No Workstation production files are touched.
