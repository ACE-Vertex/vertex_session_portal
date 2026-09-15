# CHATGPT WEBVIEW NATIVE FLEX CONSOLIDATION 000039H4H1

This is the validation repair for 000039H4.

000039H4 was rejected at the Works VALIDATE phase before staging or applying because
`npm.cmd` is not an allowed manifest verification program.

Therefore H4H1 includes the full intended H4 runtime payload again:
- VeraBrowserSession.ts with the H2 manual ResizeObserver/pixel-sizing workaround retired
- VeraBrowserSession.css preserving Electron-native `display:flex`
- a single Python verifier

The Python verifier performs static contract checks and then invokes `npm.cmd run build`
internally using raw-byte capture, so Works sees only the allowed `python` verification
program and Python does not decode build output with cp932.

Basis: Vertex Ray 000015 live runtime geometry showed the host height chain and webview
element were already resolving to full browserBody height. This repair therefore keeps
native Electron webview flex sizing and removes the manual JS pixel-sizing workaround.
