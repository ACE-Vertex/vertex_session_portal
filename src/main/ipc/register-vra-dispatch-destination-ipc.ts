import { ipcMain } from 'electron'
import {
  chooseVraDispatchDestination,
  getVraDispatchDestinationState
} from '../vra/vra-dispatch-destination-store'

const GET_CHANNEL = 'vertex:vra-dispatch-destination:get'
const CHOOSE_CHANNEL = 'vertex:vra-dispatch-destination:choose'

export function registerVraDispatchDestinationIpc(): void {
  ipcMain.removeHandler(GET_CHANNEL)
  ipcMain.removeHandler(CHOOSE_CHANNEL)

  ipcMain.handle(GET_CHANNEL, () => getVraDispatchDestinationState())
  ipcMain.handle(CHOOSE_CHANNEL, () => chooseVraDispatchDestination())
}
