import type {
  JudgeDecision,
  JudgeFailureClass,
  SensorSignal,
  WorkstationEvidenceDigest
} from './contracts'

interface Rule {
  failureClass: JudgeFailureClass
  confidence: number
  pattern: RegExp
  summary: string
  recommendedAction: string
  safeToRetryUnchanged: boolean
  needsMoreRay: boolean
}

const RULES: Rule[] = [
  {
    failureClass: 'TIMEOUT',
    confidence: 0.99,
    pattern: /\b(timed[_ -]?out|timeout)\b/i,
    summary: 'Verification or execution timed out.',
    recommendedAction: 'Inspect the timed command, runtime pressure and blocking dependencies before re-execution.',
    safeToRetryUnchanged: false,
    needsMoreRay: true
  },
  {
    failureClass: 'ORIGIN_UNRESOLVED',
    confidence: 0.99,
    pattern: /\bVRA_ORIGIN_UNRESOLVED\b|origin[_ -]?unresolved/i,
    summary: 'Immutable VRA origin could not be resolved.',
    recommendedAction: 'Repair origin capture. Do not fall back to the active Vera/window.',
    safeToRetryUnchanged: false,
    needsMoreRay: true
  },
  {
    failureClass: 'PATH_SCOPE_DENIED',
    confidence: 0.99,
    pattern: /\bRAY_SCOPE_DENIED\b|scope[_ -]?denied|outside allowed root/i,
    summary: 'An observation target escaped the configured read-only scope.',
    recommendedAction: 'Add the intended root explicitly or correct the target path. Do not weaken scope checks globally.',
    safeToRetryUnchanged: false,
    needsMoreRay: false
  },
  {
    failureClass: 'LOCK_FAILURE',
    confidence: 0.96,
    pattern: /\b(lock failed|lock conflict|write lock|target lock|lock denied)\b/i,
    summary: 'A lock or target ownership conflict blocked execution.',
    recommendedAction: 'Inspect current owner and recovery state before creating a replacement VRA.',
    safeToRetryUnchanged: false,
    needsMoreRay: true
  },
  {
    failureClass: 'BUILD_FAILURE',
    confidence: 0.95,
    pattern: /\b(TS\d{4}|typecheck.*fail|build.*fail|compile.*error|cargo.*error)\b/i,
    summary: 'Build or type validation failed.',
    recommendedAction: 'Ray the reported source anchors and dependency edges, then patch only the failing contract.',
    safeToRetryUnchanged: false,
    needsMoreRay: true
  },
  {
    failureClass: 'WORKSTATION_OFFLINE',
    confidence: 0.95,
    pattern: /\b(ECONNREFUSED|workstation offline|health.*unavailable|server unavailable)\b/i,
    summary: 'Workstation control endpoint was unavailable.',
    recommendedAction: 'Recover the Workstation server and reconcile the existing durable job instead of blindly reposting.',
    safeToRetryUnchanged: false,
    needsMoreRay: false
  },
  {
    failureClass: 'VERIFY_FAILURE',
    confidence: 0.90,
    pattern: /\b(VERIFY_FAILED|verification failed|assert(?:ion)?.*fail|exit[_ -]?code.?[1-9])\b/i,
    summary: 'Verification failed.',
    recommendedAction: 'Hydrate stdout/stderr, identify the failing assertion and Ray only the implicated sources before producing a new VRA.',
    safeToRetryUnchanged: false,
    needsMoreRay: true
  }
]

export class JudgeCore {
  evaluate(digest: WorkstationEvidenceDigest, signals: SensorSignal[]): JudgeDecision {
    const signalText = signals.map(signal => `${signal.code} ${signal.message}`).join('\n')
    const haystack = `${digest.rawFailureText}\n${signalText}`

    if (digest.verified === true && digest.success !== false && digest.result !== 'failed') {
      return {
        failureClass: 'NONE',
        confidence: 1,
        summary: 'Evidence is verified and no failure signal is present.',
        recommendedAction: 'No repair VRA is required.',
        safeToRetryUnchanged: true,
        needsMoreRay: false,
        signals: signals.map(signal => signal.code)
      }
    }

    for (const rule of RULES) {
      if (!rule.pattern.test(haystack)) continue
      return {
        failureClass: rule.failureClass,
        confidence: rule.confidence,
        summary: rule.summary,
        recommendedAction: rule.recommendedAction,
        safeToRetryUnchanged: rule.safeToRetryUnchanged,
        needsMoreRay: rule.needsMoreRay,
        signals: signals.map(signal => signal.code)
      }
    }

    const unavailableStreams = !digest.stdout && !digest.stderr
    return {
      failureClass: unavailableStreams ? 'EVIDENCE_UNAVAILABLE' : 'UNKNOWN',
      confidence: unavailableStreams ? 0.82 : 0.55,
      summary: unavailableStreams
        ? 'Evidence indicates failure but command streams are not available to Judge.'
        : 'Failure is present but no deterministic rule matched.',
      recommendedAction: unavailableStreams
        ? 'Hydrate bounded stdout/stderr through Ray before creating a repair VRA.'
        : 'Run a scoped Deep Ray around the evidence paths and failing command.',
      safeToRetryUnchanged: false,
      needsMoreRay: true,
      signals: signals.map(signal => signal.code)
    }
  }
}
