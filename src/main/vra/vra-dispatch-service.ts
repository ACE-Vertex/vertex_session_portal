import { createHash, randomUUID } from 'node:crypto'
import {
  appendFileSync,
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  realpathSync,
  renameSync,
  statSync,
  unlinkSync,
  writeFileSync
} from 'node:fs'
import { basename, dirname, extname, isAbsolute, join, relative } from 'node:path'
import { deflateRawSync, inflateRawSync } from 'node:zlib'
import type { Session, WebContents } from 'electron'
import type {
  RegisterVraWebviewSourceRequest,
  VraDispatchCard,
  VraDispatchState,
  VraEvidenceDeliveryAckRequest,
  VraEvidenceDeliveryAckResult,
  WorkstationSafetyAction,
  WorkstationSafetyActionRequest,
  WorkstationSafetyActionResult,
  WorkstationSafetyMetrics,
  WorkstationSafetyObservation,
  WorkstationSafetyState,
  WorkstationSafetyTransition
} from '../../shared/contracts'
import { getVraDispatchDestination } from './vra-dispatch-destination-store'
import { WorkstationClient, WorkstationHttpError } from '../workstation/workstation-client'
import { EvidenceReturnObservabilityTap } from '../observability/evidence-return-tap'
import { createVraRegistryRuntime, type VraRegistryRuntime } from '../vra-registry/vra-registry-runtime'
import { admitAutoRegistryCandidate } from '../vra-registry/auto-registry-intake-adapter'
import { syncAutoRegistryWorkstationLifecycle } from '../vra-registry/auto-registry-workstation-sync'
import { registryAllowsEvidenceReturn } from '../vra-registry/auto-registry-return-route-guard'
import { dispatchVeraVxsRequest } from '../shell/vxs/vera-vxs-request-bridge'

type ChangedListener = () => void
type VraOriginVera = 'VERA01' | 'VERA02' | 'VERA03' | 'VERA04' | 'VERA05' | 'UNKNOWN'
type VraHumanApproval = 'PENDING' | 'APPROVED'
type ExternalLanePolicy = 'ANY' | 'PREFER'
type VraDispatchPhase = 'CAPTURING' | 'STAGED' | 'APPROVED' | 'PUBLISHED' | 'ERROR' | 'REMOVED'
type VraStagingMetadataStatus = 'CAPTURING' | 'STAGED' | 'DISPATCHED' | 'ERROR' | 'REMOVED'
type WorkstationRegistrationState = 'NOT_READY' | 'PENDING' | 'REGISTERING' | 'REGISTERED' | 'BLOCKED'
type WorkstationJobState = 'REGISTERED' | 'DISPATCHED' | 'EXECUTING' | 'SUCCEEDED' | 'FAILED' | 'REJECTED' | 'ROLLED_BACK'

const VRA_ROUTING_CONTRACT_VERSION = 'vra-routing/1' as const
const DEFAULT_RETURN_CHANNEL = 'vertex-session-portal:return-queue' as const
const MAX_LANE_PARALLELISM = 32
const VRA_TEST_CARD_KIND = 'TEST' as const
const TEST_RERUN_EXPORT_PREFIX = 'vertex-test-rerun:'
const AUTO_AUTHORITY_COMMAND_PREFIX = 'vertex-auto-authority:'
const AUTO_DISPATCH_COMMAND_PREFIX = 'vertex-auto-dispatch:'
const VXS_REQUEST_COMMAND_PREFIX = 'vertex-vxs-request:'
const AUTO_AUTHORITY_SCHEMA = 'vertex-session-portal/auto-authority-1' as const
const AUTO_AUTHORITY_LEDGER_SCHEMA = 'vertex-session-portal/auto-authority-ledger-1' as const
const AUTO_AUTHORITY_TTL_MS = 12 * 60 * 60 * 1000

type VraCardKind = typeof VRA_TEST_CARD_KIND | null

type AutoAuthorityLease = {
  schema: typeof AUTO_AUTHORITY_SCHEMA
  authority_id: string
  controller_session: string
  allowed_sessions: string[]
  granted_utc: string
  expires_utc: string
  status: 'ACTIVE' | 'REVOKED'
  revoked_utc: string | null
  revoke_reason: string | null
}

type AutoAuthorityLedger = {
  schema: typeof AUTO_AUTHORITY_LEDGER_SCHEMA
  authorities: AutoAuthorityLease[]
}

interface ImmutableVraOrigin {
  readonly originVera: VraOriginVera
  readonly originSession: string
  readonly originWindow: string
}

interface VraManifestMetadata {
  contractVersion: typeof VRA_ROUTING_CONTRACT_VERSION
  jobId: string
  returnChannel: string
  projectId: string | null
  projectName: string | null
  artifactId: string | null
  jobTitle: string | null
  requestedLane: string | null
  lanePolicy: ExternalLanePolicy
  parallelism: number
  workerConcurrency: number | null
  correlationId: string
  cardKind: VraCardKind
  rerunOfJobId: string | null
  testRunId: string | null
}

type DurableVraDispatchCard = VraDispatchCard & {
  readonly originVera: VraOriginVera
  readonly originSession: string | null
  readonly originWindow: string | null
  routingContractVersion: typeof VRA_ROUTING_CONTRACT_VERSION
  jobId: string
  returnChannel: string
  projectId: string | null
  projectName: string | null
  artifactId: string | null
  jobTitle: string | null
  requestedLane: string | null
  lanePolicy: ExternalLanePolicy
  allocatedLane: string | null
  parallelism: number
  workerConcurrency: number | null
  correlationId: string
  cardKind: VraCardKind
  rerunOfJobId: string | null
  testRunId: string | null
  humanApproval: VraHumanApproval
  dispatchPhase: VraDispatchPhase
  publishName: string | null
  workstationRegistration: WorkstationRegistrationState
  workstationJobState: WorkstationJobState | null
  workstationEvidenceState: string | null
  workstationEvidenceReturnState: string | null
  workstationLastError: string | null
  registrationAttemptUtc: string | null
  registeredUtc: string | null
  evidenceIdentity: string | null
  evidenceCacheName: string | null
}

interface VraStagingMetadata {
  schema_version: 'vertex/vra-staging-metadata/1'
  contract_version: typeof VRA_ROUTING_CONTRACT_VERSION
  capture_id: string
  job_id: string
  correlation_id: string
  return_channel: string
  filename: string
  staged_name: string
  publish_name: string | null
  source_web_contents_id: number | null
  origin_vera: VraOriginVera
  origin_session: string | null
  origin_window: string | null
  project_id: string | null
  project_name: string | null
  artifact_id: string | null
  title: string | null
  requested_lane: string | null
  lane_policy: ExternalLanePolicy
  allocated_lane: string | null
  parallelism: number
  worker_concurrency: number | null
  card_kind?: typeof VRA_TEST_CARD_KIND | null
  rerun_of_job_id?: string | null
  test_run_id?: string | null
  human_approval: VraHumanApproval
  dispatch_phase: VraDispatchPhase
  status: VraStagingMetadataStatus
  captured_utc: string
  dispatched_utc: string | null
  size_bytes: number | null
  sha256: string | null
  workstation_registration?: WorkstationRegistrationState
  workstation_job_state?: WorkstationJobState | null
  workstation_evidence_state?: string | null
  workstation_evidence_return_state?: string | null
  workstation_last_error?: string | null
  registration_attempt_utc?: string | null
  registered_utc?: string | null
  evidence_identity?: string | null
  evidence_cache_name?: string | null
  error: string | null
}

interface PersistedLedger {
  cards: DurableVraDispatchCard[]
}

/**
 * WORKSTATION_DISPATCH_CARD_000052V1H2
 * Canonical VRA flow:
 * ChatGPT browser -> Portal-owned staging -> Dispatch Bay card ->
 * (Human EXPORT to configured folder) OR (explicit Human Workstation dispatch).
 *
 * This class is the ONE AND ONLY owner of .vra `will-download` capture.
 */
export class VraDispatchService {
  private readonly stagingRoot: string
  private readonly ledgerPath: string
  private readonly autoAuthorityPath: string
  private readonly autoAuthorityAuditPath: string
  private readonly webviewSources = new Map<number, string>()
  private readonly listeners = new Set<ChangedListener>()
  private cards: DurableVraDispatchCard[] = []
  private autoAuthorities: AutoAuthorityLease[] = []
  private attached = false
  private readonly workstation = new WorkstationClient()
  private readonly workstationInFlight = new Set<string>()
  private readonly evidenceObservability: EvidenceReturnObservabilityTap
  private readonly registryRuntime: VraRegistryRuntime
  private readonly autoRegistryInFlight = new Set<string>()
  // 000093V5H2: both the main 2500 ms timer and the renderer pull-through poll
  // enter reconcileWorkstation(). Coalesce the whole cycle so refreshState()
  // can never return a snapshot from the middle of another reconciliation.
  private workstationReconcileInFlight: Promise<void> | null = null
  private autoDispatchScanTimer: ReturnType<typeof setTimeout> | null = null
  // 000105V5: immediately after Human dispatch, Scheduler/lane truth may become
  // authoritative before the normal 2500 ms observation tick.  Keep a short,
  // coalesced /v1/safety observation burst so the Header sees the first lane
  // without inventing optimistic BUSY state.
  private workstationPostDispatchProbeInFlight: Promise<void> | null = null
  private workstationPostDispatchProbeDeadlineMs = 0
  private workstationTimer: ReturnType<typeof setInterval> | null = null
  private workstationOnline = false
  private workstationObservedUtc: string | null = null
  private workstationSafety: WorkstationSafetyObservation = {
    schema: null,
    online: false,
    state: 'UNKNOWN',
    generation: null,
    latched: null,
    newWorkAllowed: null,
    activeContinuationAllowed: null,
    autoReset: null,
    autoResume: null,
    lastTransition: null,
    metrics: null,
    executionPlane: 'UNKNOWN',
    observationPlane: 'UNKNOWN',
    evidenceReturnPlane: 'UNKNOWN',
    observedUtc: new Date().toISOString(),
    lastError: 'WORKSTATION_SAFETY_NOT_OBSERVED'
  }

  constructor(
    userDataRoot: string,
    private readonly worksIncomingRoot: string
  ) {
    this.stagingRoot = join(userDataRoot, 'vra-dispatch')
    this.ledgerPath = join(this.stagingRoot, 'ledger.json')
    this.autoAuthorityPath = join(this.stagingRoot, 'auto-authorities.json')
    this.autoAuthorityAuditPath = join(this.stagingRoot, 'auto-authority-audit.jsonl')
    this.evidenceObservability = new EvidenceReturnObservabilityTap(this.stagingRoot, this.worksIncomingRoot)
    this.registryRuntime = createVraRegistryRuntime(userDataRoot)
    mkdirSync(this.stagingRoot, { recursive: true })
    this.autoAuthorities = this.loadAutoAuthorities()
    this.revokeAutoAuthoritiesOnStartup()
    this.cards = this.loadLedger()
    this.startWorkstationReconciler()
  }

  attachToSession(target: Session): void {
    if (this.attached) return
    this.attached = true

    target.on('will-download', (_event, item, webContents) => {
      const filename = basename(item.getFilename() || 'vertex-artifact.vra')
      if (extname(filename).toLowerCase() !== '.vra') return

      // WORKSTATION_DISPATCH_CARD_000052V1H2:
      // Origin is a capture prerequisite, not renderer enrichment. A new .vra from an
      // unregistered webContents is cancelled before any staging sidecar or save path exists.
      const origin = this.captureOrigin(webContents)
      if (!origin) {
        item.cancel()
        console.warn('VRA_ORIGIN_UNRESOLVED')
        return
      }

      const captureId = randomUUID()
      const stagedName = `${Date.now()}-${captureId.slice(0, 8)}-${filename}`
      const stagedPath = join(this.stagingRoot, stagedName)
      const capturedUtc = new Date().toISOString()

      try {
        this.writeStagingMetadata(
          stagedPath,
          this.captureSeed(captureId, filename, stagedName, webContents.id, origin, capturedUtc)
        )
      } catch {
        item.cancel()
        return
      }

      // STAGING FIRST. Never point browser download directly at Human Export or _incoming.
      item.setSavePath(stagedPath)

      item.once('done', (_doneEvent, state) => {
        if (state !== 'completed' || !existsSync(stagedPath)) {
          this.markIncompleteCapture(stagedPath)
          return
        }
        this.captureCompleted(
          captureId,
          filename,
          stagedPath,
          origin,
          webContents.id,
          capturedUtc
        )
      })
    })
  }

  registerWebviewSource(request: RegisterVraWebviewSourceRequest): void {
    const sessionId = request.sessionId.trim()
    if (!/^vera-0[1-5]$/.test(sessionId)) {
      throw new Error('VRA_DISPATCH_INVALID_VERA_SESSION')
    }

    if (!Number.isInteger(request.webContentsId) || request.webContentsId <= 0) {
      throw new Error('VRA_DISPATCH_INVALID_WEB_CONTENTS_ID')
    }

    this.webviewSources.set(request.webContentsId, sessionId)
  }

  state(): VraDispatchState {
    return {
      stagingRoot: this.stagingRoot,
      worksIncomingRoot: this.worksIncomingRoot,
      // 000096V5: renderer gets one durable Evidence head per origin session.
      // Returned Evidence is never re-exposed and later Evidence waits behind the head.
      cards: this.cardsForRenderer(),
      workstationOnline: this.workstationOnline,
      workstationObservedUtc: this.workstationObservedUtc,
      // 000098V5: Header Lane Pulse is observation-only and must have one current
      // authority.  Never project durable lastTransition lane history as current
      // activity.  Both renderer-visible lane arrays derive from the normalized
      // current metrics.activeLanes produced by 000096V5.
      workstationSafety: {
        ...this.workstationSafety,
        metrics: this.workstationSafety.metrics
          ? { ...this.workstationSafety.metrics, activeLanes: [...this.workstationSafety.metrics.activeLanes] }
          : null,
        lastTransition: this.workstationSafety.lastTransition
          ? {
              ...this.workstationSafety.lastTransition,
              activeLanes: this.workstationSafety.metrics
                ? [...this.workstationSafety.metrics.activeLanes]
                : []
            }
          : null
      }
    }
  }

  /**
   * 000076V5: pull-through reconciliation boundary.
   * Renderer state reads may actively reconcile Workstation before returning.
   * This closes the restart gap where durable Workstation Evidence can advance
   * while the Portal card/sidecar remains on an older REGISTERED snapshot.
   */
  async refreshState(): Promise<VraDispatchState> {
    await this.reconcileWorkstation()
    return this.state()
  }

  /** Human EXPORT: copy staged VRA to the folder selected in Dispatch Bay. */
  exportCard(cardId: string): string {
    // 000106V5 ARD compatibility tunnel:
    // Reuse the already trusted preload/IPC string boundary.  Main process owns
    // authority validation; renderer/localStorage can never authorize a dispatch.
    if (cardId.startsWith(AUTO_AUTHORITY_COMMAND_PREFIX)) {
      return this.handleAutoAuthorityCommand(cardId.slice(AUTO_AUTHORITY_COMMAND_PREFIX.length))
    }
    if (cardId.startsWith(AUTO_DISPATCH_COMMAND_PREFIX)) {
      return this.handleAutoDispatchCommand(cardId.slice(AUTO_DISPATCH_COMMAND_PREFIX.length))
    }
    if (cardId.startsWith(VXS_REQUEST_COMMAND_PREFIX)) {
      return dispatchVeraVxsRequest(cardId.slice(VXS_REQUEST_COMMAND_PREFIX.length))
    }

    // 000102V5 compatibility tunnel:
    // Keep the existing preload/IPC contract unchanged. A renderer-issued TEST-only
    // re-run request is encoded inside the existing string argument and revalidated
    // here in the trusted main process. Production cards fail closed.
    if (cardId.startsWith(TEST_RERUN_EXPORT_PREFIX)) {
      const sourceCardId = cardId.slice(TEST_RERUN_EXPORT_PREFIX.length).trim()
      if (!sourceCardId) throw new Error('VRA_TEST_RERUN_SOURCE_CARD_REQUIRED')
      return this.stageTestCardRerun(sourceCardId)
    }

    const card = this.requireHealthyStagedCard(cardId)
    const exportRoot = getVraDispatchDestination()
    mkdirSync(exportRoot, { recursive: true })
    const destination = this.safeDestination(exportRoot, card)

    if (!existsSync(destination) || this.sha256(destination) !== card.sha256) {
      copyFileSync(card.stagedPath, destination)
    }

    // Export is intentionally non-destructive. Card/staging remains available.
    return destination
  }

