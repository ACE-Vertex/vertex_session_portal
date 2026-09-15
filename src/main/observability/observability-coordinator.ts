import {
  OBSERVABILITY_CONTRACT,
  type DeepRayReport,
  type ObservabilityAnalysis,
  type SensorSignal
} from './contracts'
import { BlackBox } from './black-box'
import { EvidenceIntelligence } from './evidence-intelligence'
import { GuardCore } from './guard-core'
import { ImpactCore } from './impact-core'
import { JudgeCore } from './judge-core'
import { RayCore, type DeepRayOptions } from './ray-core'
import { SensorCore } from './sensor-core'
import { redactSensitiveText } from './redaction'

export class ObservabilityCoordinator {
  readonly ray: RayCore
  readonly sensor: SensorCore
  readonly judge: JudgeCore
  readonly impact: ImpactCore
  readonly guard: GuardCore
  readonly blackBox: BlackBox
  readonly evidence: EvidenceIntelligence

  constructor(allowedReadRoots: string[]) {
    this.ray = new RayCore(allowedReadRoots)
    this.sensor = new SensorCore()
    this.judge = new JudgeCore()
    this.impact = new ImpactCore()
    this.guard = new GuardCore(allowedReadRoots)
    this.blackBox = new BlackBox()
    this.evidence = new EvidenceIntelligence()
  }

  async inspect(root: string, options: DeepRayOptions = {}): Promise<{
    report: DeepRayReport
    signals: SensorSignal[]
  }> {
    const report = await this.ray.deepScan(root, options)
    const signals = this.sensor.observeRay(report)
    this.blackBox.append('RAY_DEEP_SCAN', {
      root: report.root,
      nodes: report.tree.nodes.length,
      sourceFiles: report.sourceFiles.length,
      edges: report.edges.length,
      manifests: report.manifests.length,
      truncated: report.truncated,
      signals: signals.map(signal => signal.code)
    })
    return { report, signals }
  }

  async analyzeWorkstationEvidence(raw: unknown): Promise<ObservabilityAnalysis> {
    const hydratedLogs: ObservabilityAnalysis['hydratedLogs'] = []
    let stdout = ''
    let stderr = ''

    for (const log of this.evidence.commandLogPaths(raw).slice(0, 16)) {
      try {
        const read = await this.ray.readText(log.path, 64 * 1024, true)
        const safeText = redactSensitiveText(read.text)
        hydratedLogs.push({
          kind: log.kind,
          path: log.path,
          available: true,
          text: safeText,
          error: null
        })
        if (log.kind === 'stdout') stdout += `${safeText}\n`
        else stderr += `${safeText}\n`
      } catch (error) {
        hydratedLogs.push({
          kind: log.kind,
          path: log.path,
          available: false,
          text: null,
          error: redactSensitiveText(error instanceof Error ? error.message : String(error))
        })
      }
    }

    const digest = this.evidence.digest(raw, {
      stdout: stdout || null,
      stderr: stderr || null
    })
    const signals = this.sensor.observeEvidence(digest)
    const judge = this.judge.evaluate(digest, signals)

    const analysis: ObservabilityAnalysis = {
      schema: OBSERVABILITY_CONTRACT,
      digest,
      signals,
      judge,
      hydratedLogs
    }
    this.blackBox.append('WORKSTATION_EVIDENCE_ANALYSIS', analysis)
    return analysis
  }
}

export function createObservabilityCoordinator(allowedReadRoots: string[]): ObservabilityCoordinator {
  return new ObservabilityCoordinator(allowedReadRoots)
}
