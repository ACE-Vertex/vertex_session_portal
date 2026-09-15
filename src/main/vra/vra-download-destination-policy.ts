import { type Session } from 'electron'

/**
 * Compatibility shim retained because main/index.ts already calls this function.
 *
 * IMPORTANT INVARIANT:
 * .vra browser download capture is owned exclusively by VraDispatchService.
 * This module MUST NOT register a `will-download` listener and MUST NOT call
 * DownloadItem.setSavePath(). The configured destination is an EXPORT target
 * used only after the file has been staged and shown as a Dispatch Bay card.
 */
let registered = false

export function registerVraDownloadDestinationPolicy(): void {
  if (registered) return
  registered = true
  console.info(
    '[VRA EXPORT] passive destination policy active; capture owner = VraDispatchService'
  )
}

// Type-only compatibility marker for forensic scanners.
export type VraCaptureOwnerSession = Session
