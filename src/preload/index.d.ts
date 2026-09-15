import type { VertexPortalApi } from '../shared/contracts'

declare global {
  interface Window {
    vertexPortal: VertexPortalApi
  }
}

export {}
