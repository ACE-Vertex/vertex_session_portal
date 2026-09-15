export type SidebarTab = 'PROJECT' | 'VCR' | 'VCA' | 'AI'
export type SessionKind = 'MAIN' | 'SEARCH' | 'OPTIONAL'

export interface SessionState {
  id: string
  title: string
  kind: SessionKind
  position: number
  active: boolean
  priority: boolean
}

export type VirtualArdRole =
  | 'ARCHITECT'
  | 'DEVELOPER'
  | 'REVIEWER'

export type SessionMessageActor =
  | 'HUMAN'
  | 'VERA'
  | 'SYSTEM'

export type HandoffKind =
  | 'PLAN'
  | 'IMPLEMENTATION'
  | 'REVIEW'
  | 'EVIDENCE'
  | 'NOTE'

export interface VirtualArdMission {
  id: string
  objective: string
  createdUtc: string
}

export interface VirtualArdProjection {
  missionId: string
  sessionId: string
  role: VirtualArdRole
  brief: string
}

export interface SessionMessage {
  id: string
  missionId: string
  sessionId: string
  actor: SessionMessageActor
  body: string
  createdUtc: string
}

export interface VirtualArdHandoff {
  id: string
  missionId: string
  fromSessionId: string
  toSessionId: string
  kind: HandoffKind
  body: string
  createdUtc: string
}

export interface VirtualArdState {
  mission: VirtualArdMission
  projections: VirtualArdProjection[]
  messages: SessionMessage[]
  handoffs: VirtualArdHandoff[]
}

export interface PortalBootstrapState {
  sidebarTab: SidebarTab
  sessions: SessionState[]
  virtualArd: VirtualArdState | null
}

export interface VirtualArdAssignment {
  sessionId: string
  role: VirtualArdRole
  brief: string
}

export interface ProjectVirtualArdRequest {
  objective: string
  assignments: VirtualArdAssignment[]
}

export interface AppendSessionMessageRequest {
  missionId: string
  sessionId: string
  actor: SessionMessageActor
  body: string
}

export interface CreateVirtualArdHandoffRequest {
  missionId: string
  fromSessionId: string
  toSessionId: string
  kind: HandoffKind
  body: string
}

export type PortalControlCommand =
  | { type: 'SIDEBAR_SWITCH'; tab: SidebarTab }
  | { type: 'SESSION_FOCUS'; sessionId: string }
  | { type: 'SESSION_EXPAND'; sessionId: string }
  | { type: 'VCR_OPEN'; key: string }
  | { type: 'VCA_SEARCH'; query: string }
  | { type: 'PROJECT_REVEAL'; path: string }

export type PortalWindowFitReason = 'BOOTSTRAP' | 'VERA_LAYOUT'

export interface PortalWindowFitRequest {
  contentWidth: number
  contentHeight: number
  reason: PortalWindowFitReason
}

export interface PortalWindowFitResult {
  applied: boolean
  reason: PortalWindowFitReason
  width: number
  height: number
  x: number
  y: number
  workAreaWidth: number
  workAreaHeight: number
  skippedReason: string | null
}

export interface VertexPortalApi {
  submitFirmwareChangeDecision: (detail: unknown) => Promise<unknown>

  bootstrap(): Promise<PortalBootstrapState>
  setPrioritySession(sessionId: string): Promise<PortalBootstrapState>
  activateNextMainLane(): Promise<PortalBootstrapState>
  setSidebarTab(tab: SidebarTab): Promise<void>
  fitMainWindow(request: PortalWindowFitRequest): Promise<PortalWindowFitResult>

  listProjectTree(path?: string): Promise<ProjectTreeListing>
  resolveProjectTreePath(path: string): Promise<string>
  openProjectTreePath(path: string): Promise<void>
  revealProjectTreePath(path: string): Promise<void>
  copyProjectTreePath(path: string): Promise<void>

