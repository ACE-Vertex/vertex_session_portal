import {
  VxsNativeCapabilityRequest,
  VxsNativeExecutionResult,
  VxsNativeOrganProvider,
} from './vxs-native-organ-provider'

export interface VxsPowerShellFallbackResult {
  provider: 'powershell'
  ok: boolean
  blocked?: boolean
  reason?: string
  payload?: unknown
}

export type VxsPowerShellFallback = (
  request: VxsNativeCapabilityRequest,
) => Promise<VxsPowerShellFallbackResult>

export interface VxsResolvedCapabilityResult {
  route: 'NATIVE' | 'POWERSHELL' | 'BLOCKED'
  nativeProbeReason?: string
  result?: VxsNativeExecutionResult | VxsPowerShellFallbackResult
  reason?: string
}

export class VxsProviderResolver {
  private readonly nativeProvider: VxsNativeOrganProvider

  constructor(
    projectRoot: string,
    private readonly powerShellFallback: VxsPowerShellFallback,
  ) {
    this.nativeProvider = new VxsNativeOrganProvider(projectRoot)
  }

  async execute(
    request: VxsNativeCapabilityRequest,
  ): Promise<VxsResolvedCapabilityResult> {
    // Human-authority capabilities never auto-fall through this resolver.
    // Existing VXS Human Gate remains the authority for mutations.
    if (request.authority !== 'AUTO_SAFE') {
      return {
        route: 'BLOCKED',
        reason: 'HUMAN_APPLY_REQUIRED',
      }
    }

    const probe = this.nativeProvider.probe(request)

    if (probe.available) {
      const result = await this.nativeProvider.execute(request)
      if (result.ok) {
        return {
          route: 'NATIVE',
          nativeProbeReason: probe.reason,
          result,
        }
      }

      // Read-only native failures may fall back to the PowerShell provider.
      const fallbackResult = await this.powerShellFallback(request)
      return {
        route: 'POWERSHELL',
        nativeProbeReason: 'NATIVE_RUNTIME_FAILURE',
        result: fallbackResult,
      }
    }

    const fallbackResult = await this.powerShellFallback(request)
    return {
      route: 'POWERSHELL',
      nativeProbeReason: probe.reason,
      result: fallbackResult,
    }
  }
}

export interface VxsProviderExecutionPlan {
  route: 'NATIVE' | 'POWERSHELL'
  program: string
  args: string[]
  providerId: string
  reason: string
}

export function planVxsProviderExecution(
  projectRoot: string,
  request: VxsNativeCapabilityRequest,
  powerShellProgram: string,
  powerShellCommand: string,
): VxsProviderExecutionPlan {
  if (request.authority !== 'AUTO_SAFE') {
    throw new Error('HUMAN_APPLY_REQUIRED')
  }

  const nativeProvider = new VxsNativeOrganProvider(projectRoot)
  const nativePlan = nativeProvider.plan(request)

  if (nativePlan) {
    return {
      route: 'NATIVE',
      program: nativePlan.program,
      args: nativePlan.args,
      providerId: nativePlan.providerId,
      reason: 'NATIVE_PROVIDER_AVAILABLE',
    }
  }

  return {
    route: 'POWERSHELL',
    program: powerShellProgram,
    args: ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', powerShellCommand],
    providerId: 'powershell',
    reason: 'NATIVE_PROVIDER_UNAVAILABLE',
  }
}
