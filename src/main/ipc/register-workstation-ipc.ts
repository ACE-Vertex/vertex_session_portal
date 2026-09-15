import { ipcMain } from 'electron'
import type {
  AppendSessionMessageRequest,
  CreateVirtualArdHandoffRequest,
  ProjectVirtualArdRequest,
  SidebarTab,
  UpsertVcrEntryRequest,
  AppendVcaMemoryEventRequest,
  AppendVcaWeightRevisionRequest,
  RunVcaCuratorRequest,
  SaveVcaCuratorSettingsRequest,
  EnqueueVcaInboxRequest,
  UpdateVeraSessionThreadRequest
} from '../../shared/contracts'
import { WorkstationDb } from '../storage/workstation-db'
import { VcaCuratorService } from '../memory/vca-curator-service'

export function registerWorkstationIpc(
  db: WorkstationDb,
  curator: VcaCuratorService
): void {
  ipcMain.handle(
    'workstation:bootstrap',
    () =>
      db.getBootstrapState()
  )

  ipcMain.handle(
    'workstation:set-priority-session',
    (
      _event,
      sessionId: string
    ) =>
      db.setPrioritySession(
        sessionId
      )
  )

  ipcMain.handle(
    'workstation:activate-next-main-lane',
    () => db.activateNextMainLane()
  )

  ipcMain.handle(
    'workstation:set-sidebar-tab',
    (
      _event,
      tab: SidebarTab
    ) =>
      db.setSidebarTab(tab)
  )

  ipcMain.handle(
    'workstation:project-virtual-ard',
    (
      _event,
      request:
        ProjectVirtualArdRequest
    ) =>
      db.projectVirtualArd(
        request
      )
  )

  ipcMain.handle(
    'workstation:append-session-message',
    (
      _event,
      request:
        AppendSessionMessageRequest
    ) =>
      db.appendSessionMessage(
        request
      )
  )

  ipcMain.handle(
    'workstation:create-virtual-ard-handoff',
    (
      _event,
      request:
        CreateVirtualArdHandoffRequest
    ) =>
      db.createVirtualArdHandoff(
        request
      )
  )

  ipcMain.handle(
    'workstation:get-virtual-ard-state',
    (
      _event,
      missionId?: string
    ) =>
      db.getVirtualArdState(
        missionId
      )
  )


ipcMain.handle(
  'workstation:storage-status',
  () => db.storageStatus()
)

ipcMain.handle(
  'workstation:vcr-search',
  (_event, query?: string) => db.searchVcr(query ?? '')
)

ipcMain.handle(
  'workstation:vcr-upsert',
  (_event, request: UpsertVcrEntryRequest) => db.upsertVcrEntry(request)
)

ipcMain.handle(
  'workstation:vca-search',
  (_event, query?: string) => db.searchVca(query ?? '')
)

ipcMain.handle(
  'workstation:vca-memory-append',
  (_event, request: AppendVcaMemoryEventRequest) => {
    const record = db.appendVcaMemoryEvent(request)
    curator.schedule('MEMORY_APPEND')
    return record
  }
)

ipcMain.handle(
  'workstation:vca-weight-append',
  (_event, request: AppendVcaWeightRevisionRequest) => db.appendVcaWeightRevision(request)
)

ipcMain.handle(
  'workstation:vca-memory-clock',
  () => db.getVcaMemoryClockState()
)

ipcMain.handle(
  'workstation:vca-compensation',
  (_event, sessionId: string, limit?: number) => db.getVcaCompensation(sessionId, limit)
)

ipcMain.handle(
  'workstation:vca-compensation-ack',
  (_event, sessionId: string, throughRevision: number) => db.acknowledgeVcaCompensation(sessionId, throughRevision)
)

ipcMain.handle(
  'workstation:vca-curator-state',
  () => curator.state()
)

ipcMain.handle(
  'workstation:vca-curator-save-settings',
  (_event, request: SaveVcaCuratorSettingsRequest) => curator.saveSettings(request)
)

ipcMain.handle(
  'workstation:vca-curator-run',
  (_event, request?: RunVcaCuratorRequest) => curator.run(request)
)


ipcMain.handle(
  'workstation:vera-thread-bindings',
  () => db.getVeraSessionThreadBindings()
)

ipcMain.handle(
  'workstation:vera-thread-update',
  (_event, request: UpdateVeraSessionThreadRequest) => db.updateVeraSessionThread(request)
)

ipcMain.handle(
  'workstation:vca-inbox',
  () => db.getVcaInbox()
)

ipcMain.handle(
  'workstation:vca-inbox-enqueue',
  (_event, request: EnqueueVcaInboxRequest) => {
    const result = db.enqueueVcaInbox(request)
    if (!result.duplicate) curator.schedule('VCA_INBOX_ENQUEUE')
    return result
  }
)
}
