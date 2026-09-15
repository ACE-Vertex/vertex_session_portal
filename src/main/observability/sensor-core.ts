import type {
  DeepRayReport,
  SensorSignal,
  WorkstationEvidenceDigest
} from './contracts'

export class SensorCore {
  observeRay(report: DeepRayReport): SensorSignal[] {
    const signals: SensorSignal[] = []

    if (report.truncated) {
      signals.push({
        code: 'RAY_SCAN_TRUNCATED',
        severity: 'WARN',
        message: 'Deep Ray reached a configured safety bound.',
        source: 'RAY',
        evidence: { files: report.sourceFiles.length, nodes: report.tree.nodes.length }
      })
    }

    if (report.tree.warnings.length > 0) {
      signals.push({
        code: 'RAY_READ_WARNINGS',
        severity: 'WARN',
        message: 'Ray encountered paths it could not read.',
        source: 'RAY',
        evidence: { count: report.tree.warnings.length }
      })
    }

    if (report.sourceFiles.length === 0) {
      signals.push({
        code: 'RAY_NO_SOURCE_FILES',
        severity: 'WARN',
        message: 'No bounded source files were discovered.',
        source: 'RAY',
        evidence: { root: report.root }
      })
    }

    return signals
  }

  observeEvidence(digest: WorkstationEvidenceDigest): SensorSignal[] {
    const signals: SensorSignal[] = []

    if (digest.timedOut) {
      signals.push({
        code: 'WORKSTATION_VERIFY_TIMEOUT',
        severity: 'ERROR',
        message: 'A verification command timed out.',
        source: 'WORKSTATION_EVIDENCE',
        evidence: { timedOut: true }
      })
    }

    const failingExitCodes = digest.exitCodes.filter(code => code !== 0)
    if (failingExitCodes.length > 0) {
      signals.push({
        code: 'WORKSTATION_NONZERO_EXIT',
        severity: 'ERROR',
        message: 'At least one command returned a non-zero exit code.',
        source: 'WORKSTATION_EVIDENCE',
        evidence: { exitCodes: failingExitCodes.join(',') }
      })
    }

    if (digest.verified === false || digest.success === false || digest.result === 'failed') {
      signals.push({
        code: 'WORKSTATION_VERIFICATION_FAILED',
        severity: 'ERROR',
        message: 'Workstation reported unsuccessful verification.',
        source: 'WORKSTATION_EVIDENCE',
        evidence: {
          verified: digest.verified,
          success: digest.success,
          result: digest.result
        }
      })
    }

    if (!digest.stdout && !digest.stderr && (digest.verified === false || digest.result === 'failed')) {
      signals.push({
        code: 'FAILURE_STREAMS_NOT_HYDRATED',
        severity: 'WARN',
        message: 'Failure evidence has no stdout/stderr body available to Judge.',
        source: 'WORKSTATION_EVIDENCE',
        evidence: {}
      })
    }

    return signals
  }
}
