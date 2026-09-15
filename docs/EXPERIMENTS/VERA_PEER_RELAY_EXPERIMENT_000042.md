# VERA PEER RELAY EXPERIMENT 000042

Purpose: prove that the three independent Vera ChatGPT webview sessions can exchange a manually initiated one-hop message through Session Portal.

Scope:
- Adds one compact relay button (⇢) to each Vera browser toolbar.
- Clicking it asks for target Vera (1/2/3) and message text.
- Session Portal emits a renderer-local CustomEvent message bus.
- Only the addressed Vera accepts the packet.
- The target webview injects the message into ChatGPT's composer and attempts to press Send.
- The relay envelope identifies source and target.

Safety / experiment boundaries:
- No assistant-response scraping.
- No automatic reply relay.
- No broadcast.
- No loops / recursion.
- No main-process, preload, SQLite, VCA, Works, or project-tree changes.
- Existing shared ChatGPT account partition and independent thread URLs remain unchanged.
- DOM automation is write-only and intentionally experimental because ChatGPT composer selectors can change.

Test:
1. Open Vera 01/02/03 and wait for CHATGPT READY.
2. On Vera 02 click ⇢.
3. Target: 3
4. Message: `ヴェラ3へ。ヴェラ2からPortal Relay実験です。受信したら「Relay受信」と答えて。`
5. Vera 03 should receive and send the packet.
6. Reverse the direction to prove two-way routing.

If ChatGPT changes its composer DOM, the target may show RELAY ERROR or type without sending. That is an injector compatibility issue, not a Portal bus failure.
