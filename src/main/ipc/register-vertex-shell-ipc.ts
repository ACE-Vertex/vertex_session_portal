// VRA_VXS_DIRECT_HTTP_NERVE_000089V4_IMPORT
import { registerVeraVxsVraDirectHttpNerve } from '../shell/vxs/vera-vxs-vra-direct-http-nerve'
import { ipcMain } from 'electron'
import type {
  VertexShellCommandRequest,
  VertexShellSetCwdRequest,
  VertexShellStreamEvent
} from '../../shared/vertex-shell-contracts'
import { VertexShellService } from '../shell/vertex-shell-service'

export function registerVertexShellIpc(
  service: VertexShellService
): void {
  ipcMain.removeHandler('vertex-shell:state')
  ipcMain.removeHandler('vertex-shell:execute')
  ipcMain.removeHandler('vertex-shell:stop')
  ipcMain.removeHandler('vertex-shell:set-cwd')

  ipcMain.handle(
    'vertex-shell:state',
    () => service.state()
  )

  ipcMain.handle(
    'vertex-shell:set-cwd',
    (_event, request: VertexShellSetCwdRequest) =>
      service.setCwd(request)
  )

  ipcMain.handle(
    'vertex-shell:stop',
    () => service.stop()
  )

  // VERA_VXS_PRODUCTION_IPC_000088V4_REGISTER
  registerVeraVxsProductionIpc(service)
  // VRA_VXS_DIRECT_HTTP_NERVE_000089V4_REGISTER
  registerVeraVxsVraDirectHttpNerve(service)
  ipcMain.handle(
    'vertex-shell:execute',
    async (event, request: VertexShellCommandRequest) => {
      const sender = event.sender
      return service.execute(
        request,
        (streamEvent: VertexShellStreamEvent) => {
          if (!sender.isDestroyed()) {
            sender.send('vertex-shell:output', streamEvent)
          }
        }
      )
    }
  )
}

// VERA_VXS_PRODUCTION_IPC_000088V4_BEGIN
export function registerVeraVxsProductionIpc(service: VertexShellService): void {
  ipcMain.removeHandler('vera-vxs:execute')
  ipcMain.handle('vera-vxs:execute', async (_event, request: unknown) => {
    const module = await import('../shell/vxs/vera-vxs-interface')
    return module.executeVeraVxsRequest(service, request as any)
  })
}
// VERA_VXS_PRODUCTION_IPC_000088V4_END
