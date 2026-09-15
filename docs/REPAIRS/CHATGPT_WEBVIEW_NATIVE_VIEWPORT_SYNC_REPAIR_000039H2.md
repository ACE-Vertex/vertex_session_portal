# CHATGPT WEBVIEW NATIVE VIEWPORT SYNC REPAIR 000039H2

Status: REPAIR / HUMAN_APPLY

## Ray evidence

Ray 000014 observed a resolvable CSS height chain through `MainFrame -> sessionViewport -> sessionTrack -> vera-browser-session -> .session -> .browserBody -> .chatgptView`.
The visible failure therefore cannot be explained by a missing source `height:100%` declaration alone. The user-visible symptom is consistent with the Electron `<webview>` guest viewport retaining a smaller native size while the host layout grows around it.

## Repair

This repair does not roll the UI back. It keeps the current layout and adds a runtime viewport ownership boundary inside `VeraBrowserSession`:

- observe `.browserBody` with `ResizeObserver`;
- schedule synchronization on the next animation frame;
- write the measured body width/height as exact pixel dimensions onto the Electron `<webview>` element;
- resynchronize on `dom-ready` and `did-stop-loading` through the existing ready path;
- disconnect observer/frame work before rerender or component disconnect;
- keep `.browserBody` explicitly at 100% width/height with zero minimum dimensions.

No ChatGPT DOM reading, `executeJavaScript`, account/session substitution, VCA mutation, Project Tree mutation, VRA Dispatch mutation, or layout redesign is introduced.

The intended invariant is:

`browserBody.getBoundingClientRect().height === webview host element height`

so Electron receives a concrete host resize whenever the Vera lane changes size.