  private handleAutoAuthorityCommand(command: string): string {
    if (command.startsWith('grant:')) {
      const encoded = command.slice('grant:'.length)
      const payload = this.requireRecord(
        JSON.parse(decodeURIComponent(encoded)) as unknown,
        'ARD_AUTO_AUTHORITY_GRANT_PAYLOAD_INVALID'
      )
      const authorityId = this.requiredString(payload.authority_id, 'ARD_AUTO_AUTHORITY_ID_REQUIRED')
      const controllerSession = this.requireAutoSession(
        payload.controller_session,
        'ARD_AUTO_CONTROLLER_SESSION_INVALID'
      )
      const allowedSessions = this.requireStringArray(
        payload.allowed_sessions,
        'ARD_AUTO_ALLOWED_SESSIONS_INVALID'
      ).map(value => this.requireAutoSession(value, 'ARD_AUTO_ALLOWED_SESSION_INVALID'))
      const uniqueAllowed = [...new Set(allowedSessions)]
      if (!uniqueAllowed.length || uniqueAllowed.length > 5) throw new Error('ARD_AUTO_ALLOWED_SESSIONS_RANGE')
      if (!uniqueAllowed.includes(controllerSession)) throw new Error('ARD_AUTO_CONTROLLER_SCOPE_REQUIRED')
      if (!/^[A-Za-z0-9_-]{8,128}$/.test(authorityId)) throw new Error('ARD_AUTO_AUTHORITY_ID_INVALID')

      const now = new Date()
      const lease: AutoAuthorityLease = {
        schema: AUTO_AUTHORITY_SCHEMA,
        authority_id: authorityId,
        controller_session: controllerSession,
        allowed_sessions: uniqueAllowed.sort(),
        granted_utc: now.toISOString(),
        expires_utc: new Date(now.getTime() + AUTO_AUTHORITY_TTL_MS).toISOString(),
        status: 'ACTIVE',
        revoked_utc: null,
        revoke_reason: null
      }

      // A second Human AUTO arm by the same controller supersedes the previous lease.
      for (const row of this.autoAuthorities) {
        if (row.status !== 'ACTIVE' || row.controller_session !== controllerSession) continue
        row.status = 'REVOKED'
        row.revoked_utc = now.toISOString()
        row.revoke_reason = 'SUPERSEDED_BY_HUMAN_AUTO_ARM'
        this.auditAutoAuthority('AUTO_AUTHORITY_REVOKED', row, null, null)
      }

      this.autoAuthorities = this.autoAuthorities.filter(row => row.authority_id !== authorityId)
      this.autoAuthorities.push(lease)
      this.persistAutoAuthorities()
      this.auditAutoAuthority('AUTO_AUTHORITY_GRANTED', lease, null, null)
      // 000109V5: Human AUTO arm is the execution authority grant.
      // Old cards remain excluded by captured_utc >= granted_utc.
      this.scheduleAutoAuthorizedDispatchScan()
      return JSON.stringify(lease)
    }

    if (command.startsWith('revoke:')) {
      const authorityId = decodeURIComponent(command.slice('revoke:'.length)).trim()
      const lease = this.autoAuthorities.find(row => row.authority_id === authorityId)
      if (!lease) return JSON.stringify({ authority_id: authorityId, status: 'REVOKED', idempotent: true })
      if (lease.status === 'ACTIVE') {
        lease.status = 'REVOKED'
        lease.revoked_utc = new Date().toISOString()
        lease.revoke_reason = 'HUMAN_AUTO_DISARM'
        this.persistAutoAuthorities()
        this.auditAutoAuthority('AUTO_AUTHORITY_REVOKED', lease, null, null)
      }
      return JSON.stringify(lease)
    }

    throw new Error('ARD_AUTO_AUTHORITY_COMMAND_UNSUPPORTED')
  }

  private handleAutoDispatchCommand(encoded: string): string {
    const payload = this.requireRecord(
      JSON.parse(decodeURIComponent(encoded)) as unknown,
      'ARD_AUTO_DISPATCH_PAYLOAD_INVALID'
    )
    const authorityId = this.requiredString(payload.authority_id, 'ARD_AUTO_DISPATCH_AUTHORITY_REQUIRED')
    const cardId = this.requiredString(payload.card_id, 'ARD_AUTO_DISPATCH_CARD_REQUIRED')
    const parentTaskId = this.optionalString(payload.parent_task_id)
    if (parentTaskId && parentTaskId.length > 256) throw new Error('ARD_AUTO_PARENT_TASK_ID_TOO_LARGE')

    const card = this.cards.find(candidate => candidate.id === cardId)
    if (!card) throw new Error('VRA_CARD_NOT_FOUND')
    const lease = this.requireActiveAutoAuthority(authorityId, card)

    // Main-owned fallback and renderer routing can converge on the same card.
    // Treat a previously published card as an idempotent success, never a second APPLY.
    if (
      card.status === 'DISPATCHED'
      && card.humanApproval === 'APPROVED'
      && card.dispatchPhase === 'PUBLISHED'
    ) {
      this.auditAutoAuthority('AUTO_VRA_DISPATCH_IDEMPOTENT', lease, card, parentTaskId)
      return card.worksPath ?? ''
    }

    const staged = this.requireHealthyStagedCard(cardId)
    if (
      !this.workstationOnline
      || this.workstationSafety.online !== true
      || this.workstationSafety.state !== 'RUNNING'
      || this.workstationSafety.newWorkAllowed !== true
    ) {
      throw new Error('ARD_AUTO_WORKSTATION_NEW_WORK_NOT_ALLOWED')
    }

    // 000146V5: legacy renderer AUTO commands are queue signals only.
    // Actual publication occurs exclusively in the async main-process reconciliation
    // after Registry admission succeeds. This closes the AUTO -> publish bypass while
    // preserving the existing synchronous preload/IPC string contract.
    this.scheduleAutoAuthorizedDispatchScan(0)
    this.auditAutoAuthority('AUTO_VRA_REGISTRY_QUEUED', lease, staged, parentTaskId)
    return `REGISTRY_QUEUED:${staged.id}`
  }

  private requireActiveAutoAuthority(
    authorityId: string,
    card: DurableVraDispatchCard
  ): AutoAuthorityLease {
    const lease = this.autoAuthorities.find(row => row.authority_id === authorityId)
    if (!lease || lease.status !== 'ACTIVE') throw new Error('ARD_AUTO_AUTHORITY_NOT_ACTIVE')

    const expires = Date.parse(lease.expires_utc)
    if (!Number.isFinite(expires) || expires <= Date.now()) {
      lease.status = 'REVOKED'
      lease.revoked_utc = new Date().toISOString()
      lease.revoke_reason = 'EXPIRED'
      this.persistAutoAuthorities()
      this.auditAutoAuthority('AUTO_AUTHORITY_REVOKED', lease, card, null)
      throw new Error('ARD_AUTO_AUTHORITY_EXPIRED')
    }

    if (!card.originSession || card.originVera === 'UNKNOWN') {
      throw new Error('ARD_AUTO_CARD_ORIGIN_UNRESOLVED')
    }
    if (!lease.allowed_sessions.includes(card.originSession)) {
      throw new Error('ARD_AUTO_CARD_SESSION_OUT_OF_SCOPE')
    }
    if (this.veraForSession(card.originSession) !== card.originVera) {
      throw new Error('ARD_AUTO_CARD_ORIGIN_MISMATCH')
    }

    const captured = Date.parse(card.capturedUtc)
    const granted = Date.parse(lease.granted_utc)
    if (!Number.isFinite(captured) || !Number.isFinite(granted) || captured < granted) {
      throw new Error('ARD_AUTO_PREEXISTING_CARD_FORBIDDEN')
    }

    return lease
  }

  private autoAuthorityForStagedCard(card: DurableVraDispatchCard): AutoAuthorityLease | null {
    if (
      card.status !== 'STAGED'
      || card.humanApproval !== 'PENDING'
      || card.dispatchPhase !== 'STAGED'
      || !card.originSession
      || card.originVera === 'UNKNOWN'
      || this.veraForSession(card.originSession) !== card.originVera
    ) return null

    const captured = Date.parse(card.capturedUtc)
    if (!Number.isFinite(captured)) return null

    const candidates = this.autoAuthorities.filter(lease => {
      if (lease.status !== 'ACTIVE') return false
      const granted = Date.parse(lease.granted_utc)
      return Number.isFinite(granted)
        && captured >= granted
        && lease.allowed_sessions.includes(card.originSession as string)
    })
    if (!candidates.length) return null

    // A Human AUTO arm on the card's own Vera is the strongest exact authority.
    const self = candidates.filter(lease => lease.controller_session === card.originSession)
    if (self.length === 1) return self[0]
    if (self.length > 1) return null

    // AUTO_DELEGATED parent authority is allowed only when unambiguous.
    if (candidates.length === 1) return candidates[0]

    // Multiple overlapping controllers without an exact owner are ambiguous.
    // Fail closed instead of guessing which Human delegation should authorize execution.
    return null
  }

  private async reconcileAutoAuthorizedStagedCards(): Promise<void> {
    if (
      !this.workstationOnline
      || this.workstationSafety.online !== true
      || this.workstationSafety.state !== 'RUNNING'
      || this.workstationSafety.newWorkAllowed !== true
    ) return

    for (const card of [...this.cards]) {
      const lease = this.autoAuthorityForStagedCard(card)
      if (!lease || this.autoRegistryInFlight.has(card.id)) continue

      this.autoRegistryInFlight.add(card.id)
      let registryId: string | null = null
      try {
        this.requireActiveAutoAuthority(lease.authority_id, card)

        // AUTO ONLY: Registry is the mandatory responsibility boundary before Bay publish.
        // Manual dispatch() below remains unchanged and never enters this path.
        registryId = await admitAutoRegistryCandidate(this.registryRuntime.core, {
          registryId: `auto:${card.id}`,
          jobId: card.jobId,
          artifactId: card.artifactId,
          correlationId: card.correlationId,
          projectId: card.projectId,
          projectName: card.projectName,
          requestedLane: card.requestedLane,
          lanePolicy: card.lanePolicy,
          parallelism: card.parallelism,
          workerConcurrency: card.workerConcurrency,
          originVera: card.originVera,
          originSession: card.originSession,
          originWindow: card.originWindow,
          returnChannel: card.returnChannel
        })

        const result = this.publishApprovedCard(card)

        // Publication is already durably committed at this point. A post-publish Registry
        // write failure must never pretend the VRA was not published or trigger a duplicate
        // publish. Recovery/observer can reconcile the durable card on the next pass.
        try {
          await this.registryRuntime.core.markDispatched(registryId)
        } catch (registryError) {
          this.auditAutoAuthority(
            'AUTO_VRA_REGISTRY_POST_PUBLISH_STATE_FAILED',
            lease,
            card,
            null,
            registryError instanceof Error ? registryError.message : String(registryError)
          )
        }

        this.auditAutoAuthority('AUTO_VRA_DISPATCHED_MAIN', lease, card, null)
        void result
      } catch (error) {
        // Before publish, Registry rejection/storage failure is a hard fail-closed gate.
        if (registryId && card.dispatchPhase !== 'PUBLISHED') {
          try {
            await this.registryRuntime.core.fail(registryId)
          } catch {
            // Preserve the original failure. Registry recovery can inspect durable state.
          }
        }
        this.auditAutoAuthority(
          'AUTO_VRA_DISPATCH_FAILED_MAIN',
          lease,
          card,
          null,
          error instanceof Error ? error.message : String(error)
        )
      } finally {
        this.autoRegistryInFlight.delete(card.id)
      }
    }
  }

  private scheduleAutoAuthorizedDispatchScan(delayMs = 220): void {
    if (this.autoDispatchScanTimer) return
    this.autoDispatchScanTimer = setTimeout(() => {
      this.autoDispatchScanTimer = null
      void this.reconcileWorkstation()
    }, delayMs)
    this.autoDispatchScanTimer.unref?.()
  }

  private requireAutoSession(value: unknown, message: string): string {
    const session = this.requiredString(value, message).toLowerCase()
    if (!/^vera-0[1-5]$/.test(session)) throw new Error(message)
    return session
  }

  private loadAutoAuthorities(): AutoAuthorityLease[] {
    if (!existsSync(this.autoAuthorityPath)) return []
    try {
      const parsed = this.requireRecord(
        JSON.parse(readFileSync(this.autoAuthorityPath, 'utf8')) as unknown,
        'ARD_AUTO_AUTHORITY_LEDGER_INVALID'
      )
      if (parsed.schema !== AUTO_AUTHORITY_LEDGER_SCHEMA || !Array.isArray(parsed.authorities)) return []
      return (parsed.authorities as unknown[]).flatMap(value => {
        try {
          const row = this.requireRecord(value, 'ARD_AUTO_AUTHORITY_ROW_INVALID')
          const lease: AutoAuthorityLease = {
            schema: AUTO_AUTHORITY_SCHEMA,
            authority_id: this.requiredString(row.authority_id, 'ARD_AUTO_AUTHORITY_ID_REQUIRED'),
            controller_session: this.requireAutoSession(row.controller_session, 'ARD_AUTO_CONTROLLER_SESSION_INVALID'),
            allowed_sessions: this.requireStringArray(row.allowed_sessions, 'ARD_AUTO_ALLOWED_SESSIONS_INVALID')
              .map(session => this.requireAutoSession(session, 'ARD_AUTO_ALLOWED_SESSION_INVALID')),
            granted_utc: this.requiredString(row.granted_utc, 'ARD_AUTO_GRANTED_UTC_REQUIRED'),
            expires_utc: this.requiredString(row.expires_utc, 'ARD_AUTO_EXPIRES_UTC_REQUIRED'),
            status: row.status === 'ACTIVE' ? 'ACTIVE' : 'REVOKED',
            revoked_utc: this.optionalString(row.revoked_utc),
            revoke_reason: this.optionalString(row.revoke_reason)
          }
          return [lease]
        } catch {
          return []
        }
      })
    } catch {
      return []
    }
  }

  private persistAutoAuthorities(): void {
    const ledger: AutoAuthorityLedger = {
      schema: AUTO_AUTHORITY_LEDGER_SCHEMA,
      authorities: this.autoAuthorities.slice(-128)
    }
    this.writeJsonAtomic(this.autoAuthorityPath, ledger)
  }

  private revokeAutoAuthoritiesOnStartup(): void {
    const now = new Date().toISOString()
    let changed = false
    for (const lease of this.autoAuthorities) {
      if (lease.status !== 'ACTIVE') continue
      lease.status = 'REVOKED'
      lease.revoked_utc = now
      lease.revoke_reason = 'PORTAL_PROCESS_RESTART_FAIL_CLOSED'
      this.auditAutoAuthority('AUTO_AUTHORITY_REVOKED', lease, null, null)
      changed = true
    }
    if (changed) this.persistAutoAuthorities()
  }

  private auditAutoAuthority(
    event: string,
    lease: AutoAuthorityLease,
    card: DurableVraDispatchCard | null,
    parentTaskId: string | null,
    error: string | null = null
  ): void {
    try {
      appendFileSync(
        this.autoAuthorityAuditPath,
        `${JSON.stringify({
          schema: 'vertex-session-portal/auto-authority-audit-1',
          timestamp: new Date().toISOString(),
          event,
          authority_id: lease.authority_id,
          controller_session: lease.controller_session,
          allowed_sessions: lease.allowed_sessions,
          card_id: card?.id ?? null,
          job_id: card?.jobId ?? null,
          origin_session: card?.originSession ?? null,
          parent_task_id: parentTaskId,
          error
        })}\n`,
        'utf8'
      )
    } catch {
      // Audit write failure never broadens authority; command validation still fails closed.
    }
  }

  private explicitTestCard(card: DurableVraDispatchCard): boolean {
    return card.cardKind === VRA_TEST_CARD_KIND
  }

  private settledTestCard(card: DurableVraDispatchCard): boolean {
    const terminal = new Set<WorkstationJobState>(['SUCCEEDED', 'FAILED', 'REJECTED', 'ROLLED_BACK'])
    return Boolean(
      this.explicitTestCard(card) &&
      card.status === 'DISPATCHED' &&
      card.humanApproval === 'APPROVED' &&
      card.dispatchPhase === 'PUBLISHED' &&
      card.workstationJobState &&
      terminal.has(card.workstationJobState) &&
      card.workstationEvidenceReturnState === 'RETURNED'
    )
  }

