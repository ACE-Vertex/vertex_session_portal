import { randomUUID } from 'node:crypto'
import type {
  AutoRegistryIntake,
  RegistryMutationResult,
  RegistryRecord,
  RegistryState,
  RegistryTransition,
} from './vra-registry-contract'
import { VRA_REGISTRY_SCHEMA } from './vra-registry-contract'
import type { VLogAppendStore } from './vlog-contract'
import { eventFromTransition } from './vlog-contract'
import type { VraRegistryStore } from './vra-registry-store'
import { VraRegistryObserver } from './vra-registry-observer'
import { validateVraAgainstActivePolicy } from '../../shared/vra-policy-validator';

const ALLOWED: Readonly<Record<RegistryState, readonly RegistryState[]>> = {
  REGISTERED: ['READY_FOR_BAY', 'REJECTED', 'FAILED'],
  READY_FOR_BAY: ['DISPATCHED', 'REJECTED', 'FAILED'],
  DISPATCHED: ['EXECUTING', 'FAILED', 'REJECTED'],
  EXECUTING: ['EVIDENCE_AVAILABLE', 'FAILED'],
  EVIDENCE_AVAILABLE: ['RETURN_QUEUED', 'FAILED'],
  RETURN_QUEUED: ['RETURNED', 'FAILED'],
  RETURNED: [],
  FAILED: ['EVIDENCE_AVAILABLE'],
  REJECTED: [],
}

function nowUtc(): string {
  return new Date().toISOString()
}

function ensureNonEmpty(value: string, code: string): string {
  const clean = value.trim()
  if (!clean) throw new Error(code)
  return clean
}

function validateAutoIntake(input: AutoRegistryIntake): AutoRegistryIntake {
  if (input.dispatchMode !== 'AUTO') throw new Error('REGISTRY_AUTO_ONLY')
  ensureNonEmpty(input.registryId, 'REGISTRY_ID_REQUIRED')
  ensureNonEmpty(input.jobId, 'REGISTRY_JOB_ID_REQUIRED')
  ensureNonEmpty(input.artifactId, 'REGISTRY_ARTIFACT_ID_REQUIRED')
  ensureNonEmpty(input.correlationId, 'REGISTRY_CORRELATION_ID_REQUIRED')
  ensureNonEmpty(input.origin.returnChannel, 'REGISTRY_RETURN_CHANNEL_REQUIRED')
  if (input.origin.originSession !== input.origin.originWindow) {
    throw new Error('REGISTRY_ORIGIN_WINDOW_MISMATCH')
  }
  const expectedVera = `VERA${input.origin.originSession.slice(-2)}`
  if (input.origin.originVera !== expectedVera) throw new Error('REGISTRY_ORIGIN_VERA_MISMATCH')
  if (input.lanePolicy !== 'ANY' && input.lanePolicy !== 'PREFER') {
    throw new Error('REGISTRY_EXTERNAL_LANE_POLICY_INVALID')
  }
  if (input.lanePolicy === 'PREFER' && !input.requestedLane) {
    throw new Error('REGISTRY_PREFER_REQUIRES_REQUESTED_LANE')
  }
  if (!Number.isInteger(input.parallelism) || input.parallelism < 1 || input.parallelism > 32) {
    throw new Error('REGISTRY_PARALLELISM_INVALID')
  }
  if (
    input.workerConcurrency !== null &&
    (!Number.isInteger(input.workerConcurrency) || input.workerConcurrency < 1)
  ) {
    throw new Error('REGISTRY_WORKER_CONCURRENCY_INVALID')
  }
  return input
}

export class VraRegistryCore {
  private readonly observer: VraRegistryObserver

  constructor(
    private readonly store: VraRegistryStore,
    private readonly vlog: VLogAppendStore,
  ) {
    this.observer = new VraRegistryObserver(vlog)
  }

