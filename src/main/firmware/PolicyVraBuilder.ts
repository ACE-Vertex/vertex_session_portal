export type ActivePolicyReader = {
  readActivePolicy(target: string): unknown
}

export type PolicyVraBuilderResult = {
  policyTarget: string
  policyVersion: string
  manifest: Record<string, unknown>
}

type JsonRecord = Record<string, unknown>

type VraPolicyProfile = {
  contract: 'vertex-system-policy/vra-1'
  enabled: true
  mode: 'ENFORCE'
  allowedOperations: string[]
  allowedVerificationPrograms: string[]
  allowedLanePolicies: Array<'ANY' | 'PREFER'>
  allowedProjectRoots: string[]
  maxOperations: number
  allowedDestinationPrefixes?: string[]
  forceLanePolicy?: 'ANY' | 'PREFER'
}

function isRecord(value: unknown): value is JsonRecord {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function nonEmptyString(value: unknown, field: string): string {
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`POLICY_VRA_INVALID:${field}`)
  }
  return value.trim()
}

function stringArray(value: unknown, field: string): string[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`POLICY_VRA_INVALID:${field}`)
  }
  const out = value.map((item) => nonEmptyString(item, field))
  return [...new Set(out)]
}

function stable(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']'
  const obj = value as JsonRecord
  return (
    '{' +
    Object.keys(obj)
      .sort()
      .map((key) => JSON.stringify(key) + ':' + stable(obj[key]))
      .join(',') +
    '}'
  )
}

function profileCandidate(policy: JsonRecord): unknown {
  const direct = policy.vra
  const changes = isRecord(policy.changes) ? policy.changes.vra : undefined

  if (direct !== undefined && changes !== undefined && stable(direct) !== stable(changes)) {
    throw new Error('POLICY_VRA_PROFILE_AMBIGUOUS')
  }
  return direct !== undefined ? direct : changes
}

function parseProfile(active: JsonRecord): VraPolicyProfile {
  if (!isRecord(active.policy)) throw new Error('POLICY_VRA_ACTIVE_POLICY_MALFORMED')

  const candidate = profileCandidate(active.policy)
  if (!isRecord(candidate)) throw new Error('POLICY_VRA_PROFILE_MISSING')

  if (candidate.contract !== 'vertex-system-policy/vra-1') {
    throw new Error('POLICY_VRA_PROFILE_CONTRACT_MISMATCH')
  }
  if (candidate.enabled !== true || candidate.mode !== 'ENFORCE') {
    throw new Error('POLICY_VRA_PROFILE_NOT_ENFORCING')
  }

  const allowedOperations = stringArray(candidate.allowedOperations, 'allowedOperations')
  if (allowedOperations.some((op) => op !== 'copy')) {
    throw new Error('POLICY_VRA_UNSUPPORTED_OPERATION_POLICY')
  }

  const allowedVerificationPrograms = stringArray(
    candidate.allowedVerificationPrograms,
    'allowedVerificationPrograms'
  )

  const rawLanePolicies = stringArray(candidate.allowedLanePolicies, 'allowedLanePolicies')
  if (rawLanePolicies.some((lane) => lane !== 'ANY' && lane !== 'PREFER')) {
    throw new Error('POLICY_VRA_INVALID_LANE_POLICY')
  }
  const allowedLanePolicies = rawLanePolicies as Array<'ANY' | 'PREFER'>

  const allowedProjectRoots = stringArray(candidate.allowedProjectRoots, 'allowedProjectRoots')

  if (
    typeof candidate.maxOperations !== 'number' ||
    !Number.isInteger(candidate.maxOperations) ||
    candidate.maxOperations < 1 ||
    candidate.maxOperations > 64
  ) {
    throw new Error('POLICY_VRA_INVALID:maxOperations')
  }

  let allowedDestinationPrefixes: string[] | undefined
  if (candidate.allowedDestinationPrefixes !== undefined) {
    allowedDestinationPrefixes = stringArray(
      candidate.allowedDestinationPrefixes,
      'allowedDestinationPrefixes'
    )
  }

  let forceLanePolicy: 'ANY' | 'PREFER' | undefined
  if (candidate.forceLanePolicy !== undefined) {
    if (candidate.forceLanePolicy !== 'ANY' && candidate.forceLanePolicy !== 'PREFER') {
      throw new Error('POLICY_VRA_INVALID:forceLanePolicy')
    }
    if (!allowedLanePolicies.includes(candidate.forceLanePolicy)) {
      throw new Error('POLICY_VRA_FORCE_LANE_NOT_ALLOWED')
    }
    forceLanePolicy = candidate.forceLanePolicy
  }

  return {
    contract: 'vertex-system-policy/vra-1',
    enabled: true,
    mode: 'ENFORCE',
    allowedOperations,
    allowedVerificationPrograms,
    allowedLanePolicies,
    allowedProjectRoots,
    maxOperations: candidate.maxOperations,
    allowedDestinationPrefixes,
    forceLanePolicy
  }
}

