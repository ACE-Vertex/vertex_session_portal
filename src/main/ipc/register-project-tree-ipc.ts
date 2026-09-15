import {
  ipcMain
} from 'electron'
import {
  ProjectTreeService
} from '../project/project-tree-service'

export function registerProjectTreeIpc(service: ProjectTreeService): void {
  ipcMain.handle(
    'project-tree:list',
    (_event, path?: string) => service.list(path)
  )

  ipcMain.handle(
    'project-tree:resolve',
    (_event, path: string) => service.resolve(path)
  )

  ipcMain.handle(
    'project-tree:open',
    async (_event, path: string) => service.open(path)
  )

  ipcMain.handle(
    'project-tree:reveal',
    (_event, path: string) => service.reveal(path)
  )

  ipcMain.handle(
    'project-tree:copy-path',
    (_event, path: string) => service.copy(path)
  )
}