  async registerAuto(input: AutoRegistryIntake): Promise<RegistryMutationResult> {
    const safe = validateAutoIntake(input)
    const vraPolicyValidation = validateVraAgainstActivePolicy(safe);
    if (!vraPolicyValidation.valid) {
      throw new Error("VRA rejected by active System Policy");
    }

    const existingByRegistry = await this.store.getByRegistryId(safe.registryId)
    const existingByJob = await this.store.getByJobId(safe.jobId)

    if (existingByRegistry || existingByJob) {
      const existing = existingByRegistry ?? existingByJob
      if (
        !existing ||
        existing.registryId !== safe.registryId ||
        existing.jobId !== safe.jobId ||
        existing.artifactId !== safe.artifactId ||
        existing.correlationId !== safe.correlationId
      ) {
        throw new Error('REGISTRY_IDENTITY_CONFLICT')
      }
      return { record: existing, changed: false, idempotent: true }
    }

    const utc = nowUtc()
    const record: RegistryRecord = {
      ...safe,
      schema: VRA_REGISTRY_SCHEMA,
      state: 'REGISTERED',
      allocatedLane: null,
      evidenceId: null,
      rerunOfJobId: null,
      createdUtc: utc,
      updatedUtc: utc,
    }
    await this.store.put(record)

    await this.vlog.append({
      schema: 'vertex-session-portal/vlog/1',
      eventId: `registry:${record.registryId}:registered`,
      kind: 'REGISTRY_REGISTERED',
      registryId: record.registryId,
      jobId: record.jobId,
      artifactId: record.artifactId,
      correlationId: record.correlationId,
      occurredUtc: utc,
      stateFrom: null,
      stateTo: 'REGISTERED',
      evidenceId: null,
      code: null,
      note: null,
    })

    return { record, changed: true, idempotent: false }
  }

  async markBayReady(registryId: string): Promise<RegistryMutationResult> {
    return this.transition(registryId, 'READY_FOR_BAY')
  }

  async markDispatched(registryId: string): Promise<RegistryMutationResult> {
    return this.transition(registryId, 'DISPATCHED')
  }

  async markExecuting(registryId: string, allocatedLane: string): Promise<RegistryMutationResult> {
    if (!/^lane-(0[1-9]|[12][0-9]|3[0-2])$/.test(allocatedLane)) {
      throw new Error('REGISTRY_ALLOCATED_LANE_INVALID')
    }
    return this.transition(registryId, 'EXECUTING', { allocatedLane })
  }

  async bindEvidence(registryId: string, evidenceId: string): Promise<RegistryMutationResult> {
    ensureNonEmpty(evidenceId, 'REGISTRY_EVIDENCE_ID_REQUIRED')
    return this.transition(registryId, 'EVIDENCE_AVAILABLE', { evidenceId })
  }

  async markReturnQueued(registryId: string): Promise<RegistryMutationResult> {
    return this.transition(registryId, 'RETURN_QUEUED')
  }

  async markReturned(registryId: string): Promise<RegistryMutationResult> {
    const record = await this.requireRecord(registryId)
    if (!record.evidenceId) throw new Error('REGISTRY_RETURN_WITHOUT_EVIDENCE')
    return this.transition(registryId, 'RETURNED')
  }

  async fail(registryId: string): Promise<RegistryMutationResult> {
    return this.transition(registryId, 'FAILED')
  }

  private async requireRecord(registryId: string): Promise<RegistryRecord> {
    const record = await this.store.getByRegistryId(registryId)
    if (!record) throw new Error('REGISTRY_RECORD_NOT_FOUND')
    return record
  }

  private async transition(
    registryId: string,
    to: RegistryState,
    patch: Pick<Partial<RegistryRecord>, 'allocatedLane' | 'evidenceId'> = {},
  ): Promise<RegistryMutationResult> {
    const current = await this.requireRecord(registryId)
    if (current.state === to) return { record: current, changed: false, idempotent: true }
    if (!ALLOWED[current.state].includes(to)) {
      throw new Error(`REGISTRY_ILLEGAL_TRANSITION:${current.state}->${to}`)
    }

    const occurredUtc = nowUtc()
    const next: RegistryRecord = {
      ...current,
      ...patch,
      state: to,
      updatedUtc: occurredUtc,
    }

    const transition: RegistryTransition = {
      registryId: next.registryId,
      jobId: next.jobId,
      artifactId: next.artifactId,
      correlationId: next.correlationId,
      from: current.state,
      to,
      occurredUtc,
      evidenceId: next.evidenceId,
      allocatedLane: next.allocatedLane,
    }

    const anomalies = this.observer.observe(transition)
    if (anomalies.length > 0) {
      throw new Error(`REGISTRY_OBSERVER_REJECTED:${anomalies.map((x) => x.code).join(',')}`)
    }

    await this.store.put(next)
    await this.vlog.append(eventFromTransition(randomUUID(), transition))

    if (to === 'READY_FOR_BAY') {
      await this.vlog.append({
        schema: 'vertex-session-portal/vlog/1',
        eventId: `bay-ready:${next.registryId}:${occurredUtc}`,
        kind: 'BAY_TRIGGER_READY',
        registryId: next.registryId,
        jobId: next.jobId,
        artifactId: next.artifactId,
        correlationId: next.correlationId,
        occurredUtc,
        stateFrom: current.state,
        stateTo: to,
        evidenceId: next.evidenceId,
        code: null,
        note: 'Trigger only. Dispatch Bay owns presentation; Workstation owns lane allocation.',
      })
    }

    return { record: next, changed: true, idempotent: false }
  }
}