function parseIncoming(raw: unknown): { value: JsonRecord; wasString: boolean } {
  const wasString = typeof raw === 'string'
  let value: unknown = raw

  if (wasString) {
    try {
      value = JSON.parse(raw as string)
    } catch {
      throw new Error('POLICY_VRA_INPUT_JSON_INVALID')
    }
  }

  if (!isRecord(value)) throw new Error('POLICY_VRA_INPUT_NOT_OBJECT')
  return { value, wasString }
}

function exactRecord(value: unknown, field: string): JsonRecord {
  if (!isRecord(value)) throw new Error(`POLICY_VRA_INVALID:${field}`)
  return value
}

function isSha256(value: string): boolean {
  return /^[0-9a-f]{64}$/.test(value)
}

export class PolicyVraBuilder {
  constructor(private readonly policyReader: ActivePolicyReader) {}

  private resolveActivePolicy(input: JsonRecord): {
    target: string
    active: JsonRecord
    version: string
    profile: VraPolicyProfile
  } {
    const routing = exactRecord(input.routing, 'routing')
    const target = exactRecord(input.target, 'target')

    const candidates = [
      routing.project_id,
      routing.project_name,
      target.project_root
    ].filter((value): value is string => typeof value === 'string' && Boolean(value.trim()))

    const uniqueCandidates = [...new Set(candidates.map((value) => value.trim()))]
    if (uniqueCandidates.length === 0) throw new Error('POLICY_VRA_POLICY_TARGET_UNRESOLVED')

    const matches: Array<{ target: string; active: JsonRecord }> = []
    for (const candidate of uniqueCandidates) {
      const active = this.policyReader.readActivePolicy(candidate)
      if (isRecord(active)) matches.push({ target: candidate, active })
    }

    if (matches.length === 0) throw new Error('POLICY_VRA_ACTIVE_POLICY_MISSING')
    if (matches.length > 1) {
      const versions = new Set(
        matches.map((match) => (typeof match.active.version === 'string' ? match.active.version : ''))
      )
      const policies = new Set(matches.map((match) => stable(match.active.policy)))
      if (versions.size !== 1 || policies.size !== 1) {
        throw new Error('POLICY_VRA_ACTIVE_POLICY_AMBIGUOUS')
      }
    }

    const selected = matches[0]
    const version = nonEmptyString(selected.active.version, 'active.version')
    const profile = parseProfile(selected.active)
    return { target: selected.target, active: selected.active, version, profile }
  }

  build(raw: unknown): unknown {
    return this.buildWithEvidence(raw).output
  }

