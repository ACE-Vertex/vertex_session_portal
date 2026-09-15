# VERA CHATGPT BROWSER BRIDGE 000033

## Purpose

Vertex Session Portal is a Vera-dedicated session browser.

This patch migrates each active MAIN lane from the legacy provider-backed chat surface to a real ChatGPT browser surface while preserving the existing Session Portal lane topology.

## Canonical behavior

- Vera Session 01..05 are the primary identities.
- Each MAIN Vera lane renders `https://chatgpt.com/` inside an Electron browser guest.
- All Vera browser lanes use the same persistent Electron partition: `persist:vertex-vera-chatgpt`.
- The shared partition allows one ChatGPT account login to be reused by all Vera lanes inside Session Portal.
- Each Vera lane independently remembers its last ChatGPT URL/thread in the host-side localStorage.
- No external browser cookies are imported or copied.
- No ChatGPT DOM scraping, automated output extraction, or fake provider fallback is introduced.
- Empty AI Assistant configuration remains NO ASSISTANT.
- Existing Ollama / LM Studio / OpenAI API / Local model settings remain subordinate AI Assistant configuration.
- Search Vera remains separate.
- VCR/VCA remain untouched.
- Project Explorer Tree remains reserved for dedicated patch 000031.

## Login flow

1. Open Session Portal.
2. Vera 01 loads ChatGPT.
3. Sign in to the user's normal ChatGPT account inside the Vera browser.
4. Because all Vera lanes share the persistent browser partition, the account session is shared.
5. Vera 02..05 can then open separate ChatGPT threads while using the same logged-in account.

The account session is persisted by Electron under the app's user-data browser partition. Session Portal does not copy credentials from Edge, Chrome, or another external browser.

## Browser security boundary

The parent Electron window enables the webview tag only for the Vera bridge.

Before a guest is attached:
- initial source must be `https://chatgpt.com/`
- partition must be `persist:vertex-vera-chatgpt`
- guest preload is stripped
- Node integration is disabled
- context isolation, sandbox, and web security remain enabled
- insecure mixed content is disabled

Guest navigation is limited to HTTPS so normal ChatGPT authentication redirects can function without enabling local/file/javascript navigation.

## Migration note

`VeraSession` and the legacy provider agent code remain in the repository for rollback/migration safety, but active MAIN sessions are rendered by `VeraBrowserSession` after this patch.

No claim is made that ChatGPT internal Memory is synchronized by this patch. VCA/VCR/VMB Memory convergence and Memory Clock work are separate later stages.

Expected marker:

`VERTEX_SESSION_PORTAL_VERA_CHATGPT_BROWSER_BRIDGE_000033=PASS`
