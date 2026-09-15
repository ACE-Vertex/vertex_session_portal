# VXS Clipboard Ownership Repair 000029

## Observed failure

The visible VXS terminal is canonical (`VXS │` / `VXS ›`), but clicking the
shell `COPY` button can still place a legacy `VSH` transcript on the clipboard.

The previous 000027 repair preserved the legacy COPY handler and added a second
bubble-stage clipboard write. That leaves two writers active for one click.
Because clipboard writes are asynchronous, the legacy writer can win and
recreate the Presentation / Clipboard divergence.

## Repair

Only the VXS transcript `COPY` button changes ownership.

The VXS runtime now:

1. observes the click during the ShadowRoot capture phase
2. confirms the exact button label is `COPY`
3. reads the visible output
4. canonicalizes it through the existing VXS normalizer
5. calls `preventDefault()` and `stopImmediatePropagation()`
6. writes the canonical transcript once

The legacy Host COPY handler therefore cannot perform a second write.

## Scope preserved

- VXS 0.1.0
- PowerShell compatibility backend
- VXS command registry / capability packs
- settings / tabs / editor display
- Explorer `COPY PATH`
- Human Gate / HUMAN_APPLY
- Observation / Return Bus
- ACK lifecycle
- VRA routing
- Workstation lane authority
- build-before-launch guard 000028H1

No Host Bridge replacement is performed.

## Baseline

Expected service baseline from 000027:

`e0bbba6057097005857527953a8470f5dde41cf876ac6a5bb16737d327f66b2e`

Patched service SHA256:

`f227c2a168fa79b97e8abdc3bc6cf67c4bc8cd957e95b171068f6c7b5f8f899c`

After APPLY, close the running Session Portal and launch with
`VERTEX_SESSION_PORTAL_CURRENT.cmd` so the current source is rebuilt before
Electron starts.
