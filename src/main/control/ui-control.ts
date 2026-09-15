import type {
  BrowserWindow
} from 'electron'
import type {
  PortalControlCommand
} from '../../shared/contracts'
import {
  normalizePortalControlCommand
} from '../../shared/contracts'

export interface PortalControlDispatchEvidence {
  accepted: true
  type: PortalControlCommand['type']
  serializedBytes: number
}

/**
 * Main-process authority boundary for UI-only commands.
 *
 * This channel may guide the user's view, but it does not execute shell
 * commands, mutate project files, write VCR/VCA canonical data, or send
 * external messages.
 */
export function dispatchPortalControl(
  window: BrowserWindow,
  candidate: unknown
): PortalControlDispatchEvidence {
  if (window.isDestroyed()) {
    throw new Error(
      'PORTAL_CONTROL_WINDOW_DESTROYED'
    )
  }

  if (window.webContents.isDestroyed()) {
    throw new Error(
      'PORTAL_CONTROL_WEBCONTENTS_DESTROYED'
    )
  }

  const command =
    normalizePortalControlCommand(
      candidate
    )

  const serialized =
    JSON.stringify(command)

  window.webContents.send(
    'portal:control',
    serialized
  )

  return {
    accepted: true,
    type: command.type,
    serializedBytes: Buffer.byteLength(
      serialized,
      'utf8'
    )
  }
}
