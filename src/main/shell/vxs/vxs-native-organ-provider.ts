import { spawn } from 'child_process'
import { createHash } from 'crypto'
import { existsSync, readFileSync } from 'fs'
import { isAbsolute, join } from 'path'

export type VxsNativeAuthority = 'AUTO_SAFE' | 'HUMAN_APPLY'

export interface VxsNativeCapabilityRequest {
  resource: string
  action: string
  target?: string
  authority: VxsNativeAuthority
}

export interface VxsNativeProviderDescriptor {
  schema: 'vertex-vxs/native-provider-binding-1'
  provider_id: string
  state: string
  binary: {
    path: string
    sha256: string
  }
  authority: {
    default: VxsNativeAuthority
    allowed: VxsNativeAuthority[]
    human_apply_required_for_mutation: boolean
  }
  side_effect_policy: string
  capabilities: Record<string, string[]>
  routing: {
    priority: string
    fallback: string
    fallback_status: string
  }
}

export interface VxsNativeExecutionResult {
  provider: 'native'
  providerId: string
  ok: boolean
  exitCode: number
  stdout: string
  stderr: string
  payload?: unknown
}

export interface VxsNativeProbeResult {
  available: boolean
  reason:
    | 'AVAILABLE'
    | 'DESCRIPTOR_MISSING'
    | 'DESCRIPTOR_INVALID'
    | 'BINARY_MISSING'
    | 'BINARY_HASH_MISMATCH'
    | 'CAPABILITY_UNSUPPORTED'
    | 'AUTHORITY_NOT_ALLOWED'
  descriptor?: VxsNativeProviderDescriptor
  binaryPath?: string
}

const DESCRIPTOR_RELATIVE_PATH =
  'runtime/vxs/native/providers/vxs-native-observer.json'

function sha256File(path: string): string {
  return createHash('sha256').update(readFileSync(path)).digest('hex')
}

function normalizeResource(resource: string): string {
  return resource.trim().toLowerCase()
}

function normalizeAction(action: string): string {
  return action.trim().toLowerCase()
}

function mapInvocation(
  request: VxsNativeCapabilityRequest,
): string[] | null {
  const resource = request.resource.trim().toUpperCase()
  const action = request.action.trim().toUpperCase()

  if (resource === 'SYSTEM' && action === 'OBSERVE') {
    return ['system']
  }

  if (resource === 'FILESYSTEM') {
    if (!request.target) return null

    if (action === 'TEST' || action === 'EXISTS') {
      return ['fs-exists', request.target]
    }
    if (action === 'OBSERVE' || action === 'METADATA') {
      return ['fs-meta', request.target]
    }
    if (action === 'FIND' || action === 'LIST') {
      return ['fs-list', request.target]
    }
  }

  return null
}

export class VxsNativeOrganProvider {
  constructor(private readonly projectRoot: string) {}

  private descriptorPath(): string {
    return join(this.projectRoot, DESCRIPTOR_RELATIVE_PATH)
  }

  probe(request: VxsNativeCapabilityRequest): VxsNativeProbeResult {
    const descriptorPath = this.descriptorPath()
    if (!existsSync(descriptorPath)) {
      return { available: false, reason: 'DESCRIPTOR_MISSING' }
    }

    let descriptor: VxsNativeProviderDescriptor
    try {
      descriptor = JSON.parse(
        readFileSync(descriptorPath, 'utf8'),
      ) as VxsNativeProviderDescriptor
    } catch {
      return { available: false, reason: 'DESCRIPTOR_INVALID' }
    }

    if (
      descriptor.schema !== 'vertex-vxs/native-provider-binding-1' ||
      descriptor.provider_id !== 'vxs-native-observer'
    ) {
      return { available: false, reason: 'DESCRIPTOR_INVALID' }
    }

    if (!descriptor.authority.allowed.includes(request.authority)) {
      return {
        available: false,
        reason: 'AUTHORITY_NOT_ALLOWED',
        descriptor,
      }
    }

    const resourceKey = normalizeResource(request.resource)
    const actionKey = normalizeAction(request.action)
    const declared = descriptor.capabilities[resourceKey] ?? []

    const invocation = mapInvocation(request)
    const declaredAlias =
      resourceKey === 'system' && actionKey === 'observe'
        ? 'observe'
        : resourceKey === 'filesystem' &&
            (actionKey === 'test' || actionKey === 'exists')
          ? 'exists'
          : resourceKey === 'filesystem' &&
              (actionKey === 'observe' || actionKey === 'metadata')
            ? 'metadata'
            : resourceKey === 'filesystem' &&
                (actionKey === 'find' || actionKey === 'list')
              ? 'list'
              : ''

    if (!invocation || !declaredAlias || !declared.includes(declaredAlias)) {
      return {
        available: false,
        reason: 'CAPABILITY_UNSUPPORTED',
        descriptor,
      }
    }

    const descriptorBinary = descriptor.binary.path
    const binaryPath = isAbsolute(descriptorBinary)
      ? descriptorBinary
      : join(this.projectRoot, descriptorBinary)

    if (!existsSync(binaryPath)) {
      return {
        available: false,
        reason: 'BINARY_MISSING',
        descriptor,
        binaryPath,
      }
    }

    const actualSha256 = sha256File(binaryPath)
    if (actualSha256 !== descriptor.binary.sha256.toLowerCase()) {
      return {
        available: false,
        reason: 'BINARY_HASH_MISMATCH',
        descriptor,
        binaryPath,
      }
    }

    return {
      available: true,
      reason: 'AVAILABLE',
      descriptor,
      binaryPath,
    }
  }

  plan(request: VxsNativeCapabilityRequest): {
    providerId: string
    program: string
    args: string[]
  } | null {
    const probe = this.probe(request)
    if (!probe.available || !probe.binaryPath || !probe.descriptor) {
      return null
    }

    const args = mapInvocation(request)
    if (!args) {
      return null
    }

    return {
      providerId: probe.descriptor.provider_id,
      program: probe.binaryPath,
      args,
    }
  }

  execute(
    request: VxsNativeCapabilityRequest,
  ): Promise<VxsNativeExecutionResult> {
    const probe = this.probe(request)
    if (!probe.available || !probe.binaryPath || !probe.descriptor) {
      return Promise.reject(
        new Error(`Native provider unavailable: ${probe.reason}`),
      )
    }

    const args = mapInvocation(request)
    if (!args) {
      return Promise.reject(
        new Error('Native capability invocation is unsupported'),
      )
    }

    return new Promise((resolve, reject) => {
      const child = spawn(probe.binaryPath as string, args, {
        cwd: this.projectRoot,
        shell: false,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      })

      let stdout = ''
      let stderr = ''

      child.stdout.setEncoding('utf8')
      child.stderr.setEncoding('utf8')
      child.stdout.on('data', (chunk: string) => {
        stdout += chunk
      })
      child.stderr.on('data', (chunk: string) => {
        stderr += chunk
      })
      child.on('error', reject)
      child.on('close', (code) => {
        const exitCode = code ?? -1
        let payload: unknown
        if (stdout.trim()) {
          try {
            const lines = stdout.trim().split(/\r?\n/)
            payload = JSON.parse(lines[lines.length - 1])
          } catch {
            payload = undefined
          }
        }

        resolve({
          provider: 'native',
          providerId: probe.descriptor?.provider_id ?? 'unknown',
          ok: exitCode === 0,
          exitCode,
          stdout,
          stderr,
          payload,
        })
      })
    })
  }
}
