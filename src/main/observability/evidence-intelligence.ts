import type { WorkstationEvidenceDigest } from './contracts'

type UnknownRecord = Record<string, unknown>

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null
}

function asBoolean(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null
}

function collectRecords(root: unknown, maxNodes = 2000): UnknownRecord[] {
  const records: UnknownRecord[] = []
  const queue: unknown[] = [root]
  const seen = new Set<unknown>()

  while (queue.length > 0 && records.length < maxNodes) {
    const current = queue.shift()
    if (current === null || current === undefined || seen.has(current)) continue
    if (typeof current === 'object') seen.add(current)

    if (Array.isArray(current)) {
      queue.push(...current)
      continue
    }
    if (!isRecord(current)) continue

    records.push(current)
    for (const value of Object.values(current)) {
      if (typeof value === 'object' && value !== null) queue.push(value)
    }
  }
  return records
}

function firstValue(records: UnknownRecord[], keys: string[]): unknown {
  for (const record of records) {
    for (const key of keys) {
      if (key in record) return record[key]
    }
  }
  return undefined
}

function allNumbers(records: UnknownRecord[], keys: string[]): number[] {
  const numbers: number[] = []
  for (const record of records) {
    for (const key of keys) {
      const value = record[key]
      if (typeof value === 'number' && Number.isFinite(value)) numbers.push(value)
    }
  }
  return numbers
}

function anyTrue(records: UnknownRecord[], keys: string[]): boolean {
  return records.some(record => keys.some(key => record[key] === true))
}

export interface HydratedStreams {
  stdout?: string | null
  stderr?: string | null
}

export interface EvidenceLogPath {
  kind: 'stdout' | 'stderr'
  path: string
}

export class EvidenceIntelligence {
  digest(raw: unknown, streams: HydratedStreams = {}): WorkstationEvidenceDigest {
    const records = collectRecords(raw)
    const jobId = asString(firstValue(records, ['job_id', 'jobId']))
    const artifactId = asString(firstValue(records, ['artifact_id', 'artifactId']))
    const evidenceId = asString(firstValue(records, ['evidence_id', 'evidenceId']))
    const executionLane = asString(firstValue(records, ['execution_lane', 'lane_id', 'executionLane']))
    const result = asString(firstValue(records, ['result', 'final_state']))
    const verified = asBoolean(firstValue(records, ['verified']))
    const success = asBoolean(firstValue(records, ['success']))
    const internalReference = asString(firstValue(records, ['internal_reference', 'internalReference']))
    const evidencePath = asString(firstValue(records, ['evidence_path', 'evidencePath']))
    const exitCodes = allNumbers(records, ['exit_code', 'exitCode'])
    const timedOut = anyTrue(records, ['timed_out', 'timedOut'])
    const stdout = streams.stdout ?? null
    const stderr = streams.stderr ?? null

    const failureParts = [
      result,
      internalReference,
      stdout,
      stderr,
      exitCodes.length > 0 ? `exit_code=${exitCodes.join(',')}` : null,
      timedOut ? 'timed_out=true' : null
    ].filter((value): value is string => typeof value === 'string' && value.length > 0)

    return {
      jobId,
      artifactId,
      evidenceId,
      executionLane,
      result,
      verified,
      success,
      timedOut,
      exitCodes,
      internalReference,
      evidencePath,
      stdout,
      stderr,
      rawFailureText: failureParts.join('\n')
    }
  }

  commandLogPaths(raw: unknown): EvidenceLogPath[] {
    const records = collectRecords(raw)
    const results: EvidenceLogPath[] = []
    const seen = new Set<string>()

    for (const record of records) {
      const stdoutPath = asString(record.stdout_path ?? record.stdoutPath)
      const stderrPath = asString(record.stderr_path ?? record.stderrPath)
      if (stdoutPath) {
        const key = `stdout:${stdoutPath}`
        if (!seen.has(key)) {
          seen.add(key)
          results.push({ kind: 'stdout', path: stdoutPath })
        }
      }
      if (stderrPath) {
        const key = `stderr:${stderrPath}`
        if (!seen.has(key)) {
          seen.add(key)
          results.push({ kind: 'stderr', path: stderrPath })
        }
      }
    }
    return results
  }
}