  private requireTestRerunSource(cardId: string): DurableVraDispatchCard {
    const card = this.requireHealthyStagedCard(cardId)
    if (!this.explicitTestCard(card)) {
      throw new Error('VRA_TEST_RERUN_NON_TEST_DENIED')
    }
    if (!this.settledTestCard(card)) {
      throw new Error('VRA_TEST_RERUN_SOURCE_NOT_SETTLED')
    }

    const manifest = this.readVraManifest(card.stagedPath)
    if (!manifest || this.scalar(manifest.card_kind) !== VRA_TEST_CARD_KIND) {
      throw new Error('VRA_TEST_RERUN_MANIFEST_TEST_MARKER_REQUIRED')
    }

    const unfinishedChild = this.cards.find(candidate =>
      candidate.rerunOfJobId === card.jobId && !this.settledTestCard(candidate)
    )
    if (unfinishedChild) {
      throw new Error('VRA_TEST_RERUN_CHILD_ALREADY_PENDING')
    }

    return card
  }

  private stageTestCardRerun(cardId: string): string {
    const source = this.requireTestRerunSource(cardId)
    const sourceManifest = this.readVraManifest(source.stagedPath)
    if (!sourceManifest) throw new Error('VRA_TEST_RERUN_MANIFEST_UNREADABLE')

    const sourceRouting = this.asRecord(sourceManifest.routing)
    if (!sourceRouting) throw new Error('VRA_TEST_RERUN_ROUTING_REQUIRED')

    const captureId = randomUUID()
    const testRunId = randomUUID()
    const stamp = Date.now()
    const baseArtifactId =
      this.scalar(sourceManifest.artifact_id) ??
      source.artifactId ??
      `vertex-test-${captureId.slice(0, 8)}`
    const nextArtifactId = `${baseArtifactId}-r${stamp.toString(36)}-${testRunId.slice(0, 6)}`
    const nextJobId = `job-${nextArtifactId}`
    const nextCorrelationId = `corr-${testRunId}`
    const nextFilename = `${nextArtifactId}.vra`
    const nextCapturedUtc = new Date().toISOString()
    const stagedName = `${stamp}-${captureId.slice(0, 8)}-${nextFilename}`
    const stagedPath = join(this.stagingRoot, basename(stagedName))
    const tempPath = `${stagedPath}.rerun.tmp-${process.pid}-${stamp}`

    const nextRouting: Record<string, unknown> = {
      ...sourceRouting,
      contract_version: VRA_ROUTING_CONTRACT_VERSION,
      job_id: nextJobId,
      origin_vera: source.originVera,
      origin_session: source.originSession,
      origin_window: source.originWindow,
      return_channel: source.returnChannel,
      correlation_id: nextCorrelationId
    }
    delete nextRouting.allocated_lane
    delete nextRouting.execution_lane
    delete nextRouting.require_lane

    const sourceTitle =
      this.scalar(sourceManifest.title) ??
      this.scalar(sourceManifest.job_summary) ??
      source.jobTitle ??
      source.filename

    const nextManifest: Record<string, unknown> = {
      ...sourceManifest,
      artifact_id: nextArtifactId,
      title: `${sourceTitle} / RE-RUN`,
      card_kind: VRA_TEST_CARD_KIND,
      test_run: {
        schema: 'vertex-test-run/1',
        run_id: testRunId,
        rerun_of_job_id: source.jobId,
        template_artifact_id: source.artifactId ?? baseArtifactId
      },
      routing: nextRouting
    }

    mkdirSync(this.stagingRoot, { recursive: true })
    copyFileSync(source.stagedPath, tempPath)

    try {
      this.rewriteVraManifestAtomic(tempPath, nextManifest)
      const committed = this.readVraManifest(tempPath)
      const committedRouting = this.asRecord(committed?.routing)
      const committedTestRun = this.asRecord(committed?.test_run)

      if (
        this.scalar(committed?.artifact_id) !== nextArtifactId ||
        this.scalar(committed?.card_kind) !== VRA_TEST_CARD_KIND ||
        this.scalar(committedRouting?.job_id) !== nextJobId ||
        this.scalar(committedRouting?.correlation_id) !== nextCorrelationId ||
        this.scalar(committedRouting?.origin_vera) !== source.originVera ||
        this.scalar(committedRouting?.origin_session) !== source.originSession ||
        this.scalar(committedRouting?.origin_window) !== source.originWindow ||
        this.scalar(committedTestRun?.run_id) !== testRunId ||
        this.scalar(committedTestRun?.rerun_of_job_id) !== source.jobId
      ) {
        throw new Error('VRA_TEST_RERUN_COMMIT_VERIFY_FAILED')
      }

      renameSync(tempPath, stagedPath)

      const manifest = this.readManifestMetadata(stagedPath, captureId, true)
      if (
        manifest.cardKind !== VRA_TEST_CARD_KIND ||
        manifest.jobId !== nextJobId ||
        manifest.artifactId !== nextArtifactId ||
        manifest.correlationId !== nextCorrelationId ||
        manifest.rerunOfJobId !== source.jobId ||
        manifest.testRunId !== testRunId
      ) {
        throw new Error('VRA_TEST_RERUN_METADATA_VERIFY_FAILED')
      }

      const stat = statSync(stagedPath)
      const card: DurableVraDispatchCard = {
        id: captureId,
        filename: nextFilename,
        sourceSessionId: source.originSession,
        sourceWebContentsId: source.sourceWebContentsId,
        stagedPath,
        sizeBytes: stat.size,
        sha256: this.sha256(stagedPath),
        status: 'STAGED',
        capturedUtc: nextCapturedUtc,
        dispatchedUtc: null,
        worksPath: null,
        error: null,
        originVera: source.originVera,
        originSession: source.originSession,
        originWindow: source.originWindow,
        routingContractVersion: manifest.contractVersion,
        jobId: manifest.jobId,
        returnChannel: manifest.returnChannel,
        projectId: manifest.projectId,
        projectName: manifest.projectName,
        artifactId: manifest.artifactId,
        jobTitle: manifest.jobTitle,
        requestedLane: manifest.requestedLane,
        lanePolicy: manifest.lanePolicy,
        allocatedLane: null,
        parallelism: manifest.parallelism,
        workerConcurrency: manifest.workerConcurrency,
        correlationId: manifest.correlationId,
        cardKind: manifest.cardKind,
        rerunOfJobId: manifest.rerunOfJobId,
        testRunId: manifest.testRunId,
        humanApproval: 'PENDING',
        dispatchPhase: 'STAGED',
        publishName: null,
        workstationRegistration: 'NOT_READY',
        workstationJobState: null,
        workstationEvidenceState: null,
        workstationEvidenceReturnState: null,
        workstationLastError: null,
        registrationAttemptUtc: null,
        registeredUtc: null,
        evidenceIdentity: null,
        evidenceCacheName: null
      }

      this.writeStagingMetadata(stagedPath, this.metadataFromCard(card))
      this.cards.push(card)
      this.persistAndEmit()
      return stagedPath
    } catch (error) {
      for (const candidate of [tempPath, stagedPath]) {
        if (!existsSync(candidate)) continue
        try {
          unlinkSync(candidate)
        } catch {
          // Fail closed: no card is added unless archive and sidecar commit.
        }
      }
      throw error
    }
  }

  /**
   * Explicit Human dispatch boundary.
   * Portal only records the requested lane; allocatedLane remains Workstation authority.
   */
  dispatch(cardId: string): VraDispatchCard {
    const card = this.requireHealthyStagedCard(cardId)
    return this.publishApprovedCard(card)
  }

  private publishApprovedCard(card: DurableVraDispatchCard): VraDispatchCard {
    mkdirSync(this.worksIncomingRoot, { recursive: true })
    const destination = join(this.worksIncomingRoot, this.workstationArtifactFilename(card))

    // VERA4 filesystem transaction boundary:
    // 1) durable Human Approval commit, 2) temporary copy, 3) SHA256 verify,
    // 4) atomic rename into _incoming, 5) final sidecar commit.
    // HTTP POST /v1/jobs intentionally remains a Final Integration concern.
    card.humanApproval = 'APPROVED'
    card.dispatchPhase = 'APPROVED'
    card.publishName = basename(destination)
    card.error = null
    this.writeStagingMetadata(card.stagedPath, this.metadataFromCard(card))
    this.persistAndEmit()

    try {
      this.publishToIncomingAtomic(card, destination)
    } catch (error) {
      card.status = 'ERROR'
      card.error = `WORKSTATION_DISPATCH_PUBLISH_FAILED:${error instanceof Error ? error.message : String(error)}`
      // Approval is never silently revoked after its durable commit. A Human retry can
      // reconcile an already-renamed final file or perform a fresh atomic publication.
      card.dispatchPhase = 'APPROVED'
      this.writeStagingMetadata(card.stagedPath, this.metadataFromCard(card))
      this.persistAndEmit()
      throw error
    }

    card.status = 'DISPATCHED'
    card.dispatchPhase = 'PUBLISHED'
    card.dispatchedUtc = new Date().toISOString()
    card.worksPath = destination
    card.error = null
    card.workstationRegistration = 'PENDING'
    card.workstationLastError = null
    // Never assign allocatedLane here. Final Lane Allocation Authority is Workstation.
    // Filesystem = Data Commit. HTTP = Control Registration.
    const finalMetadata = this.metadataFromCard(card)
    this.writeStagingMetadata(card.stagedPath, finalMetadata)
    this.publishIncomingCommitSidecar(card, finalMetadata)
    this.persistAndEmit()
    void this.observePostDispatchLaneTruth(card.id)
    return { ...card }
  }

  remove(cardId: string): VraDispatchState {
    const index = this.cards.findIndex(card => card.id === cardId)
    if (index < 0) return this.state()

    const card = this.cards[index]
    // Tombstone first so a process kill cannot resurrect a removed card from ledger/sidecar merge.
    this.writeStagingMetadata(card.stagedPath, {
      ...this.metadataFromCard(card),
      status: 'REMOVED'
    })

    this.cards.splice(index, 1)
    if (card.status !== 'DISPATCHED' && existsSync(card.stagedPath)) {
      try {
        unlinkSync(card.stagedPath)
      } catch {
        // Card removal should not fail only because the staged file is locked.
      }
    }

    this.persistAndEmit()
    return this.state()
  }

  async acknowledgeEvidenceDelivery(request: VraEvidenceDeliveryAckRequest): Promise<VraEvidenceDeliveryAckResult> {
    const cardId = this.requiredString(request?.cardId, 'EVIDENCE_ACK_CARD_ID_MISSING')
    const evidenceId = this.requiredString(request?.evidenceId, 'EVIDENCE_ACK_EVIDENCE_ID_MISSING')
    const artifactId = this.requiredString(request?.artifactId, 'EVIDENCE_ACK_ARTIFACT_ID_MISSING')
    const returnedAt = this.requiredString(request?.returnedAt, 'EVIDENCE_ACK_RETURNED_AT_MISSING')
    if (!Number.isFinite(Date.parse(returnedAt))) throw new Error('EVIDENCE_ACK_RETURNED_AT_INVALID')

    const card = this.cards.find(candidate => candidate.id === cardId)
    if (!card) throw new Error('EVIDENCE_ACK_CARD_NOT_FOUND')
    if (card.humanApproval !== 'APPROVED' || card.dispatchPhase !== 'PUBLISHED' || card.status !== 'DISPATCHED') {
      throw new Error('EVIDENCE_ACK_HUMAN_PUBLISH_PRECONDITION_FAILED')
    }
    if (!card.jobId || !card.artifactId || !card.evidenceIdentity) throw new Error('EVIDENCE_ACK_IDENTITY_INCOMPLETE')
    if (card.evidenceIdentity !== evidenceId) throw new Error('EVIDENCE_ACK_EVIDENCE_ID_MISMATCH')
    if (card.artifactId !== artifactId) throw new Error('EVIDENCE_ACK_ARTIFACT_ID_MISMATCH')
    if (card.workstationEvidenceState !== 'AVAILABLE') throw new Error('EVIDENCE_ACK_NOT_AVAILABLE')
    if (!['RETURN_QUEUED', 'RETURNED'].includes(card.workstationEvidenceReturnState ?? '')) {
      throw new Error('EVIDENCE_ACK_NOT_RETURN_QUEUED')
    }
    if (card.originVera === 'UNKNOWN' || !card.originSession || !card.originWindow ||
        card.originWindow !== card.originSession || card.originVera !== this.veraForSession(card.originSession)) {
      throw new Error('EVIDENCE_ACK_ORIGIN_FAIL_CLOSED')
    }

    const response = await this.workstation.acknowledgeEvidence(card.jobId, {
      evidence_id: evidenceId,
      artifact_id: artifactId,
      returned_at: returnedAt
    })
    const body = response.body
    if (body.acknowledged !== true) throw new Error('EVIDENCE_ACK_RESPONSE_NOT_ACKNOWLEDGED')
    if (body.job_id !== card.jobId || body.evidence_id !== evidenceId || body.artifact_id !== artifactId) {
      throw new Error('EVIDENCE_ACK_RESPONSE_IDENTITY_MISMATCH')
    }
    if (body.evidence_return_state !== 'RETURNED' || body.returned_at !== returnedAt) {
      throw new Error('EVIDENCE_ACK_RESPONSE_RETURNED_STATE_MISMATCH')
    }
    if (typeof body.idempotent !== 'boolean') throw new Error('EVIDENCE_ACK_RESPONSE_IDEMPOTENCY_MISSING')

    card.workstationEvidenceReturnState = 'RETURNED'
    card.workstationLastError = null
    this.persistCardState(card)

    await syncAutoRegistryWorkstationLifecycle(
      this.registryRuntime.core,
      this.registryRuntime.store,
      {
        jobId: card.jobId,
        artifactId: card.artifactId,
        correlationId: card.correlationId,
        portalPublished: card.dispatchPhase === 'PUBLISHED' && card.status === 'DISPATCHED',
        workstationRegistration: card.workstationRegistration,
        workstationJobState: card.workstationJobState,
        allocatedLane: card.allocatedLane,
        evidenceId: card.evidenceIdentity,
        evidenceState: card.workstationEvidenceState,
        evidenceReturnState: card.workstationEvidenceReturnState
      }
        )

    return {
      acknowledged: true,
      idempotent: body.idempotent,
      jobId: card.jobId,
      evidenceId,
      artifactId,
      evidenceReturnState: 'RETURNED',
      returnedAt
    }
  }

  async getWorkstationSafety(): Promise<WorkstationSafetyObservation> {
    let response: Awaited<ReturnType<WorkstationClient['getSafety']>>
    try {
      response = await this.workstation.getSafety()
      this.workstationOnline = true
    } catch (error) {
      // An HTTP error still proves loopback reachability; a socket/timeout failure does not.
      this.workstationOnline = error instanceof WorkstationHttpError
      this.workstationObservedUtc = new Date().toISOString()
      const observation = this.unknownSafetyObservation(
        error instanceof Error ? error.message : String(error),
        this.workstationOnline
      )
      this.setWorkstationSafety(observation)
      return observation
    }

    try {
      const observation = this.parseSafetyObservation(response.body)
      this.workstationObservedUtc = observation.observedUtc
      this.setWorkstationSafety(observation)
      return observation
    } catch (error) {
      const observation = this.unknownSafetyObservation(
        error instanceof Error ? error.message : String(error),
        true
      )
      this.workstationObservedUtc = observation.observedUtc
      this.setWorkstationSafety(observation)
      return observation
    }
  }

  async performWorkstationSafetyAction(
    request: WorkstationSafetyActionRequest
  ): Promise<WorkstationSafetyActionResult> {
    const action = this.requireSafetyAction(request?.action)
    const requestId = this.requiredString(request?.requestId, 'SAFETY_REQUEST_ID_MISSING')
    const reason = this.requiredString(request?.reason, 'SAFETY_REASON_MISSING')
    if (requestId.length > 256) throw new Error('SAFETY_REQUEST_ID_TOO_LONG')
    if (reason.length > 2048) throw new Error('SAFETY_REASON_TOO_LONG')

    const response = await this.workstation.safetyAction(action, {
      request_id: requestId,
      authority: 'HUMAN',
      reason
    })
    this.workstationOnline = true
    const post = this.parseSafetyActionResponse(response.body, action)

    // No optimistic authority: a successful POST is not shown as final until GET /v1/safety
    // returns the same durable state/generation from Workstation.
    const recheck = await this.workstation.getSafety()
    const observation = this.parseSafetyObservation(recheck.body)
    this.workstationObservedUtc = observation.observedUtc
    this.setWorkstationSafety(observation)
    if (observation.state !== post.state || observation.generation !== post.generation) {
      throw new Error('SAFETY_POST_REVERIFY_MISMATCH_FAIL_CLOSED')
    }

    return { ...post, observation }
  }

