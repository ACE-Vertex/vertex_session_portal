# Responsive Session Sizing 000022

The visual contract is:

- Normal session **minimum width = 600px**
- Priority / focused session **minimum target = 1200px**
- No maximum width
- Available extra horizontal space should be distributed to sessions
- When the window is too narrow, sessions must not be crushed below their minimums;
  the session viewport scrolls horizontally instead.

The previous implementation accidentally treated 600 / 1200 as fixed widths.

000022 changes only sizing behavior:

- normal: `flex: 1 1 600px; min-width: 600px; width: auto`
- priority: `flex: 2 1 1200px; min-width: 1200px; width: auto`
- track: `width: max-content; min-width: 100%`

Therefore:
- wide screens use available space,
- 49-inch layouts stop wasting space,
- narrow screens preserve readability,
- 600 / 1200 remain hard lower bounds rather than hard fixed widths.
