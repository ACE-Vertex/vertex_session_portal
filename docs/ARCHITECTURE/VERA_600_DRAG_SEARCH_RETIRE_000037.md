# VERTEX SESSION PORTAL — VERA 600 DRAG + SEARCH WINDOW RETIRE 000037

## Human intent

The real ChatGPT Browser lane proved wider than the original layout budget. The canonical operator target is five Vera browser lanes at a 600 px base width so the remaining horizontal workspace can later become a VRA / Vertex Works dispatch surface.

Search Vera must no longer consume a permanent lane. Lane focus/priority must no longer change width automatically. Human drag is the only lane sizing operation.

## 000037 contract

- MAIN Vera browser lane canonical base/minimum width: **600 px**.
- Focus / priority may change visual emphasis only; it must not expand or shrink a lane.
- The expand button and header-double-click sizing action are retired.
- Each Vera lane has an independent right-edge drag rail.
- A manually dragged width is persisted per Vera lane in renderer localStorage and restored on restart.
- Double-clicking the resize rail resets the lane to the canonical 600 px base width and clears the stored override.
- Search Vera is retired from the MainFrame render path and consumes **0 horizontal pixels**.
- Search/Retrieval backend source is intentionally not destroyed in this patch; only the dedicated Search Vera window is retired. This keeps retrieval reusable by future Vera/VCA features without occupying UI space.
- Project Explorer Tree remains reserved for dedicated 000031 work.
- No VRA / Works dispatch UI is created yet. 000037 only frees and stabilizes the horizontal workspace for that next stage.

## Width model

```text
Explorer 365 | Vera01 600 | Vera02 600 | Vera03 600 | Vera04 600 | Vera05 600 | [future VRA / Works]
```

A lane may be made wider by the Human at any time. No model, focus event, priority event, or automatic layout transition is allowed to change that width.