  onChanged(listener: ChangedListener): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  private veraForSession(sessionId: string): VraOriginVera {
    const match = /^vera-0([1-5])$/.exec(sessionId)
    return match ? `VERA0${match[1]}` as VraOriginVera : 'UNKNOWN'
  }

  private sourceFor(webContents: WebContents): string | null {
    return this.webviewSources.get(webContents.id) ?? null
  }

  private captureOrigin(webContents: WebContents): ImmutableVraOrigin | null {
    const originSession = this.sourceFor(webContents)
    const originVera = this.originVeraFromSession(originSession)
    if (!originSession || originVera === 'UNKNOWN') return null

    return Object.freeze({
      originVera,
      originSession,
      originWindow: originSession
    })
  }

  private originVeraFromSession(sessionId: string | null): VraOriginVera {
    switch (sessionId) {
      case 'vera-01': return 'VERA01'
      case 'vera-02': return 'VERA02'
      case 'vera-03': return 'VERA03'
      case 'vera-04': return 'VERA04'
      case 'vera-05': return 'VERA05'
      default: return 'UNKNOWN'
    }
  }

  private captureCompleted(
    id: string,
    filename: string,
    stagedPath: string,
    origin: ImmutableVraOrigin,
    webContentsId: number,
    capturedUtc: string
  ): void {
    let manifest: VraManifestMetadata
    try {
      // Workstation HTTP registration validates routing from manifest.json itself.
      // Commit immutable capture-time routing into the staged VRA BEFORE its SHA is bound.
      // Never recover origin from renderer/card/current-window presentation state.
      manifest = this.ensureCaptureRoutingEnvelope(stagedPath, id, origin)
    } catch (error) {
      this.rejectCompletedCapture(stagedPath, error instanceof Error ? error.message : String(error))
      return
    }

    const sha256 = this.sha256(stagedPath)

    const jobConflict = this.cards.find(card =>
      card.jobId === manifest.jobId &&
      (card.sha256 !== sha256 || card.originSession !== origin.originSession)
    )
    if (jobConflict) {
      this.rejectCompletedCapture(stagedPath, 'VRA_JOB_IDENTITY_CONFLICT')
      return
    }

    const duplicate = this.cards.find(card =>
      card.jobId === manifest.jobId &&
      card.sha256 === sha256 &&
      card.originSession === origin.originSession
    )
    if (duplicate) {
      this.writeStagingMetadata(stagedPath, {
        ...this.captureSeed(id, filename, basename(stagedPath), webContentsId, origin, capturedUtc),
        job_id: manifest.jobId,
        correlation_id: manifest.correlationId,
        return_channel: manifest.returnChannel,
        project_id: manifest.projectId,
        project_name: manifest.projectName,
        artifact_id: manifest.artifactId,
        title: manifest.jobTitle,
        requested_lane: manifest.requestedLane,
        lane_policy: manifest.lanePolicy,
        parallelism: manifest.parallelism,
        worker_concurrency: manifest.workerConcurrency,
        card_kind: manifest.cardKind,
        rerun_of_job_id: manifest.rerunOfJobId,
        test_run_id: manifest.testRunId,
        status: 'REMOVED',
        dispatch_phase: 'REMOVED',
        sha256,
        size_bytes: statSync(stagedPath).size
      })
      try {
        unlinkSync(stagedPath)
      } catch {
        // Duplicate suppression is best effort; the existing job/card remains canonical.
      }
      return
    }

    const stat = statSync(stagedPath)
    const card: DurableVraDispatchCard = {
      id,
      filename,
      sourceSessionId: origin.originSession,
      sourceWebContentsId: webContentsId,
      stagedPath,
      sizeBytes: stat.size,
      sha256,
      status: 'STAGED',
      capturedUtc,
      dispatchedUtc: null,
      worksPath: null,
      error: null,
      originVera: origin.originVera,
      originSession: origin.originSession,
      originWindow: origin.originWindow,
      routingContractVersion: manifest.contractVersion,
      jobId: manifest.jobId,
      returnChannel: manifest.returnChannel,
      projectId: manifest.projectId,
      projectName: manifest.projectName,
      artifactId: manifest.artifactId,
      jobTitle: manifest.jobTitle,
      requestedLane: manifest.requestedLane,
      lanePolicy: manifest.lanePolicy,
      allocatedLane: null,
      parallelism: manifest.parallelism,
      workerConcurrency: manifest.workerConcurrency,
      correlationId: manifest.correlationId,
      cardKind: manifest.cardKind,
      rerunOfJobId: manifest.rerunOfJobId,
      testRunId: manifest.testRunId,
      humanApproval: 'PENDING',
      dispatchPhase: 'STAGED',
      publishName: null,
      workstationRegistration: 'NOT_READY',
      workstationJobState: null,
      workstationEvidenceState: null,
      workstationEvidenceReturnState: null,
      workstationLastError: null,
      registrationAttemptUtc: null,
      registeredUtc: null,
      evidenceIdentity: null,
      evidenceCacheName: null
    }

    // Sidecar is the durable Capture -> Staging routing source of truth.
    this.writeStagingMetadata(stagedPath, this.metadataFromCard(card))
    this.cards.push(card)
    this.persistAndEmit()
    // 000109V5: renderer routing is an accelerator only. Main process owns the
    // authoritative fallback from Human AUTO authority -> approved VRA publication.
    this.scheduleAutoAuthorizedDispatchScan()
  }

  private rejectCompletedCapture(stagedPath: string, message: string): void {
    const metadata = this.readStagingMetadata(this.metadataPath(stagedPath))
    if (!metadata) return
    const rejected: VraStagingMetadata = {
      ...metadata,
      status: 'ERROR',
      dispatch_phase: 'ERROR',
      size_bytes: existsSync(stagedPath) ? statSync(stagedPath).size : metadata.size_bytes,
      sha256: existsSync(stagedPath) ? this.sha256(stagedPath) : metadata.sha256,
      error: message
    }
    this.writeStagingMetadata(stagedPath, rejected)
    const card = this.recoverCard(rejected)
    if (card) {
      this.cards.push(card)
      this.persistAndEmit()
    }
  }

  private requireCard(cardId: string): DurableVraDispatchCard {
    const card = this.cards.find(candidate => candidate.id === cardId)
    if (!card) throw new Error('VRA_DISPATCH_CARD_NOT_FOUND')
    return card
  }

  private requireHealthyStagedCard(cardId: string): DurableVraDispatchCard {
    const card = this.requireCard(cardId)
    if (!existsSync(card.stagedPath)) {
      this.fail(card, 'STAGED_VRA_NOT_FOUND')
      throw new Error('STAGED_VRA_NOT_FOUND')
    }

    const currentSha = this.sha256(card.stagedPath)
    if (currentSha !== card.sha256) {
      this.fail(card, 'STAGED_VRA_SHA256_MISMATCH')
      throw new Error('STAGED_VRA_SHA256_MISMATCH')
    }

    return card
  }

  private fail(card: DurableVraDispatchCard, message: string): DurableVraDispatchCard {
    card.status = 'ERROR'
    card.error = message
    this.writeStagingMetadata(card.stagedPath, this.metadataFromCard(card))
    this.persistAndEmit()
    return { ...card }
  }

  private captureSeed(
    captureId: string,
    filename: string,
    stagedName: string,
    webContentsId: number,
    origin: ImmutableVraOrigin,
    capturedUtc: string
  ): VraStagingMetadata {
    return {
      schema_version: 'vertex/vra-staging-metadata/1',
      contract_version: VRA_ROUTING_CONTRACT_VERSION,
      capture_id: captureId,
      job_id: `job-${captureId}`,
      correlation_id: captureId,
      return_channel: DEFAULT_RETURN_CHANNEL,
      filename,
      staged_name: stagedName,
      publish_name: null,
      source_web_contents_id: webContentsId,
      origin_vera: origin.originVera,
      origin_session: origin.originSession,
      origin_window: origin.originWindow,
      project_id: null,
      project_name: null,
      artifact_id: null,
      title: null,
      requested_lane: null,
      lane_policy: 'ANY',
      allocated_lane: null,
      parallelism: 1,
      worker_concurrency: null,
      card_kind: null,
      rerun_of_job_id: null,
      test_run_id: null,
      human_approval: 'PENDING',
      dispatch_phase: 'CAPTURING',
      status: 'CAPTURING',
      captured_utc: capturedUtc,
      dispatched_utc: null,
      size_bytes: null,
      sha256: null,
      error: null
    }
  }

  private metadataFromCard(card: DurableVraDispatchCard): VraStagingMetadata {
    return {
      schema_version: 'vertex/vra-staging-metadata/1',
      contract_version: card.routingContractVersion,
      capture_id: card.id,
      job_id: card.jobId,
      correlation_id: card.correlationId,
      return_channel: card.returnChannel,
      filename: card.filename,
      staged_name: basename(card.stagedPath),
      publish_name: card.publishName,
      source_web_contents_id: card.sourceWebContentsId,
      origin_vera: card.originVera,
      origin_session: card.originSession,
      origin_window: card.originWindow,
      project_id: card.projectId,
      project_name: card.projectName,
      artifact_id: card.artifactId,
      title: card.jobTitle,
      requested_lane: card.requestedLane,
      lane_policy: card.lanePolicy,
      allocated_lane: card.allocatedLane,
      parallelism: card.parallelism,
      worker_concurrency: card.workerConcurrency,
      card_kind: card.cardKind,
      rerun_of_job_id: card.rerunOfJobId,
      test_run_id: card.testRunId,
      human_approval: card.humanApproval,
      dispatch_phase: card.dispatchPhase,
      status: card.status,
      captured_utc: card.capturedUtc,
      dispatched_utc: card.dispatchedUtc,
      size_bytes: card.sizeBytes,
      sha256: card.sha256,
      workstation_registration: card.workstationRegistration,
      workstation_job_state: card.workstationJobState,
      workstation_evidence_state: card.workstationEvidenceState,
      workstation_evidence_return_state: card.workstationEvidenceReturnState,
      workstation_last_error: card.workstationLastError,
      registration_attempt_utc: card.registrationAttemptUtc,
      registered_utc: card.registeredUtc,
      evidence_identity: card.evidenceIdentity,
      evidence_cache_name: card.evidenceCacheName,
      error: card.error
    }
  }

  private markIncompleteCapture(stagedPath: string): void {
    const metadata = this.readStagingMetadata(this.metadataPath(stagedPath))
    if (!metadata) return
    try {
      this.writeStagingMetadata(stagedPath, {
        ...metadata,
        status: 'REMOVED',
        dispatch_phase: 'REMOVED',
        error: null
      })
    } catch {
      // Keep the prior CAPTURING seed. Startup recovery will fail closed.
      return
    }
    if (existsSync(stagedPath)) {
      try {
        unlinkSync(stagedPath)
      } catch {
        // A locked partial download remains quarantined by its REMOVED sidecar.
      }
    }
  }

  private metadataPath(stagedPath: string): string {
    return `${stagedPath}.meta.json`
  }

  private writeStagingMetadata(stagedPath: string, metadata: VraStagingMetadata): void {
    this.writeJsonAtomic(this.metadataPath(stagedPath), metadata)
  }

  private writeJsonAtomic(path: string, value: unknown): void {
    const temp = `${path}.${process.pid}.${randomUUID()}.tmp`
    writeFileSync(temp, JSON.stringify(value, null, 2), 'utf8')
    try {
      renameSync(temp, path)
    } finally {
      if (existsSync(temp)) {
        try {
          unlinkSync(temp)
        } catch {
          // Stale temp is never canonical; next startup ignores *.tmp files.
        }
      }
    }
  }

  private readStagingMetadata(path: string): VraStagingMetadata | null {
    try {
      const value = JSON.parse(readFileSync(path, 'utf8')) as Partial<VraStagingMetadata>
      if (
        value.schema_version !== 'vertex/vra-staging-metadata/1' ||
        typeof value.capture_id !== 'string' ||
        typeof value.filename !== 'string' ||
        typeof value.staged_name !== 'string'
      ) {
        return null
      }
      return value as VraStagingMetadata
    } catch {
      return null
    }
  }

  private loadStagingMetadata(): VraStagingMetadata[] {
    try {
      return readdirSync(this.stagingRoot)
        .filter(name => name.endsWith('.meta.json'))
        .map(name => this.readStagingMetadata(join(this.stagingRoot, name)))
        .filter((value): value is VraStagingMetadata => value !== null)
    } catch {
      return []
    }
  }

  private hydrateCard(
    card: VraDispatchCard,
    metadata: VraStagingMetadata | null = null,
    allowLegacySourceSessionId = false
  ): DurableVraDispatchCard {
    const current = card as VraDispatchCard & Partial<DurableVraDispatchCard>
    const persistedSession =
      metadata?.origin_session ??
      current.originSession ??
      (allowLegacySourceSessionId ? card.sourceSessionId : null)
    const manifest = existsSync(card.stagedPath)
      ? this.readManifestMetadata(card.stagedPath, card.id, false)
      : this.emptyManifestMetadata(card.id)
    const originVera =
      metadata?.origin_vera ??
      current.originVera ??
      (allowLegacySourceSessionId ? this.originVeraFromSession(persistedSession) : 'UNKNOWN')

    const hydrated: DurableVraDispatchCard = {
      ...card,
      originVera,
      originSession: persistedSession,
      originWindow: metadata?.origin_window ?? current.originWindow ?? persistedSession,
      routingContractVersion: metadata?.contract_version ?? current.routingContractVersion ?? manifest.contractVersion,
      jobId: metadata?.job_id ?? current.jobId ?? manifest.jobId,
      returnChannel: metadata?.return_channel ?? current.returnChannel ?? manifest.returnChannel,
      projectId: metadata?.project_id ?? current.projectId ?? manifest.projectId,
      projectName: metadata?.project_name ?? current.projectName ?? manifest.projectName,
      artifactId: metadata?.artifact_id ?? current.artifactId ?? manifest.artifactId,
      jobTitle: metadata?.title ?? current.jobTitle ?? manifest.jobTitle,
      requestedLane: metadata?.requested_lane ?? current.requestedLane ?? manifest.requestedLane,
      lanePolicy: this.normalizeLanePolicy(metadata?.lane_policy ?? current.lanePolicy ?? manifest.lanePolicy, false),
      allocatedLane: metadata?.allocated_lane ?? current.allocatedLane ?? null,
      parallelism: this.normalizeParallelism(metadata?.parallelism ?? current.parallelism ?? manifest.parallelism, false),
      workerConcurrency: this.normalizeWorkerConcurrency(metadata?.worker_concurrency ?? current.workerConcurrency ?? manifest.workerConcurrency, false),
      correlationId: metadata?.correlation_id ?? current.correlationId ?? manifest.correlationId,
      cardKind: metadata?.card_kind ?? current.cardKind ?? manifest.cardKind,
      rerunOfJobId: metadata?.rerun_of_job_id ?? current.rerunOfJobId ?? manifest.rerunOfJobId,
      testRunId: metadata?.test_run_id ?? current.testRunId ?? manifest.testRunId,
      humanApproval:
        metadata?.human_approval ??
        current.humanApproval ??
        (card.status === 'DISPATCHED' ? 'APPROVED' : 'PENDING'),
      dispatchPhase:
        metadata?.dispatch_phase ??
        current.dispatchPhase ??
        (card.status === 'DISPATCHED' ? 'PUBLISHED' : 'STAGED'),
      publishName: metadata?.publish_name ?? current.publishName ?? null,
      workstationRegistration: metadata?.workstation_registration ?? current.workstationRegistration ?? (card.status === 'DISPATCHED' ? 'PENDING' : 'NOT_READY'),
      workstationJobState: metadata?.workstation_job_state ?? current.workstationJobState ?? null,
      workstationEvidenceState: metadata?.workstation_evidence_state ?? current.workstationEvidenceState ?? null,
      workstationEvidenceReturnState: metadata?.workstation_evidence_return_state ?? current.workstationEvidenceReturnState ?? null,
      workstationLastError: metadata?.workstation_last_error ?? current.workstationLastError ?? null,
      registrationAttemptUtc: metadata?.registration_attempt_utc ?? current.registrationAttemptUtc ?? null,
      registeredUtc: metadata?.registered_utc ?? current.registeredUtc ?? null,
      evidenceIdentity: metadata?.evidence_identity ?? current.evidenceIdentity ?? null,
      evidenceCacheName: metadata?.evidence_cache_name ?? current.evidenceCacheName ?? null
    }

    return this.reconcileApprovedPublication(hydrated)
  }

