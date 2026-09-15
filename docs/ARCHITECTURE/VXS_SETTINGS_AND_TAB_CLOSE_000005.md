# VXS Settings + Tab Close 000005

Target:
- Vertex Session Portal embedded VXS

Scope:
- Extend current verified `vertex-shell-service.ts`
- Do NOT replace the current `vertex-shell-host-bridge.ts`

Features:

1. Settings gear
   - Replaces the old upper-right collapse glyph at runtime.
   - Hover opens the settings popover.
   - Click pins/unpins the popover.

2. Editor Display Mode
   - Default Mode:
     - White = Standard / Info
     - Green = Success / Ready
     - Orange = Warning / Caution
     - Red = Error / Failed
   - OLD Mode:
     - Green = Default text
     - Red = Error only
   - Selection persists in localStorage.

3. Font Size
   - 9 px to 20 px.
   - Applies immediately to terminal output, CWD, command input, and VXS prompt.
   - Persists in localStorage.

4. Shell tab close affordance
   - Adds `×` at the right side of each Shell tab.
   - Closing the active tab activates an adjacent tab first.
   - Closing the last visible tab creates a fresh tab so VXS stays usable.
   - A running/busy tab cannot be closed.
   - Closed tabs are suppressed for the current VXS runtime.

Preserved:
- VXS 0.1.0
- `vxs --version`
- `VXS_META`
- Vertex eXecution Shell window title
- existing host bridge production source
- Workstation Lane Allocation Authority
- Human Gate / HUMAN_APPLY
- VRA `vra/1`
- existing command execution and Evidence behavior
