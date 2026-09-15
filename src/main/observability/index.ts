import { app } from 'electron'
import { vertexObservability } from './vertex-observability-core'
import { startDispatchCorrelationObserver } from './dispatch-correlation-observer'

let activationRequested = false

export function activateVertexObservabilityCore(): void {
  if (activationRequested) return
  activationRequested = true

  void app.whenReady().then(() => {
    vertexObservability.start()
    startDispatchCorrelationObserver()
  })
}

activateVertexObservabilityCore()
