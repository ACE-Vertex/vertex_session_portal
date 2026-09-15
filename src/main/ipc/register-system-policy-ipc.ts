import { ipcMain } from 'electron'
import {
  listActiveSystemPolicies,
  resolveActiveSystemPolicy
} from '../../shared/system-policy-registry'

// VERTEX_SYSTEM_POLICY_RESOLVER_000062V2
export function registerSystemPolicyIpc(): void {
  ipcMain.handle('vertex:system-policy-resolve', (_event, policyId: unknown) => {
    if (typeof policyId !== 'string' || policyId.trim().length === 0) return null
    return resolveActiveSystemPolicy(policyId.trim())
  })

  ipcMain.handle('vertex:system-policy-list', () => listActiveSystemPolicies())
}
