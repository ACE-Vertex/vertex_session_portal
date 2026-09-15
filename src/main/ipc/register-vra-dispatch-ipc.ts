import { BrowserWindow, clipboard, ipcMain, screen } from 'electron'
import { listVertexContracts, resolveVertexContract, type VertexContractId } from '../../shared/vertex-contract-catalog'
import type {
  RegisterVraWebviewSourceRequest,
  PortalWindowFitRequest,
  PortalWindowFitResult,
  VraDispatchCard,
  VraDispatchState,
  VraEvidenceDeliveryAckRequest,
  VraEvidenceDeliveryAckResult,
  WorkstationSafetyActionRequest,
  WorkstationSafetyActionResult,
  WorkstationSafetyObservation,
  WorkstationServerProcessState
} from '../../shared/contracts'
import { VraDispatchService } from '../vra/vra-dispatch-service'
import { workstationProcessController } from '../workstation/workstation-process-controller'
import { registerFirmwareRegistrarIpc } from './register-firmware-registrar-ipc'

export function registerVraDispatchIpc(service: VraDispatchService): void {
  // VERTEX_CONTRACT_CATALOG_API_000036V2: read-only canonical system-contract catalog.
  ipcMain.removeHandler('vertex:contract-resolve')
  ipcMain.removeHandler('vertex:contract-list')
  registerFirmwareRegistrarIpc()

  ipcMain.handle('vertex:contract-resolve', (_event, id: VertexContractId) => resolveVertexContract(id))
  ipcMain.handle('vertex:contract-list', () => listVertexContracts())
  ipcMain.removeHandler('workstation:vra-dispatch-state')
  ipcMain.removeHandler('workstation:vra-register-webview-source')
  ipcMain.removeHandler('workstation:vra-dispatch-card')
  ipcMain.removeHandler('workstation:vra-export-card')
  ipcMain.removeHandler('workstation:vra-remove-card')
  ipcMain.removeHandler('workstation:vra-evidence-ack')
  ipcMain.removeHandler('workstation:safety-state')
  ipcMain.removeHandler('workstation:safety-action')
  ipcMain.removeHandler('workstation:server-process-state')
  ipcMain.removeHandler('workstation:server-start')
  ipcMain.removeHandler('portal:main-window-fit')
  ipcMain.removeHandler('portal:clipboard-read-text')

  ipcMain.handle(
    'workstation:vra-dispatch-state',
    async (): Promise<VraDispatchState> => service.refreshState()
  )

  ipcMain.handle(
    'workstation:vra-register-webview-source',
    (_event, request: RegisterVraWebviewSourceRequest): void => {
      service.registerWebviewSource(request)
    }
  )

  ipcMain.handle(
    'workstation:vra-export-card',
    (_event, cardId: string): string => service.exportCard(cardId)
  )

  ipcMain.handle(
    'workstation:vra-dispatch-card',
    (_event, cardId: string): VraDispatchCard => service.dispatch(cardId)
  )

  ipcMain.handle(
    'workstation:vra-remove-card',
    (_event, cardId: string): VraDispatchState => service.remove(cardId)
  )

  ipcMain.handle(
    'workstation:vra-evidence-ack',
    async (_event, request: VraEvidenceDeliveryAckRequest): Promise<VraEvidenceDeliveryAckResult> =>
      service.acknowledgeEvidenceDelivery(request)
  )

  ipcMain.handle(
    'workstation:safety-state',
    async (): Promise<WorkstationSafetyObservation> => service.getWorkstationSafety()
  )

  ipcMain.handle(
    'workstation:safety-action',
    async (_event, request: WorkstationSafetyActionRequest): Promise<WorkstationSafetyActionResult> =>
      service.performWorkstationSafetyAction(request)
  )

  ipcMain.handle(
    'workstation:server-process-state',
    async (): Promise<WorkstationServerProcessState> =>
      workstationProcessController.state()
  )

  ipcMain.handle(
    'workstation:server-start',
    async (): Promise<WorkstationServerProcessState> =>
      workstationProcessController.start()
  )

  ipcMain.handle(
    'portal:main-window-fit',
    (event, request: PortalWindowFitRequest): PortalWindowFitResult => {
      const win = BrowserWindow.fromWebContents(event.sender)
      if (!win || win.isDestroyed()) {
        throw new Error('PORTAL_MAIN_WINDOW_NOT_FOUND')
      }

      if (!request || (request.reason !== 'BOOTSTRAP' && request.reason !== 'VERA_LAYOUT')) {
        throw new Error('PORTAL_MAIN_WINDOW_FIT_REASON_INVALID')
      }

      const requestedContentWidth = Math.round(Number(request.contentWidth))
      const requestedContentHeight = Math.round(Number(request.contentHeight))

      if (
        !Number.isFinite(requestedContentWidth) ||
        !Number.isFinite(requestedContentHeight)
      ) {
        throw new Error('PORTAL_MAIN_WINDOW_FIT_SIZE_INVALID')
      }

      const currentBounds = win.getBounds()
      const display = screen.getDisplayMatching(currentBounds)
      const workArea = display.workArea

      // Never override a Human-selected maximized/fullscreen state.
      if (win.isMaximized() || win.isFullScreen()) {
        return {
          applied: false,
          reason: request.reason,
          width: currentBounds.width,
          height: currentBounds.height,
          x: currentBounds.x,
          y: currentBounds.y,
          workAreaWidth: workArea.width,
          workAreaHeight: workArea.height,
          skippedReason: 'MAXIMIZED_OR_FULLSCREEN'
        }
      }

      const contentBounds = win.getContentBounds()
      const frameWidth = Math.max(0, currentBounds.width - contentBounds.width)
      const frameHeight = Math.max(0, currentBounds.height - contentBounds.height)
      const [minWidth, minHeight] = win.getMinimumSize()
      const [configuredMaxWidth, configuredMaxHeight] = win.getMaximumSize()

      // Renderer provides size only; target window and position remain main-process authority.
      const boundedContentWidth = Math.max(
        320,
        Math.min(requestedContentWidth, 20_000)
      )
      const boundedContentHeight = Math.max(
        240,
        Math.min(requestedContentHeight, 12_000)
      )

      const maxWidth = Math.min(
        workArea.width,
        configuredMaxWidth > 0 ? configuredMaxWidth : workArea.width
      )
      const maxHeight = Math.min(
        workArea.height,
        configuredMaxHeight > 0 ? configuredMaxHeight : workArea.height
      )

      const width = Math.max(
        Math.min(minWidth, maxWidth),
        Math.min(boundedContentWidth + frameWidth, maxWidth)
      )
      const height = Math.max(
        Math.min(minHeight, maxHeight),
        Math.min(boundedContentHeight + frameHeight, maxHeight)
      )

      const maxX = workArea.x + workArea.width - width
      const maxY = workArea.y + workArea.height - height
      const x = Math.min(Math.max(currentBounds.x, workArea.x), maxX)
      const y = Math.min(Math.max(currentBounds.y, workArea.y), maxY)

      const changed =
        currentBounds.width !== width ||
        currentBounds.height !== height ||
        currentBounds.x !== x ||
        currentBounds.y !== y

      if (changed) {
        win.setBounds({ x, y, width, height }, true)
      }

      return {
        applied: changed,
        reason: request.reason,
        width,
        height,
        x,
        y,
        workAreaWidth: workArea.width,
        workAreaHeight: workArea.height,
        skippedReason: null
      }
    }
  )

  ipcMain.handle(
    'portal:clipboard-read-text',
    async (): Promise<string> => await clipboard.readText()
  )
}