  buildWithEvidence(raw: unknown): {
    output: unknown
    policyTarget: string
    policyVersion: string
    manifest: JsonRecord
  } {
    const { value: input, wasString } = parseIncoming(raw)
    const { target: policyTarget, version: policyVersion, profile } =
      this.resolveActivePolicy(input)

    const source = exactRecord(input.source, 'source')
    const target = exactRecord(input.target, 'target')
    const routing = exactRecord(input.routing, 'routing')

    const projectRoot = nonEmptyString(target.project_root, 'target.project_root')
    if (!profile.allowedProjectRoots.includes(projectRoot)) {
      throw new Error('POLICY_VRA_PROJECT_ROOT_DENIED')
    }

    const requestedLane = nonEmptyString(routing.lane_policy, 'routing.lane_policy')
    if (requestedLane !== 'ANY' && requestedLane !== 'PREFER') {
      throw new Error('POLICY_VRA_LANE_POLICY_INVALID')
    }
    if (!profile.allowedLanePolicies.includes(requestedLane)) {
      throw new Error('POLICY_VRA_LANE_POLICY_DENIED')
    }
    const lanePolicy = profile.forceLanePolicy ?? requestedLane

    if (!Array.isArray(input.operations) || input.operations.length === 0) {
      throw new Error('POLICY_VRA_OPERATIONS_MISSING')
    }
    if (input.operations.length > profile.maxOperations) {
      throw new Error('POLICY_VRA_TOO_MANY_OPERATIONS')
    }

    const operations = input.operations.map((item, index) => {
      const op = exactRecord(item, `operations[${index}]`)
      if (op.op !== 'copy' || !profile.allowedOperations.includes('copy')) {
        throw new Error('POLICY_VRA_OPERATION_DENIED')
      }

      const sourcePath = nonEmptyString(op.source, `operations[${index}].source`)
      const destination = nonEmptyString(op.destination, `operations[${index}].destination`)
      const sha256 = nonEmptyString(op.sha256, `operations[${index}].sha256`).toLowerCase()

      if (!sourcePath.startsWith('payload/') || sourcePath.includes('\\')) {
        throw new Error('POLICY_VRA_COPY_SOURCE_INVALID')
      }
      if (destination.includes('\\')) {
        throw new Error('POLICY_VRA_DESTINATION_INVALID')
      }
      if (!isSha256(sha256)) throw new Error('POLICY_VRA_SHA256_INVALID')

      if (
        profile.allowedDestinationPrefixes &&
        !profile.allowedDestinationPrefixes.some(
          (prefix) => destination === prefix || destination.startsWith(prefix.endsWith('/') ? prefix : prefix + '/')
        )
      ) {
        throw new Error('POLICY_VRA_DESTINATION_DENIED')
      }

      return {
        op: 'copy',
        source: sourcePath,
        destination,
        sha256
      }
    })

    const destinations = new Set(operations.map((op) => op.destination))

    if (!Array.isArray(input.verification) || input.verification.length === 0) {
      throw new Error('POLICY_VRA_VERIFICATION_MISSING')
    }

    const verification = input.verification.map((item, index) => {
      const verify = exactRecord(item, `verification[${index}]`)
      const program = nonEmptyString(verify.program, `verification[${index}].program`)
      if (!profile.allowedVerificationPrograms.includes(program)) {
        throw new Error('POLICY_VRA_VERIFICATION_PROGRAM_DENIED')
      }

      if (!Array.isArray(verify.args) || verify.args.length === 0) {
        throw new Error('POLICY_VRA_VERIFICATION_ARGS_MISSING')
      }
      const args = verify.args.map((arg, argIndex) =>
        nonEmptyString(arg, `verification[${index}].args[${argIndex}]`)
      )

      if (!args.some((arg) => destinations.has(arg))) {
        throw new Error('POLICY_VRA_VERIFICATION_DESTINATION_MISMATCH')
      }

      return { program, args }
    })

    const originVera = nonEmptyString(routing.origin_vera, 'routing.origin_vera')
    const sourceActor = nonEmptyString(source.actor, 'source.actor')
    if (originVera !== sourceActor) throw new Error('POLICY_VRA_PROVENANCE_MISMATCH')

    const canonical: JsonRecord = {
      schema_version: 'vra/1',
      artifact_id: nonEmptyString(input.artifact_id, 'artifact_id'),
      title: nonEmptyString(input.title, 'title'),
      source: {
        actor: sourceActor,
        model: nonEmptyString(source.model, 'source.model')
      },
      target: {
        project_root: projectRoot
      },
      authority: 'HUMAN_APPLY',
      routing: {
        contract_version: 'vra-routing/1',
        job_id: nonEmptyString(routing.job_id, 'routing.job_id'),
        origin_vera: originVera,
        origin_session: nonEmptyString(routing.origin_session, 'routing.origin_session'),
        origin_window: nonEmptyString(routing.origin_window, 'routing.origin_window'),
        return_channel: 'vertex-session-portal:return-queue',
        project_id: nonEmptyString(routing.project_id, 'routing.project_id'),
        project_name: nonEmptyString(routing.project_name, 'routing.project_name'),
        correlation_id: nonEmptyString(routing.correlation_id, 'routing.correlation_id'),
        lane_policy: lanePolicy
      },
      operations,
      verification
    }

    if (input.card_kind === 'TEST') canonical.card_kind = 'TEST'

    return {
      output: wasString ? JSON.stringify(canonical) : canonical,
      policyTarget,
      policyVersion,
      manifest: canonical
    }
  }
}
