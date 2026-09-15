import { ipcMain } from 'electron'
import { FirmwareRegistrar, type FirmwareRegistrarResult } from '../firmware/FirmwareRegistrar'
import { SystemPolicyRegistrar } from '../firmware/SystemPolicyRegistrar'
import { configureSystemPolicyResolverProvider } from '../../shared/system-policy-registry'

export const FIRMWARE_REGISTRAR_CHANNEL = 'firmware:submit-change-decision'

let registered = false
let registrar: FirmwareRegistrar | null = null

export function registerFirmwareRegistrarIpc(): void {
  if (registered) return
  registrar ??= new FirmwareRegistrar()

  ipcMain.handle(
    FIRMWARE_REGISTRAR_CHANNEL,
    async (_event, request: unknown): Promise<FirmwareRegistrarResult> => {
      return registrar!.register(request)
    }
  )

  registered = true
}


const __vertexSystemPolicyRegistrar = new SystemPolicyRegistrar()


configureSystemPolicyResolverProvider({
  resolveActiveSystemPolicy: (policyId) => __vertexSystemPolicyRegistrar.readActivePolicy(policyId),
  listActiveSystemPolicies: () => __vertexSystemPolicyRegistrar.listActivePolicies()
})
ipcMain.handle('vertex:system-policy-decision', async (_event, decision: unknown) => {
  return __vertexSystemPolicyRegistrar.submitDecision(decision)
})

ipcMain.handle('vertex:system-policy-read-active', async (_event, target: string) => {
  return __vertexSystemPolicyRegistrar.readActivePolicy(target)
})
