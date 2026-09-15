# CHATGPT WEBVIEW INTERNAL FLEX REPAIR 000039H3

## Purpose

Repair the ChatGPT guest viewport without rolling the Session Portal layout backward.

Ray 000014 confirmed that the outer height chain is present. H2 then synchronized the host element to the measured browser-body rectangle, but the guest viewport still rendered at a short height. The remaining source-level conflict is the `webview` host rule itself: Session Portal overrides Electron's required/default flex display with `display:block`. Electron documents that the `<webview>` host uses flex internally so its child OOPIF/iframe fills the host, and warns not to override that flex display.

## Repair

- Change only `.chatgptView` from `display:block` to `display:flex`.
- Preserve the H2 ResizeObserver exact-pixel viewport synchronization.
- Preserve all outer layout, 600px lane sizing, Project Tree, VCA, Dispatch Bay, persistent ChatGPT partition, Thread Bridge, and VRA download bridge.
- No ChatGPT DOM scraping and no guest `executeJavaScript`.

This is a targeted correction to the current implementation, not a rollback.
