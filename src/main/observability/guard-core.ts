import * as path from 'node:path'
import type { GuardDecision, GuardRequest } from './contracts'

function normalize(input: string): string {
  const resolved = path.resolve(input)
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved
}

function inside(root: string, candidate: string): boolean {
  const relative = path.relative(normalize(root), normalize(candidate))
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

export class GuardCore {
  private readonly roots: string[]

  constructor(allowedRoots: string[]) {
    this.roots = allowedRoots.map(root => path.resolve(root))
  }

  evaluate(request: GuardRequest): GuardDecision {
    const reasons: string[] = []
    const mutation = request.operations.some(operation => operation.kind === 'write' || operation.kind === 'delete')
    const execution = request.operations.some(operation => operation.kind === 'exec')

    if (request.mode === 'RAY' && (mutation || execution)) {
      reasons.push('RAY_READ_ONLY_VIOLATION')
    }

    if (request.mode === 'VERIFY' && mutation) {
      reasons.push('VERIFY_SOURCE_MUTATION_FORBIDDEN')
    }

    if ((request.mode === 'APPLY' || request.mode === 'RECOVERY') && mutation) {
      if (request.authority !== 'HUMAN_APPLY') reasons.push('HUMAN_APPLY_AUTHORITY_REQUIRED')
      if (request.humanApproval !== 'APPROVED') reasons.push('HUMAN_APPROVAL_REQUIRED')
    }

    for (const operation of request.operations) {
      if (!operation.path) continue
      const candidate = path.resolve(operation.path)
      if (!this.roots.some(root => inside(root, candidate))) {
        reasons.push(`PATH_OUTSIDE_ALLOWED_ROOT:${candidate}`)
      }
    }

    return { allowed: reasons.length === 0, reasons }
  }
}
