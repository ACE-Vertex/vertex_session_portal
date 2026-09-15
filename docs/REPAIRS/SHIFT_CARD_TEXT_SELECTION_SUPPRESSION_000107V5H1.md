# Shift Card Text Selection Suppression 000107V5H1

000107V5 rolled back safely because its verifier returned exit 21.

Root cause was verifier-only: it compared the queue `mousedown` listener against
the first generic `click` listener inside `bind()`. Another unrelated click
listener appears earlier, causing a false ordering failure.

H1 production source is byte-equivalent to the intended 000107V5 repair.
Only verification logic changes: it now compares the exact queue-owned
`mousedown` and queue-owned `click` anchors.

Behavior:
- Shift + primary mousedown on card body prevents Chromium native text selection.
- Existing click handler continues to own contiguous card-range selection.
- Normal non-Shift text selection remains available.
- Interactive controls are excluded.