  private recoverCard(metadata: VraStagingMetadata): DurableVraDispatchCard | null {
    if (metadata.status === 'REMOVED' || metadata.dispatch_phase === 'REMOVED') return null

    const stagedPath = join(this.stagingRoot, basename(metadata.staged_name))
    const exists = existsSync(stagedPath)
    if (!exists && metadata.status === 'CAPTURING') return null

    const interrupted = metadata.status === 'CAPTURING'
    const published = metadata.dispatch_phase === 'PUBLISHED' || metadata.status === 'DISPATCHED'
    const status: VraDispatchCard['status'] =
      interrupted || !exists
        ? 'ERROR'
        : published
          ? 'DISPATCHED'
          : metadata.status === 'ERROR'
            ? 'ERROR'
            : 'STAGED'
    const sizeBytes = exists ? statSync(stagedPath).size : metadata.size_bytes ?? 0
    const sha256 = metadata.sha256 ?? (exists ? this.sha256(stagedPath) : '')
    const manifest = exists
      ? this.readManifestMetadata(stagedPath, metadata.capture_id, false)
      : this.emptyManifestMetadata(metadata.capture_id)

    const card: DurableVraDispatchCard = {
      id: metadata.capture_id,
      filename: metadata.filename,
      sourceSessionId: metadata.origin_session,
      sourceWebContentsId: metadata.source_web_contents_id,
      stagedPath,
      sizeBytes,
      sha256,
      status,
      capturedUtc: metadata.captured_utc,
      dispatchedUtc: metadata.dispatched_utc,
      worksPath: published && metadata.publish_name
        ? join(this.worksIncomingRoot, basename(metadata.publish_name))
        : null,
      error:
        interrupted
          ? 'CAPTURE_INTERRUPTED_REVIEW_REQUIRED'
          : !exists
            ? 'STAGED_VRA_NOT_FOUND'
            : metadata.error,
      originVera: metadata.origin_vera ?? 'UNKNOWN',
      originSession: metadata.origin_session,
      originWindow: metadata.origin_window,
      routingContractVersion: metadata.contract_version ?? manifest.contractVersion,
      jobId: metadata.job_id ?? manifest.jobId,
      returnChannel: metadata.return_channel ?? manifest.returnChannel,
      projectId: metadata.project_id ?? manifest.projectId,
      projectName: metadata.project_name ?? manifest.projectName,
      artifactId: metadata.artifact_id ?? manifest.artifactId,
      jobTitle: metadata.title ?? manifest.jobTitle,
      requestedLane: metadata.requested_lane ?? manifest.requestedLane,
      lanePolicy: this.normalizeLanePolicy(metadata.lane_policy ?? manifest.lanePolicy, false),
      allocatedLane: metadata.allocated_lane ?? null,
      parallelism: this.normalizeParallelism(metadata.parallelism ?? manifest.parallelism, false),
      workerConcurrency: this.normalizeWorkerConcurrency(metadata.worker_concurrency ?? manifest.workerConcurrency, false),
      correlationId: metadata.correlation_id ?? manifest.correlationId,
      cardKind: metadata.card_kind ?? manifest.cardKind,
      rerunOfJobId: metadata.rerun_of_job_id ?? manifest.rerunOfJobId,
      testRunId: metadata.test_run_id ?? manifest.testRunId,
      humanApproval: metadata.human_approval ?? 'PENDING',
      dispatchPhase: metadata.dispatch_phase ?? (published ? 'PUBLISHED' : 'STAGED'),
      publishName: metadata.publish_name ?? null,
      workstationRegistration: metadata.workstation_registration ?? (published ? 'PENDING' : 'NOT_READY'),
      workstationJobState: metadata.workstation_job_state ?? null,
      workstationEvidenceState: metadata.workstation_evidence_state ?? null,
      workstationEvidenceReturnState: metadata.workstation_evidence_return_state ?? null,
      workstationLastError: metadata.workstation_last_error ?? null,
      registrationAttemptUtc: metadata.registration_attempt_utc ?? null,
      registeredUtc: metadata.registered_utc ?? null,
      evidenceIdentity: metadata.evidence_identity ?? null,
      evidenceCacheName: metadata.evidence_cache_name ?? null
    }
    return this.reconcileApprovedPublication(card)
  }

  private emptyManifestMetadata(captureId: string): VraManifestMetadata {
    return {
      contractVersion: VRA_ROUTING_CONTRACT_VERSION,
      jobId: `job-${captureId}`,
      returnChannel: DEFAULT_RETURN_CHANNEL,
      projectId: null,
      projectName: null,
      artifactId: null,
      jobTitle: null,
      requestedLane: null,
      lanePolicy: 'ANY',
      parallelism: 1,
      workerConcurrency: null,
      correlationId: captureId,
      cardKind: null,
      rerunOfJobId: null,
      testRunId: null
    }
  }

  private readManifestMetadata(
    path: string,
    captureId: string,
    strictRouting: boolean
  ): VraManifestMetadata {
    const empty = this.emptyManifestMetadata(captureId)

    try {
      const manifest = this.readVraManifest(path)
      if (!manifest) {
        if (strictRouting) throw new Error('VRA_MANIFEST_UNREADABLE')
        return empty
      }

      const target = this.asRecord(manifest.target)
      const routing = this.asRecord(manifest.routing)
      const projectRoot = this.scalar(target?.project_root)
      const projectName =
        this.scalar(routing?.project_name) ??
        this.scalar(target?.project_name) ??
        this.scalar(manifest.project_name) ??
        (projectRoot ? this.projectNameFromRoot(projectRoot) : null)
      const projectId =
        this.scalar(routing?.project_id) ??
        this.scalar(manifest.project_id) ??
        (projectRoot ? this.projectNameFromRoot(projectRoot) : null)
      const cardKind: VraCardKind =
        this.scalar(manifest.card_kind) === VRA_TEST_CARD_KIND ? VRA_TEST_CARD_KIND : null
      const testRun = cardKind === VRA_TEST_CARD_KIND ? this.asRecord(manifest.test_run) : null
      const rerunOfJobId = cardKind === VRA_TEST_CARD_KIND
        ? this.scalar(testRun?.rerun_of_job_id)
        : null
      const testRunId = cardKind === VRA_TEST_CARD_KIND
        ? this.scalar(testRun?.run_id)
        : null

      if (routing) {
        const contractVersion = this.scalar(routing.contract_version) ?? VRA_ROUTING_CONTRACT_VERSION
        if (contractVersion !== VRA_ROUTING_CONTRACT_VERSION) {
          throw new Error('VRA_ROUTING_CONTRACT_UNSUPPORTED')
        }

        const jobId = this.scalar(routing.job_id)
        const returnChannel = this.scalar(routing.return_channel)
        if (!jobId) throw new Error('VRA_ROUTING_JOB_ID_REQUIRED')
        if (!returnChannel) throw new Error('VRA_ROUTING_RETURN_CHANNEL_REQUIRED')

        const requestedLane = this.scalar(routing.requested_lane) ?? this.scalar(routing.lane_hint)
        const lanePolicy = this.normalizeLanePolicy(this.scalar(routing.lane_policy) ?? 'ANY', true)
        if (lanePolicy === 'PREFER' && !requestedLane) {
          throw new Error('VRA_ROUTING_REQUESTED_LANE_REQUIRED_FOR_PREFER')
        }

        return {
          contractVersion: VRA_ROUTING_CONTRACT_VERSION,
          jobId,
          returnChannel,
          projectId,
          projectName,
          artifactId: this.scalar(manifest.artifact_id),
          jobTitle: this.scalar(manifest.title) ?? this.scalar(manifest.job_summary),
          requestedLane,
          lanePolicy,
          parallelism: this.normalizeParallelism(this.numberScalar(routing.parallelism) ?? 1, true),
          workerConcurrency: this.normalizeWorkerConcurrency(this.numberScalar(routing.worker_concurrency), true),
          correlationId: this.scalar(routing.correlation_id) ?? jobId,
          cardKind,
          rerunOfJobId,
          testRunId
        }
      }

      // Legacy vra/1 without routing remains accepted. Portal creates a canonical durable
      // routing envelope while origin always comes from Capture, never from manifest guesses.
      const requestedLane = this.firstNestedScalar(manifest, [
        ['requested_lane'],
        ['lane_hint'],
        ['dispatch', 'requested_lane'],
        ['workstation', 'requested_lane']
      ])
      const legacyPolicyRaw = this.firstNestedScalar(manifest, [
        ['lane_policy'],
        ['dispatch', 'lane_policy'],
        ['workstation', 'lane_policy']
      ])
      const lanePolicy = this.normalizeLanePolicy(legacyPolicyRaw ?? (requestedLane ? 'PREFER' : 'ANY'), strictRouting)
      if (lanePolicy === 'PREFER' && !requestedLane) {
        throw new Error('VRA_ROUTING_REQUESTED_LANE_REQUIRED_FOR_PREFER')
      }

      return {
        ...empty,
        projectId,
        projectName,
        artifactId: this.scalar(manifest.artifact_id),
        jobTitle: this.scalar(manifest.title) ?? this.scalar(manifest.job_summary),
        requestedLane,
        lanePolicy,
        cardKind,
        rerunOfJobId,
        testRunId
      }
    } catch (error) {
      if (strictRouting) throw error
      return empty
    }
  }

  private ensureCaptureRoutingEnvelope(
    stagedPath: string,
    captureId: string,
    origin: ImmutableVraOrigin
  ): VraManifestMetadata {
    const manifest = this.readVraManifest(stagedPath)
    if (!manifest) throw new Error('VRA_MANIFEST_UNREADABLE')

    const existingRouting = this.asRecord(manifest.routing)
    const existingOriginVera = this.scalar(existingRouting?.origin_vera)
    const existingOriginSession = this.scalar(existingRouting?.origin_session)
    const existingOriginWindow = this.scalar(existingRouting?.origin_window)

    // An explicit origin is accepted only when it matches the immutable capture owner.
    // Mismatch is fail-closed; display metadata is never used to repair routing.
    if (existingOriginVera && existingOriginVera !== origin.originVera) {
      throw new Error('VRA_ROUTING_ORIGIN_VERA_CONFLICT')
    }
    if (existingOriginSession && existingOriginSession !== origin.originSession) {
      throw new Error('VRA_ROUTING_ORIGIN_SESSION_CONFLICT')
    }
    if (existingOriginWindow && existingOriginWindow !== origin.originWindow) {
      throw new Error('VRA_ROUTING_ORIGIN_WINDOW_CONFLICT')
    }

    // Parse the vra/1 source contract first. Legacy manifests without routing receive
    // deterministic job/return/correlation metadata from capture-time durable facts.
    const source = this.readManifestMetadata(stagedPath, captureId, true)

    const routing: Record<string, unknown> = {
      ...(existingRouting ?? {}),
      contract_version: VRA_ROUTING_CONTRACT_VERSION,
      job_id: source.jobId,
      origin_vera: origin.originVera,
      origin_session: origin.originSession,
      origin_window: origin.originWindow,
      return_channel: source.returnChannel,
      lane_policy: source.lanePolicy,
      parallelism: source.parallelism,
      correlation_id: source.correlationId
    }

    if (source.projectId) routing.project_id = source.projectId
    else delete routing.project_id

    if (source.projectName) routing.project_name = source.projectName
    else delete routing.project_name

    if (source.requestedLane) routing.requested_lane = source.requestedLane
    else delete routing.requested_lane

    if (source.workerConcurrency !== null) routing.worker_concurrency = source.workerConcurrency
    else delete routing.worker_concurrency

    // Allocation remains Workstation authority.
    delete routing.allocated_lane
    delete routing.execution_lane
    delete routing.require_lane

    const nextManifest: Record<string, unknown> = {
      ...manifest,
      routing
    }

    this.rewriteVraManifestAtomic(stagedPath, nextManifest)

    // Re-read the exact committed bytes. This same routed artifact is later hashed,
    // sidecar-bound, atomically published and registered over HTTP.
    const committed = this.readManifestMetadata(stagedPath, captureId, true)
    const committedManifest = this.readVraManifest(stagedPath)
    const committedRouting = this.asRecord(committedManifest?.routing)

    if (
      this.scalar(committedRouting?.origin_vera) !== origin.originVera ||
      this.scalar(committedRouting?.origin_session) !== origin.originSession ||
      this.scalar(committedRouting?.origin_window) !== origin.originWindow ||
      this.scalar(committedRouting?.job_id) !== committed.jobId ||
      this.scalar(committedRouting?.return_channel) !== committed.returnChannel
    ) {
      throw new Error('VRA_CAPTURE_ROUTING_COMMIT_VERIFY_FAILED')
    }

    return committed
  }

  private readVraEntries(path: string): Array<{ name: string; data: Buffer }> {
    const archive = readFileSync(path)
    const eocdSignature = 0x06054b50
    let eocd = -1
    const minimum = Math.max(0, archive.length - 0x10016)

    for (let offset = archive.length - 22; offset >= minimum; offset -= 1) {
      if (archive.readUInt32LE(offset) === eocdSignature) {
        eocd = offset
        break
      }
    }
    if (eocd < 0) throw new Error('VRA_ZIP_EOCD_NOT_FOUND')

    const entries = archive.readUInt16LE(eocd + 10)
    let cursor = archive.readUInt32LE(eocd + 16)
    const output: Array<{ name: string; data: Buffer }> = []

    for (let index = 0; index < entries; index += 1) {
      if (archive.readUInt32LE(cursor) !== 0x02014b50) {
        throw new Error('VRA_ZIP_CENTRAL_DIRECTORY_INVALID')
      }

      const flags = archive.readUInt16LE(cursor + 8)
      const method = archive.readUInt16LE(cursor + 10)
      const compressedSize = archive.readUInt32LE(cursor + 20)
      const filenameLength = archive.readUInt16LE(cursor + 28)
      const extraLength = archive.readUInt16LE(cursor + 30)
      const commentLength = archive.readUInt16LE(cursor + 32)
      const localOffset = archive.readUInt32LE(cursor + 42)
      const filename = archive
        .subarray(cursor + 46, cursor + 46 + filenameLength)
        .toString('utf8')

      if ((flags & 0x0001) !== 0) throw new Error('VRA_ZIP_ENCRYPTED_ENTRY_REJECTED')
      if (archive.readUInt32LE(localOffset) !== 0x04034b50) {
        throw new Error('VRA_ZIP_LOCAL_HEADER_INVALID')
      }

      const localNameLength = archive.readUInt16LE(localOffset + 26)
      const localExtraLength = archive.readUInt16LE(localOffset + 28)
      const dataStart = localOffset + 30 + localNameLength + localExtraLength
      const compressed = archive.subarray(dataStart, dataStart + compressedSize)

      const raw = method === 0
        ? Buffer.from(compressed)
        : method === 8
          ? inflateRawSync(compressed)
          : null

      if (!raw) throw new Error(`VRA_ZIP_COMPRESSION_UNSUPPORTED:${method}`)
      output.push({ name: filename, data: Buffer.from(raw) })

      cursor += 46 + filenameLength + extraLength + commentLength
    }

    return output
  }

  private crc32(data: Buffer): number {
    let crc = 0xffffffff
    for (const byte of data) {
      crc ^= byte
      for (let bit = 0; bit < 8; bit += 1) {
        crc = (crc >>> 1) ^ ((crc & 1) !== 0 ? 0xedb88320 : 0)
      }
    }
    return (crc ^ 0xffffffff) >>> 0
  }

