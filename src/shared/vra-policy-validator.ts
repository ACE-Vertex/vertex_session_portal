import { resolveActiveSystemPolicy } from './system-policy-registry'

// VERTEX_VRA_POLICY_VALIDATOR_CORE_000064V2

export interface VraValidationIssue {
  readonly code: string
  readonly path: string
  readonly message: string
}

export interface VraValidationResult {
  readonly valid: boolean
  readonly policy_id: string
  readonly policy_version: string | null
  readonly issues: readonly VraValidationIssue[]
}

type JsonObject = Record<string, unknown>

function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isLowerHex64(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)
}

function issue(
  code: string,
  path: string,
  message: string
): VraValidationIssue {
  return { code, path, message }
}

export function validateVraAgainstActivePolicy(
  manifest: unknown
): VraValidationResult {
  const policy = resolveActiveSystemPolicy('vertex.vra.issue')

  if (!policy) {
    return {
      valid: false,
      policy_id: 'vertex.vra.issue',
      policy_version: null,
      issues: [
        issue(
          'POLICY_NOT_AVAILABLE',
          '$',
          'Active vertex.vra.issue policy is not available.'
        )
      ]
    }
  }

  const issues: VraValidationIssue[] = []
  const contract = policy.contract

  if (!isObject(manifest)) {
    issues.push(issue('MANIFEST_NOT_OBJECT', '$', 'Manifest must be an object.'))
    return {
      valid: false,
      policy_id: policy.policy_id,
      policy_version: policy.policy_version,
      issues
    }
  }

  if (manifest.schema_version !== contract.schema_version) {
    issues.push(
      issue(
        'SCHEMA_VERSION_MISMATCH',
        '$.schema_version',
        `Expected ${contract.schema_version}.`
      )
    )
  }

  if (manifest.authority !== contract.authority) {
    issues.push(
      issue(
        'AUTHORITY_MISMATCH',
        '$.authority',
        `Expected ${contract.authority}.`
      )
    )
  }

  const artifactId = manifest.artifact_id
  if (typeof artifactId !== 'string' || artifactId.trim().length === 0) {
    issues.push(issue('ARTIFACT_ID_REQUIRED', '$.artifact_id', 'artifact_id is required.'))
  }

  const routing = manifest.routing
  if (!isObject(routing)) {
    issues.push(issue('ROUTING_REQUIRED', '$.routing', 'routing object is required.'))
  } else {
    if (routing.contract_version !== contract.routing.contract_version) {
      issues.push(
        issue(
          'ROUTING_CONTRACT_MISMATCH',
          '$.routing.contract_version',
          `Expected ${contract.routing.contract_version}.`
        )
      )
    }

    for (const field of contract.routing.required) {
      const value = routing[field]
      if (typeof value !== 'string' || value.trim().length === 0) {
        issues.push(
          issue(
            'ROUTING_FIELD_REQUIRED',
            `$.routing.${field}`,
            `${field} is required.`
          )
        )
      }
    }

    if (routing.return_channel !== contract.routing.return_channel) {
      issues.push(
        issue(
          'RETURN_CHANNEL_MISMATCH',
          '$.routing.return_channel',
          `Expected ${contract.routing.return_channel}.`
        )
      )
    }

    const lanePolicy = routing.lane_policy
    if (
      typeof lanePolicy !== 'string' ||
      !contract.routing.lane_policy_allowed.includes(
        lanePolicy as (typeof contract.routing.lane_policy_allowed)[number]
      )
    ) {
      issues.push(
        issue(
          'LANE_POLICY_NOT_ALLOWED',
          '$.routing.lane_policy',
          `Allowed values: ${contract.routing.lane_policy_allowed.join(', ')}.`
        )
      )
    }
  }

  const operations = manifest.operations
  if (!Array.isArray(operations) || operations.length === 0) {
    issues.push(issue('OPERATIONS_REQUIRED', '$.operations', 'operations must be non-empty.'))
  } else {
    operations.forEach((raw, index) => {
      const path = `$.operations[${index}]`
      if (!isObject(raw)) {
        issues.push(issue('OPERATION_NOT_OBJECT', path, 'Operation must be an object.'))
        return
      }

      if (raw.op !== 'copy') {
        issues.push(issue('OPERATION_NOT_ALLOWED', `${path}.op`, 'Only copy is allowed.'))
      }

      if (
        typeof raw.source !== 'string' ||
        !raw.source.startsWith(contract.operations.source_prefix) ||
        raw.source.includes('\\')
      ) {
        issues.push(
          issue(
            'SOURCE_PATH_INVALID',
            `${path}.source`,
            `source must start with ${contract.operations.source_prefix} and use '/'.`
          )
        )
      }

      if (typeof raw.destination !== 'string' || raw.destination.length === 0 || raw.destination.includes('\\')) {
        issues.push(
          issue(
            'DESTINATION_PATH_INVALID',
            `${path}.destination`,
            "destination must be non-empty and use '/'."
          )
        )
      }

      if (!isLowerHex64(raw.sha256)) {
        issues.push(
          issue(
            'SHA256_INVALID',
            `${path}.sha256`,
            'sha256 must be actual lowercase 64-character hexadecimal.'
          )
        )
      }
    })
  }

  const verification = manifest.verification
  if (!Array.isArray(verification) || verification.length === 0) {
    issues.push(
      issue('VERIFICATION_REQUIRED', '$.verification', 'verification must be non-empty.')
    )
  } else {
    const destinations = new Set<string>()
    if (Array.isArray(operations)) {
      for (const raw of operations) {
        if (isObject(raw) && typeof raw.destination === 'string') {
          destinations.add(raw.destination)
        }
      }
    }

    verification.forEach((raw, index) => {
      const path = `$.verification[${index}]`
      if (!isObject(raw)) {
        issues.push(issue('VERIFICATION_NOT_OBJECT', path, 'Verification must be an object.'))
        return
      }

      if (typeof raw.program !== 'string' || raw.program.length === 0) {
        issues.push(issue('VERIFICATION_PROGRAM_REQUIRED', `${path}.program`, 'program is required.'))
      }

      if (!Array.isArray(raw.args) || raw.args.length === 0) {
        issues.push(issue('VERIFICATION_ARGS_REQUIRED', `${path}.args`, 'args must be non-empty.'))
        return
      }

      const args = raw.args.filter((arg): arg is string => typeof arg === 'string')
      const executesDestination = args.some(arg => destinations.has(arg))
      if (!executesDestination) {
        issues.push(
          issue(
            'VERIFICATION_DESTINATION_MISMATCH',
            `${path}.args`,
            'verification must execute a copied destination path.'
          )
        )
      }
    })
  }

  return {
    valid: issues.length === 0,
    policy_id: policy.policy_id,
    policy_version: policy.policy_version,
    issues
  }
}
