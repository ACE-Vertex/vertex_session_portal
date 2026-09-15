# VERTEX SESSION PORTAL - INITIAL WINDOW SIZE 3200 x 1300 000040

## Purpose
Set the normal startup size of the main Electron BrowserWindow to 3200 x 1300 pixels.

## Contract
- Startup width: 3200
- Startup height: 1300
- Existing minimum size remains 1100 x 720
- No maximize/fullscreen behavior is introduced
- Existing ChatGPT persistent partition, Workspace Tree, VRA Dispatch, VCA/VCR, and lane behavior remain untouched

The operating system may still constrain the resulting on-screen size when the available work area is smaller than the requested startup size.