  projectVirtualArd(request: ProjectVirtualArdRequest): Promise<VirtualArdState>
  appendSessionMessage(request: AppendSessionMessageRequest): Promise<SessionMessage>
  createVirtualArdHandoff(
    request: CreateVirtualArdHandoffRequest
  ): Promise<VirtualArdHandoff>
  getVirtualArdState(missionId?: string): Promise<VirtualArdState | null>

  sessionProviderStatus(): Promise<SessionProviderStatus>
  getSessionConversation(sessionId: string): Promise<SessionChatMessage[]>
  getSessionRetrieval(sessionId: string): Promise<RetrievalHit[]>

  sendSessionMessage(request: SessionAgentRequest): Promise<SessionAgentTurn>

  getProviderSettings(): Promise<ProviderSettingsState>
  saveProviderSettings(request: SaveProviderSettingsRequest): Promise<ProviderSettingsState>
  clearProviderApiKey(): Promise<ProviderSettingsState>

  getAiLaneSettings(): Promise<AiLaneSettingsState>
  saveAiLaneSettings(request: SaveAiLaneSettingsRequest): Promise<AiLaneSettingsState>
  clearAiLaneApiKey(laneId: AiLaneId): Promise<AiLaneSettingsState>
  browseLocalLlm(): Promise<string | null>
  browseSessionContextFile(): Promise<SessionContextAttachment | null>
  listAiLaneModels(request: ListAiLaneModelsRequest): Promise<string[]>