  private buildVraArchive(entries: Array<{ name: string; data: Buffer }>): Buffer {
    const localParts: Buffer[] = []
    const centralParts: Buffer[] = []
    let offset = 0

    for (const entry of entries) {
      const name = Buffer.from(entry.name, 'utf8')
      const raw = entry.data
      const compressed = deflateRawSync(raw, { level: 6 })
      const crc = this.crc32(raw)

      const local = Buffer.alloc(30)
      local.writeUInt32LE(0x04034b50, 0)
      local.writeUInt16LE(20, 4)
      local.writeUInt16LE(0x0800, 6)
      local.writeUInt16LE(8, 8)
      local.writeUInt16LE(0, 10)
      local.writeUInt16LE(0, 12)
      local.writeUInt32LE(crc, 14)
      local.writeUInt32LE(compressed.length, 18)
      local.writeUInt32LE(raw.length, 22)
      local.writeUInt16LE(name.length, 26)
      local.writeUInt16LE(0, 28)

      localParts.push(local, name, compressed)

      const central = Buffer.alloc(46)
      central.writeUInt32LE(0x02014b50, 0)
      central.writeUInt16LE(20, 4)
      central.writeUInt16LE(20, 6)
      central.writeUInt16LE(0x0800, 8)
      central.writeUInt16LE(8, 10)
      central.writeUInt16LE(0, 12)
      central.writeUInt16LE(0, 14)
      central.writeUInt32LE(crc, 16)
      central.writeUInt32LE(compressed.length, 20)
      central.writeUInt32LE(raw.length, 24)
      central.writeUInt16LE(name.length, 28)
      central.writeUInt16LE(0, 30)
      central.writeUInt16LE(0, 32)
      central.writeUInt16LE(0, 34)
      central.writeUInt16LE(0, 36)
      central.writeUInt32LE(0, 38)
      central.writeUInt32LE(offset, 42)

      centralParts.push(central, name)
      offset += local.length + name.length + compressed.length
    }

    const locals = Buffer.concat(localParts)
    const central = Buffer.concat(centralParts)

    const eocd = Buffer.alloc(22)
    eocd.writeUInt32LE(0x06054b50, 0)
    eocd.writeUInt16LE(0, 4)
    eocd.writeUInt16LE(0, 6)
    eocd.writeUInt16LE(entries.length, 8)
    eocd.writeUInt16LE(entries.length, 10)
    eocd.writeUInt32LE(central.length, 12)
    eocd.writeUInt32LE(locals.length, 16)
    eocd.writeUInt16LE(0, 20)

    return Buffer.concat([locals, central, eocd])
  }

  private rewriteVraManifestAtomic(
    stagedPath: string,
    manifest: Record<string, unknown>
  ): void {
    const entries = this.readVraEntries(stagedPath)
    const manifestIndexes = entries
      .map((entry, index) => ({ entry, index }))
      .filter(({ entry }) => entry.name === 'manifest.json' || entry.name.endsWith('/manifest.json'))

    if (manifestIndexes.length !== 1) {
      throw new Error('VRA_MANIFEST_ENTRY_COUNT_INVALID')
    }

    const index = manifestIndexes[0].index
    entries[index] = {
      name: entries[index].name,
      data: Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
    }

    const rebuilt = this.buildVraArchive(entries)
    const temp = `${stagedPath}.${randomUUID()}.routing.tmp`

    try {
      writeFileSync(temp, rebuilt, { flag: 'wx' })

      if (!this.readVraManifest(temp)) {
        throw new Error('VRA_ROUTING_REWRITE_PARSE_FAILED')
      }

      renameSync(temp, stagedPath)
    } finally {
      if (existsSync(temp)) {
        try {
          unlinkSync(temp)
        } catch {
          // Temporary routing file never becomes a published .vra.
        }
      }
    }
  }

  private readVraManifest(path: string): Record<string, unknown> | null {
    const archive = readFileSync(path)
    const eocdSignature = 0x06054b50
    let eocd = -1
    const minimum = Math.max(0, archive.length - 0x10016)

    for (let offset = archive.length - 22; offset >= minimum; offset -= 1) {
      if (archive.readUInt32LE(offset) === eocdSignature) {
        eocd = offset
        break
      }
    }
    if (eocd < 0) return null

    const entries = archive.readUInt16LE(eocd + 10)
    let cursor = archive.readUInt32LE(eocd + 16)
    for (let index = 0; index < entries; index += 1) {
      if (archive.readUInt32LE(cursor) !== 0x02014b50) return null
      const method = archive.readUInt16LE(cursor + 10)
      const compressedSize = archive.readUInt32LE(cursor + 20)
      const filenameLength = archive.readUInt16LE(cursor + 28)
      const extraLength = archive.readUInt16LE(cursor + 30)
      const commentLength = archive.readUInt16LE(cursor + 32)
      const localOffset = archive.readUInt32LE(cursor + 42)
      const filename = archive.subarray(cursor + 46, cursor + 46 + filenameLength).toString('utf8')

      if (filename === 'manifest.json' || filename.endsWith('/manifest.json')) {
        if (archive.readUInt32LE(localOffset) !== 0x04034b50) return null
        const localNameLength = archive.readUInt16LE(localOffset + 26)
        const localExtraLength = archive.readUInt16LE(localOffset + 28)
        const dataStart = localOffset + 30 + localNameLength + localExtraLength
        const compressed = archive.subarray(dataStart, dataStart + compressedSize)
        const raw = method === 0 ? compressed : method === 8 ? inflateRawSync(compressed) : null
        if (!raw) return null
        return this.asRecord(JSON.parse(raw.toString('utf8')))
      }

      cursor += 46 + filenameLength + extraLength + commentLength
    }
    return null
  }

  private asRecord(value: unknown): Record<string, unknown> | null {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
      ? value as Record<string, unknown>
      : null
  }

  private scalar(value: unknown): string | null {
    if (typeof value === 'string') {
      const trimmed = value.trim()
      return trimmed.length > 0 ? trimmed : null
    }
    if (typeof value === 'number' && Number.isFinite(value)) return String(value)
    return null
  }

