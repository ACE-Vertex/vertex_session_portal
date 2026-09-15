# Session Portal Pane Resize + Composer Cap 000024

This stage corrects two UI contracts.

## Session pane width

000022 proved the numeric minimums, but automatic `flex-grow` caused normal panes to
remain wider than the intended 600px baseline on large screens.

000024 changes the behavior:

- Normal Vera / Search Vera default width: **600px**
- Normal hard minimum: **600px**
- Priority / focused hard minimum: **1200px**
- Priority pane may absorb surplus workstation width
- Every session receives a right-edge drag rail
- Manual drag can increase pane width without a maximum
- Manual drag is clamped at 600px normal / 1200px priority
- Double-clicking the rail resets manual sizing

This preserves the original "600 -> 1200 on focus" visual concept while still allowing
a 49-inch workstation to allocate more room deliberately.

## Message composer

The message entry area is capped so it can never consume a huge vertical region:

- Composer hard maximum: **115px**
- Textarea hard maximum / auto-grow cap: **72px**
- Normal composer remains approximately one compact row
- The always-visible metadata second row is removed
- Conversation content receives the remaining vertical space
- Enter sends; Shift+Enter still creates a new line
- Textarea remains vertically resizable within the cap
