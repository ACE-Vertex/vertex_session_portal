import * as path from 'node:path'
import type { DeepRayReport, ImpactEntry, ImpactReport } from './contracts'

function normalize(input: string): string {
  const resolved = path.resolve(input)
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved
}

export class ImpactCore {
  analyze(report: DeepRayReport, targets: string[]): ImpactReport {
    const reverse = new Map<string, Set<string>>()
    for (const edge of report.edges) {
      if (!edge.to) continue
      const key = normalize(edge.to)
      const set = reverse.get(key) ?? new Set<string>()
      set.add(edge.from)
      reverse.set(key, set)
    }

    const entries: ImpactEntry[] = []
    const affected = new Set<string>()

    for (const targetInput of targets) {
      const target = path.resolve(targetInput)
      const direct = [...(reverse.get(normalize(target)) ?? new Set<string>())].sort()
      const transitive = this.walkReverse(reverse, direct)
      direct.forEach(item => affected.add(item))
      transitive.forEach(item => affected.add(item))
      entries.push({
        target,
        directDependents: direct,
        transitiveDependents: transitive
      })
    }

    return {
      method: 'RESOLVED_IMPORT_GRAPH',
      entries,
      affectedFileCount: affected.size
    }
  }

  private walkReverse(reverse: Map<string, Set<string>>, initial: string[]): string[] {
    const visited = new Set<string>()
    const queue = [...initial]

    while (queue.length > 0) {
      const current = queue.shift()
      if (!current) continue
      const key = normalize(current)
      const parents = reverse.get(key)
      if (!parents) continue
      for (const parent of parents) {
        if (visited.has(parent)) continue
        visited.add(parent)
        queue.push(parent)
      }
    }
    return [...visited].sort()
  }
}
