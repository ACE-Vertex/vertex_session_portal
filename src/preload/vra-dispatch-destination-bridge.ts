import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('vertexDispatchDestination', {
  get: () => ipcRenderer.invoke('vertex:vra-dispatch-destination:get'),
  choose: () => ipcRenderer.invoke('vertex:vra-dispatch-destination:choose')
})
