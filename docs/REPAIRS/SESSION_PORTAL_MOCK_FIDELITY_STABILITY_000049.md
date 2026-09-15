# VERTEX Session Portal — Mock Fidelity + Stream Stability 000049

## Purpose

Bring the current five-VERA Session Portal close to the approved high-density Vertex UI while repairing the regression where a ChatGPT lane can become difficult to use after a send/cancel cycle.

This is an implementation artifact, not another visual mock.

## Visual / UX scope

- Rebalances the upper-left brand block and renders `VERTEX | Session Portal` with a compact Vertex mark.
- Keeps the 3/4/5 window selector visible and moves it clear of the widened brand block.
- Adds one clear `PRIMARY ENTRY` status in the top bar.
- Applies the Vertex dark design DNA (`#070B10`, `#0C121A`, `#111923`, `#168CFF`, `#3AB8FF`) to the main shell, browser lanes, Explorer, window selector and Dispatch Bay.
- Keeps the five browser lanes and the existing Dispatch Bay topology rather than replacing the product layout.
- VERA 04 and VERA 05 no longer receive the Virtual-ARD `session-role` / mission-objective assignment chrome, so they use the same visible header structure as VERA 01–03. The literal `INDEPENDENT VERA · Human assigned session` is not introduced.

## Dispatch Bay — VRA Save Path

000046H2 already supplied the persistent global destination store, native folder picker, preload bridge and Electron download policy. 000049 deliberately does **not** overwrite that backend or the later 000048 destroyed-WebContents repair.

Instead, `VraDispatchDestinationControl.ts` is upgraded from the small gear-only control to a real `VRA Save Path` section inside Dispatch Bay:

- current path is always visible;
- DEFAULT / CUSTOM state is visible;
- the browse button opens the existing native folder picker;
- one global destination remains authoritative for the Portal;
- the old one-icon control is retired at runtime.

The source contains the old 000047 marker as a compatibility comment so the existing canonical publisher can continue to verify the destination feature without being rewritten in this pass.

## ChatGPT lane stability

The Portal does not scrape or automate the ChatGPT DOM.

The repair therefore acts at the Electron/WebContents layer:

- `disable-renderer-backgrounding`;
- `disable-background-timer-throttling`;
- `disable-backgrounding-occluded-windows`;
- `backgroundThrottling: false` for the Portal renderer, attached ChatGPT webviews and ChatGPT pop-outs;
- stronger Reload semantics (`stop` + `reloadIgnoringCache`);
- a dedicated `⟳` hard-recovery button in every VERA browser toolbar;
- explicit `unresponsive`, `responsive`, and `render-process-gone` state handling.

The anti-throttling policy is particularly important for a five-webview, ultrawide Session Portal where several active ChatGPT renderers can be partially occluded or deprioritized by Chromium.

## Launch policy

000049 creates **no new product launcher**.

After verification it republishes through the already-established 000047 canonical path:

`G:\Vertex_Project\Development\vertex_workstation\START_SESSION_PORTAL_LATEST.cmd`

which opens:

`G:\Vertex_Project\Development\vertex_workstation\SESSION_PORTAL_LATEST\Vertex Session Portal.exe`

Build/candidate directories may continue to exist internally, but the human-facing entrance remains the single `START_SESSION_PORTAL_LATEST.cmd` path.

## Verification

Works runs:

1. `scripts/apply_session_portal_mock_fidelity_stability_000049.py`
2. `scripts/verify_session_portal_mock_fidelity_stability_000049.py`

The verifier checks visual markers, VERA4/5 header gating, full VRA Save Path UI, WebContents anti-throttling/recovery logic, source build, canonical publish and canonical launcher verification.

### Manual acceptance after Works PASS

Because DOM scraping/automation is intentionally prohibited, the final ChatGPT behavioral check is human-visible:

- send two or more consecutive prompts in the same VERA lane;
- repeat on multiple VERA lanes;
- during generation use ChatGPT Cancel/Stop once, then confirm a subsequent prompt can be sent;
- if ChatGPT itself becomes unresponsive, press the Portal `⟳` recovery control and confirm the lane returns to `CHATGPT READY`.

## Preservation boundaries

- Preserve persistent shared ChatGPT partition and independent per-lane thread memory.
- Preserve five-window scaler.
- Preserve VRA capture / Works receiving lane / HUMAN_APPLY boundary.
- Preserve 000046H2 destination backend.
- Preserve 000048 destroyed-WebContents download policy repair.
- Preserve SQLite / VCR / VCA and existing project tree behavior.
- No ChatGPT DOM extraction and no automatic Apply.
