# Vertex Session Portal — ChatGPT WebView Flow Height Repair 000039H1

## Symptom

After 000039/000040, the ChatGPT composer appears near the top of each Vera lane while the lower browser area stays black. The outer `browserBody` still occupies the full lane height, but the embedded Electron `<webview>` guest viewport behaves as if it only received a short/default height.

## Root cause

000039 repaired a lower white fallback line by moving `.chatgptView` to `position:absolute; inset:0`. That removed the webview from normal layout flow. For ordinary HTML this still visually fills the parent, but Electron's `<webview>` uses its element layout bounds to size the guest `WebContents`. On this runtime/window geometry, the absolutely positioned host can retain a short guest viewport even while the surrounding black browser body remains full-height.

## Repair

Keep the black backing and fractional-rounding guard introduced by 000039, but return the `<webview>` to normal layout flow:

- `.browserBody` becomes a flex container.
- `.chatgptView` uses `position:relative` rather than absolute positioning.
- `.chatgptView` receives `flex:1 1 auto`, `align-self:stretch`, `width:100%`, and `height:100%`.
- Black backing, `line-height:0`, zero border, and bottom black inset remain, so the original white-line repair is preserved without sacrificing guest viewport height.

## Boundaries preserved

- Vera lane 600px base/minimum and drag-width behavior remain unchanged.
- Active-window neon remains unchanged.
- ChatGPT persistent partition/session logic remains unchanged.
- VCA Thread Bridge / Memory Inbox / Curator remain unchanged.
- Project Tree and VRA / Works Dispatch Lane remain unchanged.
- 3200x1300 initial BrowserWindow sizing from 000040 remains unchanged.
- No ChatGPT DOM scraping or script injection is introduced.
