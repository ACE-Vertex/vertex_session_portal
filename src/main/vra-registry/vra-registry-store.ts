import type { RegistryRecord } from './vra-registry-contract'
import type { VLogAppendStore, VLogEvent, VLogQuery, VLogQueryGate } from './vlog-contract'
import { validateVLogQuery } from './vlog-contract'

export interface VraRegistryStore {
  getByRegistryId(registryId: string): Promise<RegistryRecord | null> | RegistryRecord | null
  getByJobId(jobId: string): Promise<RegistryRecord | null> | RegistryRecord | null
  put(record: RegistryRecord): Promise<void> | void
}

export class MemoryRegistryStore implements VraRegistryStore, VLogAppendStore, VLogQueryGate {
  private readonly records = new Map<string, RegistryRecord>()
  private readonly byJob = new Map<string, string>()
  private readonly events: VLogEvent[] = []

  getByRegistryId(registryId: string): RegistryRecord | null {
    return this.records.get(registryId) ?? null
  }

  getByJobId(jobId: string): RegistryRecord | null {
    const registryId = this.byJob.get(jobId)
    return registryId ? this.records.get(registryId) ?? null : null
  }

  put(record: RegistryRecord): void {
    const existing = this.byJob.get(record.jobId)
    if (existing && existing !== record.registryId) throw new Error('REGISTRY_JOB_ID_CONFLICT')
    this.records.set(record.registryId, structuredClone(record))
    this.byJob.set(record.jobId, record.registryId)
  }

  append(event: VLogEvent): void {
    if (this.events.some((item) => item.eventId === event.eventId)) return
    this.events.push(structuredClone(event))
  }

  query(request: VLogQuery): readonly VLogEvent[] {
    const query = validateVLogQuery(request)
    return this.events
      .filter((event) =>
        (query.jobId ? event.jobId === query.jobId : true) &&
        (query.artifactId ? event.artifactId === query.artifactId : true) &&
        (query.correlationId ? event.correlationId === query.correlationId : true)
      )
      .slice(-query.limit)
      .map((event) => structuredClone(event))
  }
}
