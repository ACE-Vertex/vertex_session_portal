# VRA / Works Dispatch Lane 000038

## Purpose

Turn Vertex Session Portal into the handoff surface between Vera browser sessions and Vertex Works without bypassing the existing HUMAN_APPLY gate.

## Flow

1. A user downloads a `.vra` artifact from any Vera ChatGPT browser lane.
2. Electron intercepts that `.vra` download on the shared persistent ChatGPT session.
3. The artifact is saved into a Portal-owned staging directory instead of becoming an unmanaged browser download.
4. SHA-256, size, source Vera lane and capture time are recorded as a VRA card.
5. The right-side VRA / Works Dispatch Bay displays the card.
6. Human explicitly presses `SEND TO WORKS` or drags the card into the Works Receiving Bay.
7. The Portal verifies the staged SHA-256 and copies the `.vra` into the sibling `_incoming` receiving directory (or `VERTEX_WORKS_INCOMING` when configured).
8. Vertex Works remains responsible for Inspect / Stage / HUMAN_APPLY / Verify. Portal dispatch never applies a VRA by itself.

## Boundary

- No ChatGPT DOM scraping.
- Only `.vra` browser downloads are intercepted.
- Other browser downloads keep their normal behavior.
- The Portal does not auto-run Works and does not bypass HUMAN_APPLY.
- Duplicate VRA downloads are suppressed by SHA-256.
- Dispatch verifies the staged SHA-256 before copying to Works.

## UI

The Dispatch Bay is appended after Vera lanes inside the horizontal session track. It is intentionally independent from the retired Search Vera window.

Cards can be dispatched either by button or by drag/drop into `WORKS RECEIVING BAY`.