  storageStatus(): Promise<StorageStatus>
searchVcr(query?: string): Promise<VcrEntry[]>
upsertVcrEntry(request: UpsertVcrEntryRequest): Promise<VcrEntry>
searchVca(query?: string): Promise<VcaRecord[]>
appendVcaMemoryEvent(request: AppendVcaMemoryEventRequest): Promise<VcaRecord>
appendVcaWeightRevision(request: AppendVcaWeightRevisionRequest): Promise<VcaRecord>
getVcaMemoryClockState(): Promise<VcaMemoryClockState>
getVcaCompensation(sessionId: string, limit?: number): Promise<VcaCompensationPacket>
acknowledgeVcaCompensation(sessionId: string, throughRevision: number): Promise<VcaMemoryClockState>

getVcaCuratorState(): Promise<VcaCuratorState>
saveVcaCuratorSettings(request: SaveVcaCuratorSettingsRequest): Promise<VcaCuratorState>
runVcaCurator(request?: RunVcaCuratorRequest): Promise<VcaCuratorRunResult>

getVeraSessionThreadBindings(): Promise<VeraSessionThreadBinding[]>
updateVeraSessionThread(request: UpdateVeraSessionThreadRequest): Promise<VeraSessionThreadBinding>
getVcaInbox(): Promise<VcaInboxState>
enqueueVcaInbox(request: EnqueueVcaInboxRequest): Promise<VcaInboxEnqueueResult>

getVraDispatchState(): Promise<VraDispatchState>
registerVraWebviewSource(request: RegisterVraWebviewSourceRequest): Promise<void>
exportVraCard(cardId: string): Promise<string>
dispatchVraCard(cardId: string): Promise<VraDispatchCard>
removeVraCard(cardId: string): Promise<VraDispatchState>
acknowledgeVraEvidenceDelivery(request: VraEvidenceDeliveryAckRequest): Promise<VraEvidenceDeliveryAckResult>
getWorkstationSafety(): Promise<WorkstationSafetyObservation>
performWorkstationSafetyAction(request: WorkstationSafetyActionRequest): Promise<WorkstationSafetyActionResult>
getWorkstationServerProcessState(): Promise<WorkstationServerProcessState>
startWorkstationServer(): Promise<WorkstationServerProcessState>
readClipboardText(): Promise<string>
onVraDispatchChanged(listener: () => void): () => void

onControlCommand(listener: (serializedCommand: string) => void): void
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function requireString(
  value: unknown,
  field: string,
  maxLength: number
): string {
  if (typeof value !== 'string') {
    throw new Error(`PORTAL_CONTROL_${field}_NOT_STRING`)
  }

  const trimmed = value.trim()

  if (trimmed.length === 0) {
    throw new Error(`PORTAL_CONTROL_${field}_EMPTY`)
  }

  if (trimmed.length > maxLength) {
    throw new Error(`PORTAL_CONTROL_${field}_TOO_LONG`)
  }

  return trimmed
}

function requireSidebarTab(value: unknown): SidebarTab {
  if (value === 'PROJECT' || value === 'VCR' || value === 'VCA' || value === 'AI') {
    return value
  }

  throw new Error('PORTAL_CONTROL_INVALID_SIDEBAR_TAB')
}

export function normalizePortalControlCommand(
  value: unknown
): PortalControlCommand {
  if (!isRecord(value)) {
    throw new Error('PORTAL_CONTROL_COMMAND_NOT_OBJECT')
  }

  const type = requireString(value.type, 'TYPE', 64)

  switch (type) {
    case 'SIDEBAR_SWITCH':
      return {
        type,
        tab: requireSidebarTab(value.tab)
      }

    case 'SESSION_FOCUS':
    case 'SESSION_EXPAND':
      return {
        type,
        sessionId: requireString(
          value.sessionId,
          'SESSION_ID',
          128
        )
      }

    case 'VCR_OPEN':
      return {
        type,
        key: requireString(
          value.key,
          'VCR_KEY',
          240
        )
      }

    case 'VCA_SEARCH':
      return {
        type,
        query: requireString(
          value.query,
          'VCA_QUERY',
          4000
        )
      }

    case 'PROJECT_REVEAL':
      return {
        type,
        path: requireString(
          value.path,
          'PROJECT_PATH',
          4096
        )
      }

    default:
      throw new Error(
        `PORTAL_CONTROL_UNKNOWN_TYPE:${type}`
      )
  }
}

export function parsePortalControlCommandJson(
  serialized: string
): PortalControlCommand {
  if (typeof serialized !== 'string') {
    throw new Error(
      'PORTAL_CONTROL_SERIALIZED_COMMAND_NOT_STRING'
    )
  }

  return normalizePortalControlCommand(
    JSON.parse(serialized) as unknown
  )
}

export type SessionChatRole =
  | 'USER'
  | 'ASSISTANT'

export interface SessionChatMessage {
  id: string
  sessionId: string
  role: SessionChatRole
  body: string
  createdUtc: string
}

export type SessionContextScope =
  | 'SESSION'
  | 'PROJECT'
  | 'EVIDENCE'
  | 'PROJECT_EVIDENCE'

export interface SessionContextAttachment {
  name: string
  path: string
  content: string
}

export interface SessionAgentRequest {
  sessionId: string
  body: string
  contextScope?: SessionContextScope
  attachments?: SessionContextAttachment[]
}

export type RetrievalSource =
  | 'PROJECT'
  | 'EVIDENCE'

export interface RetrievalHit {
  source: RetrievalSource
  relativePath: string
  lineStart: number
  lineEnd: number
  snippet: string
  score: number
}

export type ProviderKind =
  | 'ollama'
  | 'lmstudio'
  | 'openai'
  | 'openai-compatible'
  | 'local'

export type AiLaneId =
  | 'lane-1'
  | 'lane-2'
  | 'lane-3'
  | 'lane-4'
  | 'lane-5'

/**
 * Canonical Session Portal architecture.
 *
 * Five lanes are Vera sessions. External/local models are optional assistants
 * attached underneath a Vera lane; they never replace Vera as the primary
 * session identity. An empty assistant configuration means NO ASSISTANT.
 * The primary transport target is the user's logged-in ChatGPT browser session.
 *
 * Legacy provider-backed chat remains temporarily available during migration
 * and MUST NOT be interpreted as the identity of Vera.
 */
export const VERA_SESSION_ARCHITECTURE = {
  primaryIdentity: 'VERA',
  laneCount: 5,
  emptyAssistantBehavior: 'NO_ASSISTANT',
  externalModelRole: 'AI_ASSISTANT_ONLY',
  primaryTransportTarget: 'CHATGPT_BROWSER_SESSION'
} as const

export const VERA_BROWSER_SESSION_CONTRACT = {
  transport: 'CHATGPT_WEB',
  entryUrl: 'https://chatgpt.com/',
  accountSession: 'PERSISTENT_SHARED',
  laneThreadState: 'INDEPENDENT_LAST_URL',
  cookieImportFromExternalBrowsers: 'NO',
  automatedDomExtraction: 'NO',
  providerFallbackForVera: 'NO'
} as const

export type VeraLaneId = AiLaneId

export interface ProviderSettingsState {
  provider: ProviderKind
  endpoint: string
  model: string
  hasApiKey: boolean
  apiKeySource: 'STORED' | 'ENV' | 'NONE'
  encryptionAvailable: boolean
  updatedUtc: string
}

export interface SaveProviderSettingsRequest {
  provider: ProviderKind
  endpoint: string
  model: string
  apiKey?: string
}

export interface AiLaneOverrideState {
  laneId: AiLaneId
  provider: ProviderKind
  endpoint: string
  model: string
  localModelPath: string
  hasApiKey: boolean
  apiKeySource: 'STORED' | 'ENV' | 'NONE'
  encryptionAvailable: boolean
  updatedUtc: string
}

export interface AiLaneState {
  laneId: AiLaneId
  label: string
  sessionId: string | null
  fallbackToVera: boolean
  override: AiLaneOverrideState | null
  resolvedProvider: ProviderKind
  resolvedEndpoint: string
  resolvedModel: string
  resolvedLocalModelPath: string
}

export interface AiLaneSettingsState {
  veraDefault: ProviderSettingsState
  lanes: AiLaneState[]
}

export interface SaveAiLaneSettingsRequest {
  laneId: AiLaneId
  provider?: ProviderKind | null
  endpoint?: string
  model?: string
  localModelPath?: string
  apiKey?: string
}

export interface ListAiLaneModelsRequest {
  laneId: AiLaneId
  provider?: ProviderKind | null
  endpoint?: string
  localModelPath?: string
}

export interface SessionAgentTurn {
  sessionId: string
  provider: ProviderKind
  model: string
  user: SessionChatMessage
  assistant: SessionChatMessage
  retrieval: RetrievalHit[]
}

export interface SessionProviderStatus {
  ready: boolean
  provider: ProviderKind
  providerLabel: string
  endpoint: string
  model: string | null
  configuredModel: string
  availableModels: string[]
  detail?: string
}

export interface VcrEntry {
  key: string
  title: string
  category: string
  status: string
  body: string
  revision: number
  createdUtc: string
  updatedUtc: string
}

export interface UpsertVcrEntryRequest {
  key: string
  title: string
  category: string
  status: string
  body: string
}

export type VcaMemoryActor = 'HUMAN' | 'VERA' | 'MUTUAL' | 'UNKNOWN' | 'SYSTEM'

export type VcaMemorySourceKind =
  | 'PORTAL_CHAT'
  | 'CHATGPT_BROWSER'
  | 'SESSION_CAPTURE'
  | 'ARD'
  | 'MANUAL'
  | 'IMPORT'

/**
 * Vertex-owned memory layer. This is intentionally separate from ChatGPT's
 * internal Memory. Human and Vera signals are peers; neither is privileged.
 * Weight history is append-only and age alone never reduces gravity.
 */
export const VCA_MEMORY_CONTRACT = {
  archiveTarget: 'ALL_CONVERSATION_EVENTS',
  weightHistory: 'APPEND_ONLY_REVISION',
  humanVeraPriority: 'PEER',
  automaticTimeDecay: 'NO',
  retrievalPrimaryOrder: 'MEMORY_GRAVITY',
  clockModel: 'CANONICAL_MEMORY_FRONTIER',
  transparentCompensation: 'EXPLICIT_ACK_FOUNDATION'
} as const

export type VcaInboxStatus = 'PENDING' | 'CURATED'
export type VcaCaptureKind = 'SESSION_BRIDGE' | 'MANUAL_BOUNDARY' | 'ARD' | 'IMPORT'

export const VCA_INBOX_CONTRACT = {
  purpose: 'SESSION_TO_VERTEX_MEMORY_BOUNDARY',
  duplicatePolicy: 'SHA256_FINGERPRINT_DEDUP',
  threadMapping: 'SESSION_ID_PLUS_CHATGPT_THREAD_URL',
  pendingMeaning: 'PROMOTED_TO_VCA_AWAITING_CURATOR',
  curatedMeaning: 'AI_CURATOR_WEIGHT_REVISION_APPENDED',
  browserContentExtraction: 'NO_DOM_SCRAPE',
  relationFoundation: 'APPEND_ONLY_MEMORY_RELATION'
} as const

export interface VeraSessionThreadBinding {
  sessionId: string
  sessionTitle: string
  threadUrl: string
  threadKey: string
  observedRevision: number
  compensatedRevision: number
  canonicalRevision: number
  lag: number
  updatedUtc: string
}

export interface UpdateVeraSessionThreadRequest {
  sessionId: string
  threadUrl: string
}

export interface EnqueueVcaInboxRequest {
  sessionId: string
  actor: VcaMemoryActor
  body: string
  captureKind: VcaCaptureKind
  threadUrl?: string
  sourceRef?: string
  createdUtc?: string
}

export interface VcaInboxItem {
  id: string
  fingerprint: string
  sessionId: string
  sessionTitle: string
  threadUrl: string
  threadKey: string
  actor: VcaMemoryActor
  body: string
  captureKind: VcaCaptureKind
  sourceRef: string | null
  status: VcaInboxStatus
  promotedEventId: string | null
  duplicateHits: number
  createdUtc: string
  processedUtc: string | null
}

export interface VcaInboxState {
  pendingCount: number
  curatedCount: number
  duplicateHits: number
  items: VcaInboxItem[]
}

export interface VcaInboxEnqueueResult {
  duplicate: boolean
  item: VcaInboxItem
  memory: VcaRecord | null
}

export type VraDispatchStatus = 'STAGED' | 'DISPATCHED' | 'ERROR'

export interface RegisterVraWebviewSourceRequest {
  sessionId: string
  webContentsId: number
}

export interface VraDispatchCard {
  id: string
  filename: string
  sourceSessionId: string | null
  sourceWebContentsId: number | null
  stagedPath: string
  sizeBytes: number
  sha256: string
  status: VraDispatchStatus
  capturedUtc: string
  dispatchedUtc: string | null
  worksPath: string | null
  error: string | null
}

export type WorkstationSafetyState = 'RUNNING' | 'DRAINING' | 'ESTOP_LATCHED' | 'RESET_READY'
export type WorkstationSafetyUiState = WorkstationSafetyState | 'UNKNOWN'
export type WorkstationSafetyAction = 'DRAIN' | 'ESTOP' | 'RESET' | 'RESUME'

export interface WorkstationSafetyTransition {
  timestamp: string
  requestId: string
  action: WorkstationSafetyAction
  previousState: WorkstationSafetyState
  newState: WorkstationSafetyState
  authority: 'HUMAN'
  reason: string
  activeJobs: number
  queuedJobs: number
  activeLanes: string[]
  locks: number
  recoveryResult: string
}

export interface WorkstationSafetyMetrics {
  activeJobs: number
  queuedJobs: number
  activeLanes: string[]
  locks: number
  recoveryResult: string
}

export interface WorkstationSafetyObservation {
  schema: 'vertex-workstation/durable-safety-state-1' | null
  online: boolean
  state: WorkstationSafetyUiState
  generation: number | null
  latched: boolean | null
  newWorkAllowed: boolean | null
  activeContinuationAllowed: boolean | null
  autoReset: false | null
  autoResume: false | null
  lastTransition: WorkstationSafetyTransition | null
  metrics: WorkstationSafetyMetrics | null
  executionPlane: 'AVAILABLE' | 'STOPPED' | 'UNKNOWN'
  observationPlane: 'ALIVE' | 'UNKNOWN'
  evidenceReturnPlane: 'ALIVE' | 'UNKNOWN'
  observedUtc: string
  lastError: string | null
}

export interface WorkstationSafetyActionRequest {
  action: WorkstationSafetyAction
  requestId: string
  reason: string
}

export interface WorkstationSafetyActionResult {
  action: WorkstationSafetyAction
  previousState: WorkstationSafetyState
  state: WorkstationSafetyState
  generation: number
  idempotent: boolean
  authority: 'HUMAN'
  observation: WorkstationSafetyObservation
}


export type WorkstationServerProcessPhase = 'OFFLINE' | 'STARTING' | 'ONLINE' | 'INCOMPATIBLE' | 'ERROR'

export type WorkstationServerRuntimeKind =
  | 'EMBEDDED'
  | 'SIBLING_BINARY'
  | 'SIBLING_CARGO'
  | 'EXTERNAL'
  | 'UNAVAILABLE'

export interface WorkstationServerProcessState {
  phase: WorkstationServerProcessPhase
  online: boolean
  serverReachable: boolean
  compatible: boolean
  managedByPortal: boolean
  pid: number | null
  runtime: WorkstationServerRuntimeKind
  bind: '127.0.0.1:47832'
  workstationRoot: string | null
  runtimeContract: string | null
  runtimeGeneration: string | null
  recoveryContract: string | null
  rootReleasePath: string | null
  rootReleaseReady: boolean
  startedUtc: string | null
  observedUtc: string
  lastError: string | null
}

export interface VraDispatchState {
  stagingRoot: string
  worksIncomingRoot: string
  cards: VraDispatchCard[]
  workstationOnline?: boolean
  workstationObservedUtc?: string | null
  workstationSafety?: WorkstationSafetyObservation | null
}

export interface VraEvidenceDeliveryAckRequest {
  cardId: string
  evidenceId: string
  artifactId: string
  returnedAt: string
}

export interface VraEvidenceDeliveryAckResult {
  acknowledged: boolean
  idempotent: boolean
  jobId: string
  evidenceId: string
  artifactId: string
  evidenceReturnState: string
  returnedAt: string
}

export const VRA_WORKS_DISPATCH_CONTRACT = {
  capture: 'CHATGPT_BROWSER_DOWNLOAD_VRA_ONLY',
  staging: 'PORTAL_OWNED',
  integrity: 'SHA256_BEFORE_DISPATCH',
  duplicatePolicy: 'SHA256_SUPPRESS',
  dispatchAuthority: 'HUMAN',
  worksBoundary: 'RECEIVING_BAY_ONLY',
  applyAuthority: 'HUMAN_APPLY',
  browserDomScrape: 'NO'
} as const

export interface VcaWeightDimensions {
  humanSignal: number
  veraSignal: number
  mutualSignal: number
  purposeRelation: number
  implementationLink: number
  recurrence: number
  novelty: number
  confidence: number
}

export interface AppendVcaMemoryEventRequest {
  sessionId: string
  actor: VcaMemoryActor
  body: string
  sourceKind: VcaMemorySourceKind
  sourceRef?: string
  createdUtc?: string
}

export interface AppendVcaWeightRevisionRequest extends VcaWeightDimensions {
  eventId: string
  curator: string
  rationale: string
}

export interface VcaRecord extends VcaWeightDimensions {
  id: string
  memoryRevision: number
  sessionId: string
  sessionTitle: string
  role: SessionChatRole
  actor: VcaMemoryActor
  body: string
  sourceKind: VcaMemorySourceKind
  sourceRef: string | null
  weightRevision: number
  memoryGravity: number
  curator: string
  rationale: string
  createdUtc: string
  weightedUtc: string
}

export interface VeraMemoryClock {
  sessionId: string
  sessionTitle: string
  observedRevision: number
  compensatedRevision: number
  effectiveRevision: number
  canonicalRevision: number
  lag: number
  updatedUtc: string
}

export interface VcaMemoryClockState {
  canonicalRevision: number
  sessions: VeraMemoryClock[]
}

export interface VcaCompensationPacket {
  sessionId: string
  fromRevision: number
  targetRevision: number
  lag: number
  memories: VcaRecord[]
}

export type VcaCuratorMode = 'PENDING' | 'REEVALUATE'

export const VCA_CURATOR_CONTRACT = {
  role: 'DEDICATED_AI_ASSISTANT',
  defaultLane: 'lane-4',
  emptyAssistantBehavior: 'NO_CURATOR_RUN',
  weightWritePolicy: 'APPEND_ONLY_REVISION',
  humanVeraPriority: 'PEER',
  automaticTimeDecay: 'NO',
  automaticRun: 'ON_NEW_MEMORY_WHEN_ENABLED',
  providerFallback: 'FORBIDDEN'
} as const

export interface VcaCuratorSettings {
  laneId: AiLaneId
  autoRun: boolean
  batchSize: number
}

export interface SaveVcaCuratorSettingsRequest {
  laneId: AiLaneId
  autoRun: boolean
  batchSize?: number
}

export interface VcaCuratorState {
  settings: VcaCuratorSettings
  configured: boolean
  ready: boolean
  provider: ProviderKind | null
  model: string | null
  pendingCount: number
  detail: string
}

export interface RunVcaCuratorRequest {
  mode?: VcaCuratorMode
  limit?: number
}

export interface VcaCuratorRunResult {
  mode: VcaCuratorMode
  laneId: AiLaneId
  configured: boolean
  provider: ProviderKind | null
  model: string | null
  candidateCount: number
  processed: number
  skipped: number
  failures: string[]
  startedUtc: string
  finishedUtc: string
}

export interface StorageStatus {
  sqliteConnected: boolean
  vcrReady: boolean
  vcaReady: boolean
  vcrCount: number
  vcaCount: number
}

//
// Compatibility restoration from VERIFIED workspace-tree-active-neon-000039.
// Presentation / Final Wiring B contracts must not erase the existing Project Tree API.
//
export type ProjectTreeNodeKind = 'DIRECTORY' | 'FILE' | 'SYMLINK' | 'OTHER'

export interface ProjectTreeNode {
  name: string
  path: string
  relativePath: string
  kind: ProjectTreeNodeKind
  expandable: boolean
}

export interface ProjectTreeBreadcrumb {
  name: string
  path: string
}

export interface ProjectTreeListing {
  rootPath: string
  workspaceRootPath: string
  parentPath: string | null
  breadcrumbs: ProjectTreeBreadcrumb[]
  directory: ProjectTreeNode
  children: ProjectTreeNode[]
}

export const PROJECT_TREE_CONTRACT = {
  source: 'REAL_FILESYSTEM',
  scope: 'VERTEX_WORKSPACE_NAVIGATION',
  ordering: 'DIRECTORY_FIRST_CASE_INSENSITIVE',
  expansion: 'LAZY',
  symbolicLinkTraversal: 'NO',
  writes: 'NO',
  selectionPersistence: 'LOCAL_UI_STATE'
} as const