  private numberScalar(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim().length > 0) {
      const parsed = Number(value)
      return Number.isFinite(parsed) ? parsed : null
    }
    return null
  }

  private normalizeLanePolicy(value: unknown, strict: boolean): ExternalLanePolicy {
    const normalized = this.scalar(value)?.toUpperCase() ?? 'ANY'
    if (normalized === 'ANY' || normalized === 'PREFER') return normalized
    if (strict) throw new Error('VRA_EXTERNAL_LANE_POLICY_UNSUPPORTED')
    return 'ANY'
  }

  private normalizeParallelism(value: unknown, strict: boolean): number {
    const numeric = typeof value === 'number' ? value : this.numberScalar(value)
    if (numeric !== null && Number.isInteger(numeric) && numeric >= 1 && numeric <= MAX_LANE_PARALLELISM) {
      return numeric
    }
    if (strict) throw new Error('VRA_ROUTING_PARALLELISM_OUT_OF_RANGE')
    return 1
  }

  private normalizeWorkerConcurrency(value: unknown, strict: boolean): number | null {
    if (value === null || value === undefined) return null
    const numeric = typeof value === 'number' ? value : this.numberScalar(value)
    if (numeric !== null && Number.isInteger(numeric) && numeric >= 1) return numeric
    if (strict) throw new Error('VRA_ROUTING_WORKER_CONCURRENCY_INVALID')
    return null
  }

  private firstNestedScalar(root: Record<string, unknown>, paths: string[][]): string | null {
    for (const path of paths) {
      let current: unknown = root
      for (const segment of path) {
        const record = this.asRecord(current)
        if (!record) {
          current = null
          break
        }
        current = record[segment]
      }
      const value = this.scalar(current)
      if (value) return value
    }
    return null
  }

  private projectNameFromRoot(projectRoot: string): string | null {
    const normalized = projectRoot.replace(/[\\/]+$/, '')
    const parts = normalized.split(/[\\/]/).filter(Boolean)
    return parts.length > 0 ? parts[parts.length - 1] : null
  }

  private publishToIncomingAtomic(card: DurableVraDispatchCard, destination: string): void {
    if (existsSync(destination)) {
      if (this.sha256(destination) === card.sha256) return
      throw new Error('WORKSTATION_INCOMING_DESTINATION_CONFLICT')
    }

    const temp = join(
      this.worksIncomingRoot,
      `.${basename(destination)}.${card.id.slice(0, 8)}.${randomUUID()}.tmp`
    )
    try {
      copyFileSync(card.stagedPath, temp)
      if (this.sha256(temp) !== card.sha256) {
        throw new Error('WORKSTATION_INCOMING_TEMP_SHA256_MISMATCH')
      }
      // Same-directory rename is the publication point. Workstation never observes a
      // partially copied final *.vra name.
      renameSync(temp, destination)
    } finally {
      if (existsSync(temp)) {
        try {
          unlinkSync(temp)
        } catch {
          // A stale *.tmp is not visible to the VRA receiving scanner.
        }
      }
    }
  }

  private reconcileApprovedPublication(card: DurableVraDispatchCard): DurableVraDispatchCard {
    if (
      card.humanApproval !== 'APPROVED' ||
      card.dispatchPhase !== 'APPROVED' ||
      !card.publishName ||
      !card.sha256
    ) {
      return card
    }

    const destination = join(this.worksIncomingRoot, basename(card.publishName))
    if (!existsSync(destination)) return card
    try {
      if (this.sha256(destination) !== card.sha256) return card
    } catch {
      return card
    }

    // Recovery for process kill after atomic rename but before final sidecar commit.
    card.status = 'DISPATCHED'
    card.dispatchPhase = 'PUBLISHED'
    card.dispatchedUtc = card.dispatchedUtc ?? new Date().toISOString()
    card.worksPath = destination
    card.error = null
    if (card.workstationRegistration === 'NOT_READY') card.workstationRegistration = 'PENDING'
    try {
      const metadata = this.metadataFromCard(card)
      this.writeStagingMetadata(card.stagedPath, metadata)
      this.publishIncomingCommitSidecar(card, metadata)
    } catch {
      // Final VRA already exists; later reconciliation repairs sidecar before any POST.
    }
    return card
  }


  // FINAL_WIRING_B_000054V1 -- filesystem Data Commit precedes HTTP Control Registration.
  private publishIncomingCommitSidecar(card: DurableVraDispatchCard, metadata: VraStagingMetadata): void {
    if (!card.publishName || card.humanApproval !== 'APPROVED' || card.status !== 'DISPATCHED') {
      throw new Error('WORKSTATION_INCOMING_SIDECAR_PRECONDITION_FAILED')
    }
    const finalVra = join(this.worksIncomingRoot, basename(card.publishName))
    if (!existsSync(finalVra) || this.sha256(finalVra) !== card.sha256) {
      throw new Error('WORKSTATION_INCOMING_VRA_NOT_COMMITTED')
    }
    const sidecar = join(this.worksIncomingRoot, `${basename(card.publishName)}.meta.json`)
    // Before allocation this remains null. After Workstation reconciliation, mirror only
    // the authoritative allocated_lane returned by Workstation; Portal never invents it.
    this.writeJsonAtomic(sidecar, {
      ...metadata,
      allocated_lane: metadata.allocated_lane ?? null,
      human_approval: 'APPROVED',
      status: 'DISPATCHED'
    })
  }

  private async observePostDispatchLaneTruth(cardId: string): Promise<void> {
    // First make sure the just-published card has crossed Control Registration.
    // That is what allows Workstation Scheduler to allocate a real lane.
    await this.reconcileWorkstationCard(cardId)

    // Then observe Scheduler/safety truth at a short cadence.  Multiple rapid
    // dispatches share one burst and extend its deadline instead of multiplying
    // timers/HTTP storms.
    this.kickPostDispatchSafetyProbe()
  }

  private kickPostDispatchSafetyProbe(): void {
    const POST_DISPATCH_OBSERVATION_WINDOW_MS = 1600
    const POST_DISPATCH_OBSERVATION_INTERVAL_MS = 180

    this.workstationPostDispatchProbeDeadlineMs = Math.max(
      this.workstationPostDispatchProbeDeadlineMs,
      Date.now() + POST_DISPATCH_OBSERVATION_WINDOW_MS
    )

    if (this.workstationPostDispatchProbeInFlight) return

    const burst = (async (): Promise<void> => {
      // The first probe is immediate.  Later probes only observe; they never
      // assign/guess a lane or mutate Workstation scheduling authority.
      while (Date.now() <= this.workstationPostDispatchProbeDeadlineMs) {
        await this.probeWorkstationHealth()

        const remaining = this.workstationPostDispatchProbeDeadlineMs - Date.now()
        if (remaining <= 0) break
        await new Promise<void>(resolve => {
          const timer = setTimeout(
            resolve,
            Math.min(POST_DISPATCH_OBSERVATION_INTERVAL_MS, remaining)
          )
          timer.unref?.()
        })
      }
    })()

    const tracked = burst.finally(() => {
      if (this.workstationPostDispatchProbeInFlight === tracked) {
        this.workstationPostDispatchProbeInFlight = null
      }

      // A dispatch can extend the deadline during the final await.  If that
      // happened, immediately start the remaining observation window.
      if (Date.now() < this.workstationPostDispatchProbeDeadlineMs) {
        this.kickPostDispatchSafetyProbe()
      }
    })

    this.workstationPostDispatchProbeInFlight = tracked
  }

  private startWorkstationReconciler(): void {
    const tick = (): void => { void this.reconcileWorkstation() }
    tick()
    this.workstationTimer = setInterval(tick, 2500)
    this.workstationTimer.unref?.()
  }

  private async probeWorkstationHealth(): Promise<boolean> {
    const previousOnline = this.workstationOnline
    try {
      await this.workstation.health()
      this.workstationOnline = true
      this.workstationObservedUtc = new Date().toISOString()
      try {
        const safety = await this.workstation.getSafety()
        this.setWorkstationSafety(this.parseSafetyObservation(safety.body))
      } catch (error) {
        this.setWorkstationSafety(this.unknownSafetyObservation(
          error instanceof Error ? error.message : String(error),
          true
        ))
      }
    } catch (error) {
      this.workstationOnline = false
      this.workstationObservedUtc = new Date().toISOString()
      this.setWorkstationSafety(this.unknownSafetyObservation(
        error instanceof Error ? error.message : String(error),
        false
      ))
    }
    if (previousOnline !== this.workstationOnline) this.emitChanged()
    return this.workstationOnline
  }

  private reconcileWorkstation(): Promise<void> {
    if (this.workstationReconcileInFlight) return this.workstationReconcileInFlight

    const cycle = (async (): Promise<void> => {
      if (!(await this.probeWorkstationHealth())) return

      // Human AUTO authority is a bounded execution grant. Resolve eligible newly
      // staged cards in main so renderer event loss cannot strand VRA cards.
      await this.reconcileAutoAuthorizedStagedCards()

      for (const card of this.cards) {
        if (card.humanApproval !== 'APPROVED' || card.dispatchPhase !== 'PUBLISHED' || card.status !== 'DISPATCHED') continue
        await this.reconcileWorkstationCard(card.id)
      }
    })()

    const tracked = cycle.finally(() => {
      if (this.workstationReconcileInFlight === tracked) {
        this.workstationReconcileInFlight = null
      }
    })
    this.workstationReconcileInFlight = tracked
    return tracked
  }

  private async reconcileWorkstationCard(cardId: string): Promise<void> {
    if (this.workstationInFlight.has(cardId)) return
    const card = this.cards.find(candidate => candidate.id === cardId)
    if (!card || card.humanApproval !== 'APPROVED' || card.dispatchPhase !== 'PUBLISHED' || card.status !== 'DISPATCHED') return
    if (!card.publishName || !card.sha256 || card.originVera === 'UNKNOWN' || !card.originSession || !card.originWindow) return

    this.workstationInFlight.add(cardId)
    try {
      const finalVra = join(this.worksIncomingRoot, basename(card.publishName))
      if (!existsSync(finalVra) || this.sha256(finalVra) !== card.sha256) {
        this.updateWorkstationState(card, { workstationRegistration: 'PENDING', workstationLastError: 'WORKSTATION_DATA_COMMIT_NOT_READY' })
        return
      }

      // The Workstation job_api requires this committed approval sidecar beside final *.vra.
      this.publishIncomingCommitSidecar(card, this.metadataFromCard(card))

      // Safety state is Workstation authority. Until an exact RUNNING observation exists,
      // Portal never attempts a new Control Registration. Already-registered jobs remain observable.
      if (card.workstationRegistration !== 'REGISTERED' && this.workstationSafety.state !== 'RUNNING') {
        this.updateWorkstationState(card, {
          workstationRegistration: 'PENDING',
          workstationLastError: `WORKSTATION_SAFETY_HOLD:${this.workstationSafety.state}`
        })
        return
      }

      if (card.workstationRegistration !== 'REGISTERED') {
        this.updateWorkstationState(card, {
          workstationRegistration: 'REGISTERING',
          registrationAttemptUtc: new Date().toISOString(),
          workstationLastError: null
        })
        try {
          const response = await this.workstation.registerJob({
            artifact_filename: basename(card.publishName),
            artifact_sha256: card.sha256
          })
          const job = this.requireRecord(response.body.job, 'WORKSTATION_REGISTER_JOB_RESPONSE_MISSING')
          this.assertWorkstationJobIdentity(card, job)
          card.workstationRegistration = 'REGISTERED'
          card.registeredUtc = card.registeredUtc ?? new Date().toISOString()
          card.workstationLastError = null
          this.applyWorkstationJob(card, job)
          this.persistCardState(card)
        } catch (error) {
          const safetyHold = error instanceof WorkstationHttpError && error.code === 'SAFETY_STATE_REJECTED'
          if (safetyHold) {
            // Safety holds are not permanent registration failures. Preserve the approved VRA
            // and retry only after Workstation authoritatively reports RUNNING again.
            card.workstationRegistration = 'PENDING'
          } else {
            // Preserve the Final Wiring B offline/idempotent registration semantics and
            // its verified compatibility shape for non-safety HTTP failures.
            card.workstationRegistration = error instanceof WorkstationHttpError && [400, 403, 409].includes(error.status)
              ? 'BLOCKED'
              : 'PENDING'
          }
          card.workstationLastError = error instanceof Error ? error.message : String(error)
          this.persistCardState(card)
          return
        }
      }

      try {
        const response = await this.workstation.getJob(card.jobId)
        const job = this.requireRecord(response.body.job, 'WORKSTATION_JOB_RESPONSE_MISSING')
        this.assertWorkstationJobIdentity(card, job)
        const before = this.workstationCardSyncKey(card)
        this.applyWorkstationJob(card, job)

        // 000093V5H1: never expose a half-successful reconcile to Human UI.
        // A successful GET /v1/jobs is only one phase. If downstream Evidence pickup
        // still fails, clearing lastError here creates a yellow/red oscillation on every poll.
        // Preserve the previous error until the entire reconcile cycle succeeds.
        const evidenceNeedsPickup =
          card.workstationEvidenceState === 'AVAILABLE' &&
          (!card.evidenceIdentity || !this.evidenceCachePresent(card))
        if (evidenceNeedsPickup) await this.retrieveEvidence(card)

        await syncAutoRegistryWorkstationLifecycle(
          this.registryRuntime.core,
          this.registryRuntime.store,
          {
            jobId: card.jobId,
            artifactId: card.artifactId,
            correlationId: card.correlationId,
            portalPublished: card.dispatchPhase === 'PUBLISHED' && card.status === 'DISPATCHED',
            workstationRegistration: card.workstationRegistration,
            workstationJobState: card.workstationJobState,
            allocatedLane: card.allocatedLane,
            evidenceId: card.evidenceIdentity,
            evidenceState: card.workstationEvidenceState,
            evidenceReturnState: card.workstationEvidenceReturnState
          }
        )

        card.workstationLastError = null
        if (before !== this.workstationCardSyncKey(card)) this.persistCardState(card)
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        if (card.workstationLastError !== message) {
          card.workstationLastError = message
          this.persistCardState(card)
        }
      }
    } finally {
      this.workstationInFlight.delete(cardId)
    }
  }

  /**
   * 000079V5: only material Workstation state is allowed to wake the renderer.
   * observed/poll time is intentionally excluded.
   */
  private workstationCardSyncKey(card: DurableVraDispatchCard): string {
    return JSON.stringify({
      registration: card.workstationRegistration,
      registrationAttemptUtc: card.registrationAttemptUtc,
      registeredUtc: card.registeredUtc,
      jobState: card.workstationJobState,
      allocatedLane: card.allocatedLane,
      evidenceState: card.workstationEvidenceState,
      evidenceReturnState: card.workstationEvidenceReturnState,
      evidenceIdentity: card.evidenceIdentity,
      evidenceCacheName: card.evidenceCacheName,
      lastError: card.workstationLastError
    })
  }

  private updateWorkstationState(card: DurableVraDispatchCard, patch: Partial<DurableVraDispatchCard>): void {
    const before = this.workstationCardSyncKey(card)
    Object.assign(card, patch)
    if (before !== this.workstationCardSyncKey(card)) this.persistCardState(card)
  }

  private applyWorkstationJob(card: DurableVraDispatchCard, job: Record<string, unknown>): boolean {
    const before = this.workstationCardSyncKey(card)
    const state = this.optionalString(job.state)
    if (state && ['REGISTERED','DISPATCHED','EXECUTING','SUCCEEDED','FAILED','REJECTED','ROLLED_BACK'].includes(state)) {
      card.workstationJobState = state as WorkstationJobState
    }
    card.allocatedLane = this.optionalString(job.allocated_lane)
    card.workstationEvidenceState = this.optionalString(job.evidence_state)
    card.workstationEvidenceReturnState = this.optionalString(job.evidence_return_state)
    return before !== this.workstationCardSyncKey(card)
  }

  private evidenceCachePresent(card: DurableVraDispatchCard): boolean {
    if (!card.evidenceCacheName) return false
    return existsSync(join(this.stagingRoot, 'workstation-evidence', card.evidenceCacheName))
  }

  private async retrieveEvidence(card: DurableVraDispatchCard): Promise<void> {
    const before = this.workstationCardSyncKey(card)
    const response = await this.workstation.getEvidence(card.jobId)
    const outer = this.requireRecord(response.body.evidence, 'WORKSTATION_EVIDENCE_RESPONSE_MISSING')
    const envelope = this.requireRecord(outer.envelope, 'WORKSTATION_EVIDENCE_ENVELOPE_MISSING')
    const evidenceId = this.requiredString(envelope.evidence_id, 'WORKSTATION_EVIDENCE_ID_MISSING')
    if (this.requiredString(envelope.job_id, 'WORKSTATION_EVIDENCE_JOB_ID_MISSING') !== card.jobId) throw new Error('WORKSTATION_EVIDENCE_JOB_ID_MISMATCH')
    if (this.requiredString(envelope.artifact_id, 'WORKSTATION_EVIDENCE_ARTIFACT_ID_MISSING') !== card.artifactId) throw new Error('WORKSTATION_EVIDENCE_ARTIFACT_ID_MISMATCH')
    const origin = this.requireRecord(envelope.origin, 'WORKSTATION_EVIDENCE_ORIGIN_MISSING')
    this.assertOriginRoute(card, origin)
    const evidence = this.requireRecord(envelope.evidence, 'WORKSTATION_EXECUTION_EVIDENCE_MISSING')
    if (this.requiredString(evidence.evidence_id, 'WORKSTATION_EXECUTION_EVIDENCE_ID_MISSING') !== evidenceId) throw new Error('WORKSTATION_EVIDENCE_IDENTITY_MISMATCH')
    if (this.requiredString(evidence.job_id, 'WORKSTATION_EXECUTION_JOB_ID_MISSING') !== card.jobId) throw new Error('WORKSTATION_EXECUTION_JOB_ID_MISMATCH')
    if (this.requiredString(evidence.artifact_id, 'WORKSTATION_EXECUTION_ARTIFACT_ID_MISSING') !== card.artifactId) throw new Error('WORKSTATION_EXECUTION_ARTIFACT_ID_MISMATCH')
    if (this.optionalString(envelope.required_reexecution_authority) !== 'HUMAN_APPLY') throw new Error('WORKSTATION_EVIDENCE_HUMAN_GATE_MISMATCH')

    // 000091V5H2: non-authoritative hidden Observability Tap.
    // Analysis failure/degradation must never block the exact-origin Evidence return path or ACK state machine.
    await this.evidenceObservability.observeAndPersist({
      raw: response.body,
      jobId: card.jobId,
      artifactId: card.artifactId,
      evidenceId,
      originSession: card.originSession
    })

    const cacheName = `${createHash('sha256').update(card.jobId).digest('hex')}.json`
    const cacheRoot = join(this.stagingRoot, 'workstation-evidence')
    mkdirSync(cacheRoot, { recursive: true })
    this.writeJsonAtomic(join(cacheRoot, cacheName), response.body)
    card.evidenceIdentity = evidenceId
    card.evidenceCacheName = cacheName
    card.workstationEvidenceState = this.optionalString(outer.evidence_state) ?? card.workstationEvidenceState
    card.workstationEvidenceReturnState = this.optionalString(outer.evidence_return_state) ?? card.workstationEvidenceReturnState
    card.workstationLastError = null
    if (before !== this.workstationCardSyncKey(card)) this.persistCardState(card)
  }

  private assertWorkstationJobIdentity(card: DurableVraDispatchCard, job: Record<string, unknown>): void {
    const checks: Array<[string, string | null, string | null]> = [
      ['job_id', card.jobId, this.optionalString(job.job_id)],
      ['artifact_id', card.artifactId, this.optionalString(job.artifact_id)],
      ['artifact_sha256', card.sha256, this.optionalString(job.artifact_sha256)],
      ['origin_vera', card.originVera, this.optionalString(job.origin_vera)],
      ['origin_session', card.originSession, this.optionalString(job.origin_session)],
      ['origin_window', card.originWindow, this.optionalString(job.origin_window)],
      ['return_channel', card.returnChannel, this.optionalString(job.return_channel)]
    ]
    for (const [field, expected, actual] of checks) {
      if (!expected || actual !== expected) throw new Error(`WORKSTATION_JOB_IDENTITY_MISMATCH:${field}`)
    }
  }

  private assertOriginRoute(card: DurableVraDispatchCard, origin: Record<string, unknown>): void {
    const expectedVera = this.originVeraFromSession(card.originSession)
    if (expectedVera === 'UNKNOWN' || expectedVera !== card.originVera) throw new Error('EVIDENCE_ORIGIN_VERA_FAIL_CLOSED')
    if (card.originWindow !== card.originSession) throw new Error('EVIDENCE_ORIGIN_WINDOW_FAIL_CLOSED')
    const checks: Array<[string, string | null, string | null]> = [
      ['job_id', card.jobId, this.optionalString(origin.job_id)],
      ['origin_vera', card.originVera, this.optionalString(origin.origin_vera)],
      ['origin_session', card.originSession, this.optionalString(origin.origin_session)],
      ['origin_window', card.originWindow, this.optionalString(origin.origin_window)],
      ['return_channel', card.returnChannel, this.optionalString(origin.return_channel)],
      ['correlation_id', card.correlationId, this.optionalString(origin.correlation_id)]
    ]
    for (const [field, expected, actual] of checks) {
      if (!expected || actual !== expected) throw new Error(`EVIDENCE_ORIGIN_ROUTE_MISMATCH:${field}`)
    }
  }

  /**
   * 000082V5 — Ray Evidence optic-nerve bridge.
   *
   * Workstation's HTTP Evidence envelope intentionally contains immutable identity
   * plus evidence_path, not the potentially-large verification body.  Session Portal
   * runs on the same trusted local machine, so it may enrich the Human/Vera return
   * payload by reading that file READ ONLY — but only when the canonical path is
   * inside vertex_workstation/runtime/lanes and the file is bounded.
   */
  private readBoundedVerificationEvidenceBody(executionEvidence: Record<string, unknown>): string | null {
    const rawPath = this.optionalString(executionEvidence.evidence_path)
    if (!rawPath) return null

    const maxBytes = 256 * 1024
    try {
      const developmentRoot = dirname(this.worksIncomingRoot)
      const allowedRoot = realpathSync(join(developmentRoot, 'vertex_workstation', 'runtime', 'lanes'))
      const candidate = realpathSync(rawPath)
      const rel = relative(allowedRoot, candidate)

      if (!rel || rel.startsWith('..') || isAbsolute(rel)) {
        return `[VERIFICATION EVIDENCE BODY BLOCKED]\nreason=PATH_OUTSIDE_WORKSTATION_LANES\npath=${rawPath}`
      }

      if (!candidate.toLowerCase().endsWith('.json')) {
        return `[VERIFICATION EVIDENCE BODY BLOCKED]\nreason=NON_JSON_EVIDENCE\npath=${rawPath}`
      }

      const stat = statSync(candidate)
      if (!stat.isFile()) {
        return `[VERIFICATION EVIDENCE BODY BLOCKED]\nreason=NOT_A_FILE\npath=${rawPath}`
      }

      if (stat.size > maxBytes) {
        return [
          '[VERIFICATION EVIDENCE BODY OMITTED]',
          `reason=SIZE_LIMIT`,
          `size=${stat.size}`,
          `limit=${maxBytes}`,
          `path=${rawPath}`
        ].join('\n')
      }

      const body = readFileSync(candidate, 'utf8')
      return [
        '[VERIFICATION EVIDENCE BODY]',
        `path=${rawPath}`,
        `bytes=${Buffer.byteLength(body, 'utf8')}`,
        '',
        body
      ].join('\n')
    } catch (error) {
      return [
        '[VERIFICATION EVIDENCE BODY UNAVAILABLE]',
        `path=${rawPath}`,
        `error=${error instanceof Error ? error.message : String(error)}`
      ].join('\n')
    }
  }

  private cardsForRenderer(): Array<DurableVraDispatchCard & { evidenceDeliveryPayload?: string }> {
    const sorted = [...this.cards].sort((a, b) => b.capturedUtc.localeCompare(a.capturedUtc))
    const heads = new Map<string, string>()

    const queued = this.cards
      .filter(card => this.evidenceDeliveryEligible(card))
      .sort((a, b) => {
        const byEvidence = this.evidenceDeliveryOrderKey(a).localeCompare(this.evidenceDeliveryOrderKey(b))
        if (byEvidence !== 0) return byEvidence
        return a.id.localeCompare(b.id)
      })

    for (const card of queued) {
      const session = card.originSession
      if (session && !heads.has(session)) heads.set(session, card.id)
    }

    return sorted.map(card =>
      this.cardForRenderer(card, Boolean(card.originSession && heads.get(card.originSession) === card.id))
    )
  }

  private evidenceDeliveryEligible(card: DurableVraDispatchCard): boolean {
    return Boolean(
      card.evidenceIdentity &&
      card.evidenceCacheName &&
      card.workstationEvidenceState === 'AVAILABLE' &&
      card.workstationEvidenceReturnState === 'RETURN_QUEUED' &&
      card.originVera !== 'UNKNOWN' &&
      card.originSession &&
      card.originWindow === card.originSession &&
      registryAllowsEvidenceReturn(this.registryRuntime.store, {
        jobId: card.jobId,
        artifactId: card.artifactId,
        correlationId: card.correlationId,
        originVera: card.originVera,
        originSession: card.originSession,
        originWindow: card.originWindow,
        returnChannel: card.returnChannel,
        evidenceId: card.evidenceIdentity
      })
    )
  }

  private evidenceDeliveryOrderKey(card: DurableVraDispatchCard): string {
    if (!card.evidenceCacheName) return `9:${card.capturedUtc}`
    try {
      const cache = join(this.stagingRoot, 'workstation-evidence', basename(card.evidenceCacheName))
      const root = this.requireRecord(JSON.parse(readFileSync(cache, 'utf8')) as unknown, 'WORKSTATION_EVIDENCE_CACHE_INVALID')
      const outer = this.requireRecord(root.evidence, 'WORKSTATION_EVIDENCE_CACHE_OUTER_MISSING')
      const envelope = this.requireRecord(outer.envelope, 'WORKSTATION_EVIDENCE_CACHE_ENVELOPE_MISSING')
      const execution = this.requireRecord(envelope.evidence, 'WORKSTATION_EVIDENCE_CACHE_EXECUTION_MISSING')
      const timestamps = this.requireRecord(execution.timestamps, 'WORKSTATION_EVIDENCE_CACHE_TIMESTAMPS_MISSING')
      const completed = this.optionalString(timestamps.completed_at)
      if (completed) {
        const numeric = completed.startsWith('unix-ms:') ? Number(completed.slice('unix-ms:'.length)) : Number.NaN
        if (Number.isFinite(numeric)) return `0:${String(Math.trunc(numeric)).padStart(20, '0')}`
        const parsed = Date.parse(completed)
        if (Number.isFinite(parsed)) return `0:${String(parsed).padStart(20, '0')}`
      }
    } catch {
      // Durable card timestamps remain a deterministic FIFO fallback.
    }
    return `1:${card.dispatchedUtc ?? card.capturedUtc}`
  }

  private currentExecutionLaneEntries(raw: string[], activeJobs: number): string[] {
    if (activeJobs === 0) return []

    // Durable /v1/safety lane inventory may retain terminal and Human-wait states.
    // Only states that represent active machine work may illuminate the 32-lane pulse.
    const activeStates = new Set([
      'INSPECTING',
      'STAGED',
      'ALLOCATED',
      'DISPATCHED',
      'EXECUTING',
      'RUNNING',
      'APPLYING',
      'VERIFYING',
      'ROLLING_BACK'
    ])

    const active = raw.filter(entry => {
      const separator = entry.indexOf(':')
      if (separator <= 0) return false
      const laneId = entry.slice(0, separator).trim()
      const laneState = entry.slice(separator + 1).trim().toUpperCase()
      return /^lane-\d{2}$/.test(laneId) && activeStates.has(laneState)
    })

    // Never invent lane identities.  If Workstation reports fewer explicit active
    // lane ids than activeJobs, the count remains authoritative and the grid stays
    // fail-closed for the unknown identities.  If the durable inventory is stale
    // and contains extras, cap it to activeJobs.
    return active.slice(0, activeJobs)
  }

  private cardForRenderer(
    card: DurableVraDispatchCard,
    allowEvidenceDelivery = false
  ): DurableVraDispatchCard & { evidenceDeliveryPayload?: string } {
    // 000096V5H1: evidenceDeliveryEligible() is a runtime predicate, not a
    // TypeScript type predicate.  Capture nullable fields into local constants
    // and narrow them explicitly before passing evidenceCacheName to basename().
    const evidenceCacheName = card.evidenceCacheName
    const evidenceIdentity = card.evidenceIdentity
    if (
      !allowEvidenceDelivery ||
      !this.evidenceDeliveryEligible(card) ||
      !evidenceCacheName ||
      !evidenceIdentity
    ) return { ...card }

    try {
      const cache = join(this.stagingRoot, 'workstation-evidence', basename(evidenceCacheName))
      const evidence = JSON.parse(readFileSync(cache, 'utf8')) as unknown
      const outer = this.requireRecord(
        this.requireRecord(evidence, 'WORKSTATION_EVIDENCE_CACHE_INVALID').evidence,
        'WORKSTATION_EVIDENCE_CACHE_OUTER_MISSING'
      )
      const envelope = this.requireRecord(outer.envelope, 'WORKSTATION_EVIDENCE_CACHE_ENVELOPE_MISSING')
      const executionEvidence = this.requireRecord(
        envelope.evidence,
        'WORKSTATION_EVIDENCE_CACHE_EXECUTION_MISSING'
      )
      const verificationBody = this.readBoundedVerificationEvidenceBody(executionEvidence)

      const text = [
        '[VERTEX WORKSTATION EVIDENCE RETURN]',
        `job_id=${card.jobId}`,
        `artifact_id=${card.artifactId ?? ''}`,
        `evidence_id=${evidenceIdentity}`,
        `origin_session=${card.originSession ?? ''}`,
        `correlation_id=${card.correlationId}`,
        '',
        JSON.stringify(evidence, null, 2),
        ...(verificationBody ? ['', verificationBody] : []),
        '',
        'Re-execution requires a new HUMAN_APPLY approval.'
      ].join('\n')
      return { ...card, evidenceDeliveryPayload: text }
    } catch {
      return { ...card }
    }
  }

  private persistCardState(card: DurableVraDispatchCard): void {
    try {
      this.writeStagingMetadata(card.stagedPath, this.metadataFromCard(card))
      if (card.status === 'DISPATCHED' && card.dispatchPhase === 'PUBLISHED' && card.publishName) {
        this.publishIncomingCommitSidecar(card, this.metadataFromCard(card))
      }
    } catch (error) {
      card.workstationLastError = error instanceof Error ? error.message : String(error)
    }
    this.persistAndEmit()
  }

  private setWorkstationSafety(next: WorkstationSafetyObservation): void {
    const previousKey = this.safetyObservationKey(this.workstationSafety)
    this.workstationSafety = next
    if (previousKey !== this.safetyObservationKey(next)) this.emitChanged()
  }

  private safetyObservationKey(value: WorkstationSafetyObservation): string {
    return JSON.stringify({
      online: value.online,
      state: value.state,
      generation: value.generation,
      lastError: value.lastError,
      metrics: value.metrics,
      lastTransition: value.lastTransition
    })
  }

  private unknownSafetyObservation(lastError: string, online: boolean): WorkstationSafetyObservation {
    return {
      schema: null,
      online,
      state: 'UNKNOWN',
      generation: null,
      latched: null,
      newWorkAllowed: null,
      activeContinuationAllowed: null,
      autoReset: null,
      autoResume: null,
      lastTransition: null,
      metrics: null,
      executionPlane: 'UNKNOWN',
      observationPlane: 'UNKNOWN',
      evidenceReturnPlane: 'UNKNOWN',
      observedUtc: new Date().toISOString(),
      lastError
    }
  }

  private parseSafetyObservation(body: Record<string, unknown>): WorkstationSafetyObservation {
    const safety = this.requireRecord(body.safety, 'WORKSTATION_SAFETY_RESPONSE_MISSING')
    const metricsRaw = this.requireRecord(body.metrics, 'WORKSTATION_SAFETY_METRICS_MISSING')
    if (safety.schema !== 'vertex-workstation/durable-safety-state-1') throw new Error('WORKSTATION_SAFETY_SCHEMA_MISMATCH')
    const state = this.requireSafetyState(safety.state)
    const generation = this.requireNonNegativeInteger(safety.generation, 'WORKSTATION_SAFETY_GENERATION_INVALID')
    const latched = this.requireBoolean(safety.latched, 'WORKSTATION_SAFETY_LATCHED_INVALID')
    const newWorkAllowed = this.requireBoolean(safety.new_work_allowed, 'WORKSTATION_SAFETY_NEW_WORK_INVALID')
    const activeContinuationAllowed = this.requireBoolean(safety.active_continuation_allowed, 'WORKSTATION_SAFETY_ACTIVE_CONTINUATION_INVALID')
    if (safety.auto_reset !== false || safety.auto_resume !== false) throw new Error('WORKSTATION_SAFETY_AUTO_RELEASE_FORBIDDEN')

    const activeJobs = this.requireNonNegativeInteger(
      metricsRaw.active_jobs,
      'WORKSTATION_SAFETY_ACTIVE_JOBS_INVALID'
    )
    const rawLaneStates = this.requireStringArray(
      metricsRaw.active_lanes,
      'WORKSTATION_SAFETY_ACTIVE_LANES_INVALID'
    )
    const metrics: WorkstationSafetyMetrics = {
      activeJobs,
      queuedJobs: this.requireNonNegativeInteger(metricsRaw.queued_jobs, 'WORKSTATION_SAFETY_QUEUED_JOBS_INVALID'),
      // 000096V5: /v1/safety active_lanes is a durable lane-state inventory, not
      // a guaranteed list of currently executing lanes.  Never light terminal /
      // Human-wait lanes as ACTIVE.  activeJobs=0 is an absolute all-off truth.
      activeLanes: this.currentExecutionLaneEntries(rawLaneStates, activeJobs),
      locks: this.requireNonNegativeInteger(metricsRaw.locks, 'WORKSTATION_SAFETY_LOCKS_INVALID'),
      recoveryResult: this.requiredString(metricsRaw.recovery_result, 'WORKSTATION_SAFETY_RECOVERY_RESULT_MISSING')
    }
    const lastTransition = safety.last_transition === null || safety.last_transition === undefined
      ? null
      : this.parseSafetyTransition(this.requireRecord(safety.last_transition, 'WORKSTATION_SAFETY_LAST_TRANSITION_INVALID'))
    const executionPlane = this.requiredString(body.execution_plane, 'WORKSTATION_SAFETY_EXECUTION_PLANE_MISSING')
    const observationPlane = this.requiredString(body.observation_plane, 'WORKSTATION_SAFETY_OBSERVATION_PLANE_MISSING')
    const evidenceReturnPlane = this.requiredString(body.evidence_return_plane, 'WORKSTATION_SAFETY_EVIDENCE_PLANE_MISSING')
    if (!['AVAILABLE', 'STOPPED'].includes(executionPlane) || observationPlane !== 'ALIVE' || evidenceReturnPlane !== 'ALIVE') {
      throw new Error('WORKSTATION_SAFETY_PLANE_CONTRACT_MISMATCH')
    }
    if (latched !== (state === 'ESTOP_LATCHED')) throw new Error('WORKSTATION_SAFETY_LATCH_CONSISTENCY_MISMATCH')
    if (newWorkAllowed !== (state === 'RUNNING')) throw new Error('WORKSTATION_SAFETY_NEW_WORK_CONSISTENCY_MISMATCH')
    if (activeContinuationAllowed !== ['RUNNING', 'DRAINING'].includes(state)) throw new Error('WORKSTATION_SAFETY_CONTINUATION_CONSISTENCY_MISMATCH')
    if (executionPlane !== (['RUNNING', 'DRAINING'].includes(state) ? 'AVAILABLE' : 'STOPPED')) throw new Error('WORKSTATION_SAFETY_EXECUTION_PLANE_STATE_MISMATCH')

    return {
      schema: 'vertex-workstation/durable-safety-state-1',
      online: true,
      state,
      generation,
      latched,
      newWorkAllowed,
      activeContinuationAllowed,
      autoReset: false,
      autoResume: false,
      lastTransition,
      metrics,
      executionPlane: executionPlane as 'AVAILABLE' | 'STOPPED',
      observationPlane: 'ALIVE',
      evidenceReturnPlane: 'ALIVE',
      observedUtc: new Date().toISOString(),
      lastError: null
    }
  }

  private parseSafetyActionResponse(
    body: Record<string, unknown>,
    requestedAction: WorkstationSafetyAction
  ): Omit<WorkstationSafetyActionResult, 'observation'> {
    const action = this.requireSafetyAction(body.action)
    if (action !== requestedAction) throw new Error('WORKSTATION_SAFETY_ACTION_RESPONSE_MISMATCH')
    const previousState = this.requireSafetyState(body.previous_state)
    const state = this.requireSafetyState(body.state)
    const generation = this.requireNonNegativeInteger(body.generation, 'WORKSTATION_SAFETY_ACTION_GENERATION_INVALID')
    const idempotent = this.requireBoolean(body.idempotent, 'WORKSTATION_SAFETY_ACTION_IDEMPOTENCY_INVALID')
    if (body.auto_reset !== false || body.auto_resume !== false || body.authority !== 'HUMAN') {
      throw new Error('WORKSTATION_SAFETY_ACTION_AUTHORITY_MISMATCH')
    }
    return { action, previousState, state, generation, idempotent, authority: 'HUMAN' }
  }

  private parseSafetyTransition(value: Record<string, unknown>): WorkstationSafetyTransition {
    if (value.authority !== 'HUMAN') throw new Error('WORKSTATION_SAFETY_TRANSITION_AUTHORITY_MISMATCH')
    return {
      timestamp: this.requiredString(value.timestamp, 'WORKSTATION_SAFETY_TRANSITION_TIMESTAMP_MISSING'),
      requestId: this.requiredString(value.request_id, 'WORKSTATION_SAFETY_TRANSITION_REQUEST_ID_MISSING'),
      action: this.requireSafetyAction(value.action),
      previousState: this.requireSafetyState(value.previous_state),
      newState: this.requireSafetyState(value.new_state),
      authority: 'HUMAN',
      reason: this.requiredString(value.reason, 'WORKSTATION_SAFETY_TRANSITION_REASON_MISSING'),
      activeJobs: this.requireNonNegativeInteger(value.active_jobs, 'WORKSTATION_SAFETY_TRANSITION_ACTIVE_JOBS_INVALID'),
      queuedJobs: this.requireNonNegativeInteger(value.queued_jobs, 'WORKSTATION_SAFETY_TRANSITION_QUEUED_JOBS_INVALID'),
      activeLanes: this.requireStringArray(value.active_lanes, 'WORKSTATION_SAFETY_TRANSITION_ACTIVE_LANES_INVALID'),
      locks: this.requireNonNegativeInteger(value.locks, 'WORKSTATION_SAFETY_TRANSITION_LOCKS_INVALID'),
      recoveryResult: this.requiredString(value.recovery_result, 'WORKSTATION_SAFETY_TRANSITION_RECOVERY_RESULT_MISSING')
    }
  }

  private requireSafetyState(value: unknown): WorkstationSafetyState {
    if (value === 'RUNNING' || value === 'DRAINING' || value === 'ESTOP_LATCHED' || value === 'RESET_READY') return value
    throw new Error('WORKSTATION_SAFETY_STATE_INVALID')
  }

  private requireSafetyAction(value: unknown): WorkstationSafetyAction {
    if (value === 'DRAIN' || value === 'ESTOP' || value === 'RESET' || value === 'RESUME') return value
    throw new Error('WORKSTATION_SAFETY_ACTION_INVALID')
  }

  private requireNonNegativeInteger(value: unknown, message: string): number {
    if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0) throw new Error(message)
    return value
  }

  private requireBoolean(value: unknown, message: string): boolean {
    if (typeof value !== 'boolean') throw new Error(message)
    return value
  }

  private requireStringArray(value: unknown, message: string): string[] {
    if (!Array.isArray(value) || value.some(item => typeof item !== 'string')) throw new Error(message)
    return value.map(item => item.trim()).filter(Boolean)
  }

  private requireRecord(value: unknown, message: string): Record<string, unknown> {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error(message)
    return value as Record<string, unknown>
  }

  private optionalString(value: unknown): string | null {
    return typeof value === 'string' && value.trim() ? value.trim() : null
  }

  private requiredString(value: unknown, message: string): string {
    const result = this.optionalString(value)
    if (!result) throw new Error(message)
    return result
  }

  private workstationArtifactFilename(card: DurableVraDispatchCard): string {
    const artifactId = card.artifactId?.trim() ?? ''
    if (!artifactId || artifactId.includes('/') || artifactId.includes('\\')) {
      throw new Error('WORKSTATION_ARTIFACT_ID_FILENAME_REJECTED')
    }
    const filename = `${artifactId}.vra`
    if (basename(filename) !== filename) throw new Error('WORKSTATION_ARTIFACT_FILENAME_REJECTED')
    return filename
  }

  private safeDestination(root: string, card: VraDispatchCard): string {
    const canonical = join(root, basename(card.filename))
    if (!existsSync(canonical)) return canonical

    try {
      if (this.sha256(canonical) === card.sha256) return canonical
    } catch {
      // Fall through to a duplicate-safe filename.
    }

    const extension = extname(card.filename)
    const stem = basename(card.filename, extension)
    return join(root, `${stem}-${card.id.slice(0, 8)}${extension}`)
  }

  private sha256(path: string): string {
    return createHash('sha256').update(readFileSync(path)).digest('hex')
  }

  private loadLedger(): DurableVraDispatchCard[] {
    let ledgerCards: VraDispatchCard[] = []

    if (existsSync(this.ledgerPath)) {
      try {
        const parsed = JSON.parse(readFileSync(this.ledgerPath, 'utf8')) as {
          cards?: VraDispatchCard[]
        }
        if (Array.isArray(parsed.cards)) {
          ledgerCards = parsed.cards.filter(card => typeof card?.id === 'string')
        }
      } catch {
        // Sidecar recovery below remains authoritative if ledger was interrupted.
      }
    }

    const metadata = this.loadStagingMetadata()
    const metadataById = new Map(metadata.map(item => [item.capture_id, item]))
    const removed = new Set(
      metadata.filter(item => item.status === 'REMOVED').map(item => item.capture_id)
    )
    const cards = new Map<string, DurableVraDispatchCard>()

    for (const raw of ledgerCards) {
      if (removed.has(raw.id)) continue
      const sidecar = metadataById.get(raw.id) ?? null
      const hydrated = this.hydrateCard(raw, sidecar, sidecar === null)
      cards.set(hydrated.id, hydrated)

      // Legacy-only migration: persisted sourceSessionId may seed origin only when no H1/H2
      // sidecar exists. New Capture is never allowed to use this fallback.
      if (!metadataById.has(raw.id) && existsSync(raw.stagedPath)) {
        try {
          this.writeStagingMetadata(raw.stagedPath, this.metadataFromCard(hydrated))
        } catch {
          // Ledger card remains available; future mutation can retry sidecar persistence.
        }
      }
    }

    for (const item of metadata) {
      if (removed.has(item.capture_id) || cards.has(item.capture_id)) continue
      const recovered = this.recoverCard(item)
      if (recovered) cards.set(recovered.id, recovered)
    }

    return [...cards.values()]
  }

  private emitChanged(): void {
    for (const listener of this.listeners) listener()
  }

  private persistAndEmit(): void {
    const ledger: PersistedLedger = { cards: this.cards }
    this.writeJsonAtomic(this.ledgerPath, ledger)
    this.emitChanged()
  }

}
