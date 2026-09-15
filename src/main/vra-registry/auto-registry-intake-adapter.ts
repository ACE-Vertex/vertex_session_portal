import type { AutoRegistryIntake, ImmutableRegistryOrigin } from './vra-registry-contract'
import type { VraRegistryCore } from './vra-registry-core'

type OriginVera = ImmutableRegistryOrigin['originVera']
type OriginSession = ImmutableRegistryOrigin['originSession']
type LanePolicy = AutoRegistryIntake['lanePolicy']

export interface AutoRegistryCandidate {
  registryId: string
  jobId: string
  artifactId: string | null
  correlationId: string
  projectId: string | null
  projectName: string | null
  requestedLane: string | null
  lanePolicy: LanePolicy
  parallelism: number
  workerConcurrency: number | null
  originVera: OriginVera | 'UNKNOWN'
  originSession: string | null
  originWindow: string | null
  returnChannel: string
}

function requireOriginSession(value: string | null, code: string): OriginSession {
  if (!value || !/^vera-0[1-5]$/.test(value)) throw new Error(code)
  return value as OriginSession
}

function requireOriginVera(value: OriginVera | 'UNKNOWN'): OriginVera {
  if (value === 'UNKNOWN') throw new Error('REGISTRY_AUTO_ORIGIN_VERA_REQUIRED')
  return value
}

/**
 * AUTO-only admission boundary.
 *
 * This adapter has no Workstation, Bay UI, filesystem publication, or Human Gate
 * authority. It converts an already Human-authorized AUTO card into Registry identity,
 * persists REGISTERED, then advances only to READY_FOR_BAY.
 */
export async function admitAutoRegistryCandidate(
  core: VraRegistryCore,
  candidate: AutoRegistryCandidate,
): Promise<string> {
  const artifactId = candidate.artifactId?.trim()
  if (!artifactId) throw new Error('REGISTRY_AUTO_ARTIFACT_ID_REQUIRED')

  const originSession = requireOriginSession(candidate.originSession, 'REGISTRY_AUTO_ORIGIN_SESSION_REQUIRED')
  const originWindow = requireOriginSession(candidate.originWindow, 'REGISTRY_AUTO_ORIGIN_WINDOW_REQUIRED')
  const originVera = requireOriginVera(candidate.originVera)

  if (originSession !== originWindow) throw new Error('REGISTRY_AUTO_ORIGIN_WINDOW_MISMATCH')
  if (`VERA${originSession.slice(-2)}` !== originVera) throw new Error('REGISTRY_AUTO_ORIGIN_VERA_MISMATCH')

  const intake: AutoRegistryIntake = {
    dispatchMode: 'AUTO',
    registryId: candidate.registryId,
    jobId: candidate.jobId,
    artifactId,
    correlationId: candidate.correlationId,
    projectId: candidate.projectId,
    projectName: candidate.projectName,
    requestedLane: candidate.requestedLane,
    lanePolicy: candidate.lanePolicy,
    parallelism: candidate.parallelism,
    workerConcurrency: candidate.workerConcurrency,
    origin: {
      originVera,
      originSession,
      originWindow,
      returnChannel: candidate.returnChannel,
    },
  }

  await core.registerAuto(intake)
  await core.markBayReady(candidate.registryId)
  return candidate.registryId
}
