import type {
  PortalControlCommand
} from '../../../shared/contracts'
import {
  parsePortalControlCommandJson
} from '../../../shared/contracts'

export type { PortalControlCommand }

type Listener = (
  command: PortalControlCommand
) => void

class PortalControlChannel {
  private readonly listeners = new Set<Listener>()

  subscribe(
    listener: Listener
  ): () => void {
    this.listeners.add(listener)

    return () => {
      this.listeners.delete(listener)
    }
  }

  dispatch(
    command: PortalControlCommand
  ): void {
    for (const listener of this.listeners) {
      listener(command)
    }
  }

  dispatchSerialized(
    serializedCommand: string
  ): void {
    this.dispatch(
      parsePortalControlCommandJson(
        serializedCommand
      )
    )
  }
}

export const portalControl =
  new PortalControlChannel()
