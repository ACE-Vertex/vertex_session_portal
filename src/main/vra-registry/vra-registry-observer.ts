import type { RegistryTransition } from './vra-registry-contract'
import type { VLogAppendStore, VLogEvent } from './vlog-contract'

export interface RegistryAnomaly {
  code: string
  registryId: string
  jobId: string
  occurredUtc: string
  detail: string
}

export class VraRegistryObserver {
  constructor(private readonly vlog: VLogAppendStore) {}

  observe(transition: RegistryTransition): RegistryAnomaly[] {
    const anomalies: RegistryAnomaly[] = []

    if (transition.to === 'RETURNED' && !transition.evidenceId) {
      anomalies.push({
        code: 'RETURNED_WITHOUT_EVIDENCE',
        registryId: transition.registryId,
        jobId: transition.jobId,
        occurredUtc: transition.occurredUtc,
        detail: 'RETURNED requires durable Evidence identity.',
      })
    }

    if (transition.allocatedLane && !/^lane-(0[1-9]|[12][0-9]|3[0-2])$/.test(transition.allocatedLane)) {
      anomalies.push({
        code: 'ALLOCATED_LANE_OUT_OF_RANGE',
        registryId: transition.registryId,
        jobId: transition.jobId,
        occurredUtc: transition.occurredUtc,
        detail: transition.allocatedLane,
      })
    }

    for (const anomaly of anomalies) {
      const event: VLogEvent = {
        schema: 'vertex-session-portal/vlog/1',
        eventId: `anomaly:${anomaly.jobId}:${anomaly.code}:${anomaly.occurredUtc}`,
        kind: 'ANOMALY',
        registryId: anomaly.registryId,
        jobId: anomaly.jobId,
        artifactId: transition.artifactId,
        correlationId: transition.correlationId,
        occurredUtc: anomaly.occurredUtc,
        stateFrom: transition.from,
        stateTo: transition.to,
        evidenceId: transition.evidenceId,
        code: anomaly.code,
        note: anomaly.detail,
      }
      void this.vlog.append(event)
    }

    return anomalies
  }
}
