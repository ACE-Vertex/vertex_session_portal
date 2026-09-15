import type {
  AiLaneId,
  AiLaneSettingsState,
  ProviderKind,
  ProjectTreeBreadcrumb,
  ProjectTreeListing,
  ProjectTreeNode,
  SidebarTab,
  VcaCuratorState,
  VcaInboxState,
  VcaMemoryActor,
  VcaMemoryClockState,
  VeraSessionThreadBinding,
  VcaRecord,
  VcrEntry
} from '../../../../shared/contracts'
import { escapeHtml } from '../../shared/escape'
import styles from './Explorer.css?inline'

const copy: Record<SidebarTab, { eyebrow: string; title: string; body: string }> = {
  PROJECT: { eyebrow: 'WORKSTATION', title: 'PROJECT EXPLORER', body: 'Local project / files / dependency surfaces.' },
  VCR: { eyebrow: 'CANONICAL', title: 'VERTEX CANONICAL REGISTRY', body: 'SQLite-backed canonical definitions, history and status.' },
  VCA: { eyebrow: 'MEMORY', title: 'VERTEX CONVERSATION ARCHIVE', body: 'Vertex-owned weighted experience archive with Memory Gravity and Vera session clocks.' },
  AI: { eyebrow: 'VERA', title: 'VERA SESSION MATRIX', body: 'Five Vera sessions. Each Vera can carry one optional AI Assistant.' }
}

const providers: Array<{ value: ProviderKind; label: string }> = [
  { value: 'ollama', label: 'Ollama' },
  { value: 'lmstudio', label: 'LM Studio' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'openai-compatible', label: 'OpenAI Compatible' },
  { value: 'local', label: 'Local Raw LLM' }
]

const providerEndpoints: Record<ProviderKind, string> = {
  ollama: 'http://127.0.0.1:11434',
  lmstudio: 'http://127.0.0.1:1234',
  openai: 'https://api.openai.com',
  'openai-compatible': 'http://127.0.0.1:8000',
  local: ''
}

function providerName(provider: ProviderKind): string {
  return providers.find(item => item.value === provider)?.label ?? provider
}

function basename(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() ?? path
}

export class VertexExplorer extends HTMLElement {
  private activeTab: SidebarTab = 'PROJECT'
  private detail = ''
  private aiSettings: AiLaneSettingsState | null = null
  private selectedLaneId: AiLaneId = 'lane-1'
  private modelOptions: string[] = []
  private activeMainLanes = 3
  private vcr: VcrEntry[] = []
  private vca: VcaRecord[] = []
  private vcaClock: VcaMemoryClockState | null = null
  private vcaCurator: VcaCuratorState | null = null
  private vcaInbox: VcaInboxState | null = null
  private vcaThreads: VeraSessionThreadBinding[] = []
  private projectRoot: ProjectTreeNode | null = null
  private projectRootPath = ''
  private projectCanonicalRootPath = ''
  private projectParentPath: string | null = null
  private projectBreadcrumbs: ProjectTreeBreadcrumb[] = []
  private projectChildren = new Map<string, ProjectTreeNode[]>()
  private projectParents = new Map<string, string>()
  private projectExpanded = new Set<string>()
  private projectLoaded = new Set<string>()
  private projectLoadingPaths = new Set<string>()
  private projectSelectedPath = ''
  private projectContextMenu: { x: number; y: number; path: string } | null = null
  private searchQuery = ''
  private loading = false
  private vcrEditorOpen = false
  private vcrEditorEntry: VcrEntry | null = null
  private vcrDraftKey = ''
  private vcrEditorClosing = false

  private readonly onWindowKeydown = (event: KeyboardEvent): void => {
    if (event.key === 'Escape' && this.vcrEditorOpen) {
      event.preventDefault()
      this.closeVcrEditor()
      return
    }
    if (event.key === 'Escape' && this.projectContextMenu) {
      event.preventDefault()
      this.projectContextMenu = null
      this.render()
    }
  }

  constructor() {
    super()
    this.attachShadow({ mode: 'open' })
  }

  connectedCallback(): void {
    window.addEventListener('keydown', this.onWindowKeydown)
    this.render()
    void this.loadActiveTab()
  }

  disconnectedCallback(): void {
    window.removeEventListener('keydown', this.onWindowKeydown)
  }

  setTab(tab: SidebarTab): void {
    this.activeTab = tab
    this.detail = ''
    this.searchQuery = ''
    this.render()
    void this.loadActiveTab()
  }

  showVcrEntry(key: string): void {
    this.activeTab = 'VCR'
    this.searchQuery = key
    this.detail = `Open canonical: ${key}`
    this.render()
    void this.loadVcr(key)
  }

  showVcaSearch(query: string): void {
    this.activeTab = 'VCA'
    this.searchQuery = query
    this.detail = `Search conversation: ${query}`
    this.render()
    void this.loadVca(query)
  }

  revealProject(path: string): void {
    this.activeTab = 'PROJECT'
    this.detail = `Reveal: ${path}`
    this.render()
    void this.revealProjectNode(path)
  }

  private async loadActiveTab(): Promise<void> {
    if (this.activeTab === 'PROJECT') await this.loadProjectTree()
    if (this.activeTab === 'AI') await this.loadAiLaneSettings()
    if (this.activeTab === 'VCR') await this.loadVcr(this.searchQuery)
    if (this.activeTab === 'VCA') await this.loadVca(this.searchQuery)
  }

  private async loadAiLaneSettings(): Promise<void> {
    this.loading = true
    this.render()
    try {
      const [settings, bootstrap] = await Promise.all([
        window.vertexPortal.getAiLaneSettings(),
        window.vertexPortal.bootstrap()
      ])
      this.aiSettings = settings
      this.activeMainLanes = bootstrap.sessions.filter(session => session.kind === 'MAIN' && session.active).length
      const selected = this.aiSettings.lanes.find(item => item.laneId === this.selectedLaneId)
      if (!selected) this.selectedLaneId = 'lane-1'
    } catch (error: unknown) {
      this.detail = error instanceof Error ? error.message : String(error)
    } finally {
      this.loading = false
      this.render()
    }
  }

  private async loadVcr(query: string): Promise<void> {
    this.loading = true
    this.render()
    try {
      this.vcr = await window.vertexPortal.searchVcr(query)
    } catch (error: unknown) {
      this.vcr = []
      this.detail = error instanceof Error ? error.message : String(error)
    } finally {
      this.loading = false
      this.render()
    }
  }

  private async loadVca(query: string): Promise<void> {
    this.loading = true
    this.render()
    try {
      const [records, clock, curator, inbox, threads] = await Promise.all([
        window.vertexPortal.searchVca(query),
        window.vertexPortal.getVcaMemoryClockState(),
        window.vertexPortal.getVcaCuratorState(),
        window.vertexPortal.getVcaInbox(),
        window.vertexPortal.getVeraSessionThreadBindings()
      ])
      this.vca = records
      this.vcaClock = clock
      this.vcaCurator = curator
      this.vcaInbox = inbox
      this.vcaThreads = threads
    } catch (error: unknown) {
      this.vca = []
      this.vcaClock = null
      this.vcaCurator = null
      this.vcaInbox = null
      this.vcaThreads = []
      this.detail = error instanceof Error ? error.message : String(error)
    } finally {
      this.loading = false
      this.render()
    }
  }

  private projectTreeStorageKey(): string {
    return 'vertex-session-portal:project-tree-ui:000039'
  }

  private projectNavigationStorageKey(): string {
    return 'vertex-session-portal:project-tree-root:000039'
  }

  private restoreProjectNavigationRoot(): string {
    try {
      return localStorage.getItem(this.projectNavigationStorageKey()) ?? ''
    } catch {
      return ''
    }
  }

  private persistProjectNavigationRoot(): void {
    if (!this.projectRootPath) return
    try {
      localStorage.setItem(this.projectNavigationStorageKey(), this.projectRootPath)
    } catch {
      // Navigation persistence is optional.
    }
  }

  private restoreProjectTreeUi(rootPath: string): { expanded: string[]; selected: string } {
    try {
      const raw = localStorage.getItem(this.projectTreeStorageKey())
      if (!raw) return { expanded: [], selected: '' }
      const parsed = JSON.parse(raw) as { rootPath?: string; expanded?: string[]; selected?: string }
      if (parsed.rootPath !== rootPath) return { expanded: [], selected: '' }
      return {
        expanded: Array.isArray(parsed.expanded) ? parsed.expanded.filter(item => typeof item === 'string') : [],
        selected: typeof parsed.selected === 'string' ? parsed.selected : ''
      }
    } catch {
      return { expanded: [], selected: '' }
    }
  }

  private persistProjectTreeUi(): void {
    if (!this.projectRootPath) return
    try {
      localStorage.setItem(this.projectTreeStorageKey(), JSON.stringify({
        rootPath: this.projectRootPath,
        expanded: Array.from(this.projectExpanded),
        selected: this.projectSelectedPath
      }))
    } catch {
      // UI persistence failure must never break project navigation.
    }
  }

  private absorbProjectListing(listing: ProjectTreeListing): void {
    this.projectChildren.set(listing.directory.path, listing.children)
    this.projectLoaded.add(listing.directory.path)
    for (const child of listing.children) this.projectParents.set(child.path, listing.directory.path)
  }

  private applyProjectRootListing(listing: ProjectTreeListing): void {
    this.projectRoot = listing.directory
    this.projectRootPath = listing.directory.path
    this.projectCanonicalRootPath = listing.rootPath
    this.projectParentPath = listing.parentPath
    this.projectBreadcrumbs = listing.breadcrumbs
    this.absorbProjectListing(listing)
  }

  private async loadProjectTree(force = false): Promise<void> {
    if (this.projectRoot && !force) {
      this.render()
      return
    }

    this.loading = true
    this.render()
    try {
      const preferredRoot = this.restoreProjectNavigationRoot()
      let listing: ProjectTreeListing
      try {
        listing = await window.vertexPortal.listProjectTree(preferredRoot || undefined)
      } catch {
        listing = await window.vertexPortal.listProjectTree()
      }

      this.projectChildren.clear()
      this.projectParents.clear()
      this.projectLoaded.clear()
      this.projectLoadingPaths.clear()
      this.applyProjectRootListing(listing)

      const persisted = this.restoreProjectTreeUi(this.projectRootPath)
      this.projectExpanded = new Set([this.projectRootPath, ...persisted.expanded])
      this.projectSelectedPath = persisted.selected

      const restore = persisted.expanded
        .filter(path => path !== this.projectRootPath)
        .sort((left, right) => left.split(/[\\/]/).length - right.split(/[\\/]/).length)
        .slice(0, 120)

      for (const path of restore) {
        try {
          this.absorbProjectListing(await window.vertexPortal.listProjectTree(path))
        } catch {
          this.projectExpanded.delete(path)
        }
      }
      this.persistProjectNavigationRoot()
      this.persistProjectTreeUi()
    } catch (error: unknown) {
      this.projectRoot = null
      this.projectRootPath = ''
      this.projectCanonicalRootPath = ''
      this.projectParentPath = null
      this.projectBreadcrumbs = []
      this.projectChildren.clear()
      this.detail = error instanceof Error ? error.message : String(error)
    } finally {
      this.loading = false
      this.render()
    }
  }

  private async navigateProjectRoot(path: string): Promise<void> {
    this.loading = true
    this.projectContextMenu = null
    this.render()
    try {
      const listing = await window.vertexPortal.listProjectTree(path)
      this.projectChildren.clear()
      this.projectParents.clear()
      this.projectLoaded.clear()
      this.projectLoadingPaths.clear()
      this.applyProjectRootListing(listing)
      this.projectExpanded = new Set([this.projectRootPath])
      this.projectSelectedPath = this.projectRootPath
      this.detail = `Tree root: ${listing.directory.path}`
      this.persistProjectNavigationRoot()
      this.persistProjectTreeUi()
    } catch (error: unknown) {
      this.detail = error instanceof Error ? error.message : String(error)
    } finally {
      this.loading = false
      this.render()
    }
  }

  private async toggleProjectDirectory(path: string): Promise<void> {
    if (this.projectExpanded.has(path)) {
      this.projectExpanded.delete(path)
      this.persistProjectTreeUi()
      this.render()
      return
    }

    if (!this.projectLoaded.has(path)) {
      this.projectLoadingPaths.add(path)
      this.render()
      try {
        this.absorbProjectListing(await window.vertexPortal.listProjectTree(path))
      } catch (error: unknown) {
        this.detail = error instanceof Error ? error.message : String(error)
        this.projectLoadingPaths.delete(path)
        this.render()
        return
      }
      this.projectLoadingPaths.delete(path)
    }

    this.projectExpanded.add(path)
    this.persistProjectTreeUi()
    this.render()
  }

  private projectNodeByPath(path: string): ProjectTreeNode | null {
    if (this.projectRoot?.path === path) return this.projectRoot
    for (const children of this.projectChildren.values()) {
      const found = children.find(node => node.path === path)
      if (found) return found
    }
    return null
  }

  private async refreshProjectDirectory(path?: string): Promise<void> {
    if (!this.projectRoot) return
    let target = path || this.projectSelectedPath || this.projectRoot.path
    const selected = this.projectNodeByPath(target)
    if (selected && selected.kind !== 'DIRECTORY') target = this.projectParents.get(target) || this.projectRoot.path

    this.projectLoadingPaths.add(target)
    this.render()
    try {
      const listing = await window.vertexPortal.listProjectTree(target)
      this.absorbProjectListing(listing)
      if (target === this.projectRootPath) {
        this.projectParentPath = listing.parentPath
        this.projectBreadcrumbs = listing.breadcrumbs
      }
      this.detail = `Refreshed: ${listing.directory.relativePath || listing.directory.name}`
    } catch (error: unknown) {
      this.detail = error instanceof Error ? error.message : String(error)
    } finally {
      this.projectLoadingPaths.delete(target)
      this.persistProjectTreeUi()
      this.render()
    }
  }

  private async revealProjectNode(path: string): Promise<void> {
    try {
      if (!this.projectRoot) await this.loadProjectTree()
      if (!this.projectRoot) return
      const target = await window.vertexPortal.resolveProjectTreePath(path)

      if (!target.toLowerCase().startsWith(this.projectRootPath.toLowerCase())) {
        await this.navigateProjectRoot(target)
        return
      }

      const root = this.projectRoot.path
      const separator = root.includes('\\') ? '\\' : '/'
      const relativeTarget = target.slice(root.length).replace(/^[\\/]+/, '')
      const segments = relativeTarget ? relativeTarget.split(/[\\/]+/).filter(Boolean) : []
      let current = root
      this.projectExpanded.add(root)

      for (let index = 0; index < Math.max(0, segments.length - 1); index += 1) {
        current = `${current}${separator}${segments[index]}`
        if (!this.projectLoaded.has(current)) {
          try {
            this.absorbProjectListing(await window.vertexPortal.listProjectTree(current))
          } catch {
            break
          }
        }
        this.projectExpanded.add(current)
      }

      this.projectSelectedPath = target
      this.persistProjectTreeUi()
      this.render()
      queueMicrotask(() => {
        const row = Array.from(this.shadowRoot?.querySelectorAll<HTMLElement>('.treeRow[data-path]') ?? [])
          .find(item => item.dataset.path === target)
        row?.scrollIntoView({ block: 'nearest' })
      })
    } catch (error: unknown) {
      this.detail = error instanceof Error ? error.message : String(error)
      this.render()
    }
  }

  private selectProjectPath(path: string): void {
    this.projectSelectedPath = path
    this.persistProjectTreeUi()
    for (const row of this.shadowRoot?.querySelectorAll<HTMLElement>('.treeRow') ?? []) {
      row.dataset.selected = String(row.dataset.path === path)
    }
  }

  private visibleProjectRows(): Array<{ node: ProjectTreeNode; depth: number; root: boolean }> {
    if (!this.projectRoot) return []
    const rows: Array<{ node: ProjectTreeNode; depth: number; root: boolean }> = []
    const visit = (node: ProjectTreeNode, depth: number, root = false): void => {
      rows.push({ node, depth, root })
      if (node.kind !== 'DIRECTORY' || !this.projectExpanded.has(node.path)) return
      for (const child of this.projectChildren.get(node.path) ?? []) visit(child, depth + 1)
    }
    visit(this.projectRoot, 0, true)
    return rows
  }

  private projectTree(): string {
    if (!this.projectRoot) {
      return `<div class="placeholder compact"><div class="pulse"></div><p class="copy">${this.loading ? 'Reading workspace filesystem…' : 'Workspace filesystem unavailable.'}</p></div>`
    }

    const rows = this.visibleProjectRows().map(({ node, depth, root }) => {
      const loaded = this.projectLoaded.has(node.path)
      const loading = this.projectLoadingPaths.has(node.path)
      const children = this.projectChildren.get(node.path) ?? []
      const expanded = this.projectExpanded.has(node.path)
      const toggle = node.kind !== 'DIRECTORY'
        ? '·'
        : loading
          ? '…'
          : loaded && children.length === 0
            ? '·'
            : expanded ? '⌄' : '›'
      const icon = node.kind === 'DIRECTORY' ? (root ? '◇' : '▱') : node.kind === 'SYMLINK' ? '↗' : node.kind === 'FILE' ? '◆' : '◇'
      const label = node.relativePath || node.name
      return `
        <div class="treeRow${root ? ' root' : ''}" role="treeitem" tabindex="0"
          style="--tree-depth:${depth}"
          data-path="${escapeHtml(node.path)}"
          data-kind="${node.kind}"
          data-canonical="${node.path === this.projectCanonicalRootPath}"
          data-selected="${node.path === this.projectSelectedPath}">
          <span class="treeIndent" aria-hidden="true"></span>
          <button class="treeToggle" type="button" data-tree-toggle="${escapeHtml(node.path)}" aria-label="Toggle ${escapeHtml(node.name)}" ${node.kind !== 'DIRECTORY' ? 'disabled' : ''}>${toggle}</button>
          <span class="treeIcon" data-kind="${node.kind}" aria-hidden="true">${icon}</span>
          <span class="treeName" title="${escapeHtml(label)}">${escapeHtml(node.name)}</span>
        </div>
      `
    }).join('')

    const menuNode = this.projectContextMenu ? this.projectNodeByPath(this.projectContextMenu.path) : null
    const menu = this.projectContextMenu && menuNode ? `
      <div class="treeContextMenu" role="menu" style="left:${this.projectContextMenu.x}px;top:${this.projectContextMenu.y}px" data-tree-context>
        ${menuNode.kind === 'DIRECTORY' ? '<button type="button" data-tree-menu="root">OPEN AS TREE ROOT</button>' : ''}
        <button type="button" data-tree-menu="open">${menuNode.kind === 'DIRECTORY' ? 'OPEN IN EXPLORER' : 'OPEN'}</button>
        <button type="button" data-tree-menu="reveal">REVEAL IN EXPLORER</button>
        <button type="button" data-tree-menu="copy">COPY PATH</button>
        <button type="button" data-tree-menu="refresh">REFRESH</button>
      </div>
    ` : ''

    const breadcrumbs = this.projectBreadcrumbs.map((crumb, index) => `
      <button type="button" data-project-breadcrumb="${escapeHtml(crumb.path)}" title="${escapeHtml(crumb.path)}">${escapeHtml(crumb.name)}</button>${index < this.projectBreadcrumbs.length - 1 ? '<span>›</span>' : ''}
    `).join('')

    return `
      <div class="projectTreeToolbar">
        <div class="projectTreeToolbarTop">
          <div class="projectTreeLocation"><span>WORKSPACE FILESYSTEM</span><strong title="${escapeHtml(this.projectRoot.path)}">${escapeHtml(this.projectRoot.name)}</strong></div>
          <div class="projectTreeActions">
            <button type="button" data-action="project-up" title="Parent folder" ${this.projectParentPath ? '' : 'disabled'}>↑</button>
            <button type="button" data-action="project-home" title="Canonical project root">⌂</button>
            <button type="button" data-action="project-refresh" title="Refresh tree">↻</button>
          </div>
        </div>
        <div class="projectBreadcrumbs" aria-label="Workspace path">${breadcrumbs}</div>
      </div>
      <div class="tree" role="tree" aria-label="Workspace filesystem tree">${rows}</div>
      ${menu}
    `
  }

  private providerPanel(): string {
    const settings = this.aiSettings
    if (!settings) {
      return `<div class="placeholder"><div class="pulse"></div><p class="copy">${this.loading ? 'Loading Vera session settings…' : 'Vera session settings unavailable.'}</p></div>`
    }

    const lane = settings.lanes.find(item => item.laneId === this.selectedLaneId) ?? settings.lanes[0]
    const override = lane.override
    const provider = override?.provider ?? null
    const endpoint = override?.endpoint ?? ''
    const model = override?.model ?? ''
    const localModelPath = override?.localModelPath ?? ''
    const disabled = provider === null
    const local = provider === 'local'
    const currentModelOptions = Array.from(new Set([model, ...this.modelOptions].filter(Boolean)))
    const laneNumber = lane.laneId.replace('lane-', '').padStart(2, '0')
    const laneIndex = settings.lanes.findIndex(item => item.laneId === lane.laneId)
    const sessionActive = laneIndex >= 0 && laneIndex < this.activeMainLanes
    const assistantLabel = override
      ? `${providerName(override.provider)} · ${override.model || basename(override.localModelPath) || 'AUTO'}`
      : 'NONE'

    return `
      <section class="aiPanel">
        <div class="veraPrimary">
          <div>
            <span class="fallbackEyebrow">PRIMARY IDENTITY</span>
            <strong>VERA ${laneNumber}</strong>
          </div>
          <span>${sessionActive ? 'ACTIVE' : 'STANDBY'} · CHATGPT BROWSER TARGET</span>
        </div>

        <div class="laneRail" role="tablist" aria-label="Vera sessions">
          ${settings.lanes.map((item, index) => {
            const active = index < this.activeMainLanes
            return `
              <button class="laneButton" type="button" data-lane="${item.laneId}" data-active="${item.laneId === lane.laneId}" data-session-active="${active}">
                <strong>${item.label.replace('LANE ', '')}</strong>
                <span>${active ? 'VERA' : 'STANDBY'}</span>
              </button>
            `
          }).join('')}
        </div>
        <div class="laneCapacity">
          <span>ACTIVE VERA SESSIONS · ${this.activeMainLanes}/5</span>
          <button class="addLaneButton" type="button" data-action="add-lane" ${this.activeMainLanes >= 5 ? 'disabled' : ''}>⊕ ADD VERA</button>
        </div>

        <div class="laneIdentity">
          <div>
            <span class="fieldLabel">VERA SESSION ${laneNumber}</span>
            <strong>${sessionActive ? 'PRIMARY / ACTIVE' : 'PRIMARY / STANDBY'}</strong>
          </div>
          <span>${lane.sessionId ? escapeHtml(lane.sessionId) : 'RESERVE'}</span>
        </div>

        <div class="assistantHeader">
          <div>
            <span class="assistantEyebrow">DEDICATED AI ASSISTANT</span>
            <strong>${escapeHtml(assistantLabel)}</strong>
          </div>
          <span>${override ? 'ATTACHED' : 'OPTIONAL'}</span>
        </div>

        <form class="settingsForm">
          <label class="fieldLabel" for="provider">ASSISTANT PROVIDER</label>
          <select id="provider" name="provider" class="fieldInput">
            <option value="" ${provider === null ? 'selected' : ''}>No Assistant</option>
            ${providers.map(item => `<option value="${item.value}" ${item.value === provider ? 'selected' : ''}>${item.label}</option>`).join('')}
          </select>

          <div class="conditionalField" data-local-field data-visible="${local}">
            <label class="fieldLabel" for="localModelPath">LOCAL ASSISTANT SOURCE</label>
            <div class="fieldWithButton">
              <input id="localModelPath" name="localModelPath" class="fieldInput" value="${escapeHtml(localModelPath)}" placeholder="Select .gguf / raw model…" readonly />
              <button class="inlineButton" type="button" data-action="browse-local">REFER</button>
            </div>
          </div>

          <label class="fieldLabel" for="endpoint">ENDPOINT</label>
          <input id="endpoint" name="endpoint" class="fieldInput" value="${escapeHtml(endpoint)}" autocomplete="off" ${disabled || local ? 'disabled' : ''} placeholder="${local ? 'Not used for raw local assistant' : 'Assistant provider endpoint'}" />

          <label class="fieldLabel" for="model">SELECTED LLM</label>
          <div class="fieldWithButton">
            <input id="model" name="model" class="fieldInput" value="${escapeHtml(model)}" list="availableModels" autocomplete="off" ${disabled ? 'disabled' : ''} placeholder="${local ? 'Derived from selected local file' : 'Select or type assistant model'}" />
            <button class="inlineButton" type="button" data-action="refresh-models" ${disabled ? 'disabled' : ''}>LIST</button>
          </div>
          <datalist id="availableModels">
            ${currentModelOptions.map(item => `<option value="${escapeHtml(item)}"></option>`).join('')}
          </datalist>

          <label class="fieldLabel" for="apiKey">API KEY</label>
          <input id="apiKey" name="apiKey" class="fieldInput" type="password" placeholder="${override?.hasApiKey ? '••••••••  stored / env' : disabled ? 'No assistant credential required' : local ? 'Not required for raw local assistant' : 'Enter assistant API key if required'}" autocomplete="new-password" ${disabled || local ? 'disabled' : ''} />

          <div class="settingMeta">
            <span>PRIMARY · VERA SESSION ${laneNumber}</span>
            <span>ASSISTANT ROUTE · ${override ? 'ASSISTANT ONLY' : 'NO ASSISTANT'}</span>
            <span>KEY · ${override?.apiKeySource ?? 'NONE'}</span>
            <span>OS ENCRYPTION · ${(override?.encryptionAvailable ?? settings.veraDefault.encryptionAvailable) ? 'READY' : 'UNAVAILABLE'}</span>
          </div>

          <div class="settingActions">
            <button class="primaryButton" type="submit">SAVE ASSISTANT</button>
            <button class="secondaryButton" type="button" data-action="clear-key" ${!override?.hasApiKey ? 'disabled' : ''}>CLEAR KEY</button>
          </div>
          <button class="veraButton" type="button" data-action="remove-assistant" ${!override ? 'disabled' : ''}>REMOVE AI ASSISTANT</button>
        </form>
      </section>
    `
  }

  private nextVcrKey(): string {
    const now = new Date()
    const pad = (value: number, length = 2): string => String(value).padStart(length, '0')
    return `VCR-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}-${pad(now.getMilliseconds(), 3)}`
  }

  private openVcrEditor(entry: VcrEntry | null): void {
    this.vcrEditorEntry = entry
    this.vcrDraftKey = entry?.key ?? this.nextVcrKey()
    this.vcrEditorOpen = true
    this.vcrEditorClosing = false
    this.render()
    window.setTimeout(() => {
      const target = this.shadowRoot?.querySelector<HTMLInputElement>(
        entry ? 'input[name="title"]' : 'input[name="key"]'
      )
      target?.focus()
      target?.select()
    }, 0)
  }

  private closeVcrEditor(): void {
    if (!this.vcrEditorOpen || this.vcrEditorClosing) return
    const backdrop = this.shadowRoot?.querySelector<HTMLElement>('.vcrModalBackdrop')
    const panel = this.shadowRoot?.querySelector<HTMLElement>('.vcrModal')
    if (!backdrop || !panel) {
      this.vcrEditorOpen = false
      this.vcrEditorEntry = null
      this.vcrEditorClosing = false
      this.render()
      return
    }

    this.vcrEditorClosing = true
    backdrop.dataset.closing = 'true'
    panel.dataset.closing = 'true'
    window.setTimeout(() => {
      this.vcrEditorOpen = false
      this.vcrEditorEntry = null
      this.vcrDraftKey = ''
      this.vcrEditorClosing = false
      this.render()
    }, 150)
  }

  private vcrEditorModal(): string {
    if (!this.vcrEditorOpen) return ''

    const entry = this.vcrEditorEntry
    const editing = entry !== null
    const title = entry?.title ?? ''
    const category = entry?.category ?? 'GENERAL'
    const status = entry?.status ?? 'ACTIVE'
    const body = entry?.body ?? ''

    return `
      <div class="vcrModalBackdrop" data-vcr-modal-backdrop data-closing="${this.vcrEditorClosing}">
        <section class="vcrModal" role="dialog" aria-modal="true" aria-labelledby="vcrEditorTitle" data-closing="${this.vcrEditorClosing}">
          <header class="vcrModalHeader">
            <div>
              <span class="vcrModalEyebrow">${editing ? `REVISION ${entry.revision}` : 'NEW CANONICAL CARD'}</span>
              <h3 id="vcrEditorTitle">${editing ? 'VCR CARD' : 'ADD VCR'}</h3>
            </div>
            <button class="vcrCloseButton" type="button" data-action="close-vcr" aria-label="Close VCR editor" title="Close">×</button>
          </header>

          ${editing ? `
            <div class="vcrRevisionMeta">
              <span>CREATED · ${escapeHtml(entry.createdUtc)}</span>
              <span>UPDATED · ${escapeHtml(entry.updatedUtc)}</span>
              <span>SAVE APPENDS · r${entry.revision + 1}</span>
            </div>
          ` : `
            <div class="vcrRevisionMeta">
              <span>NEW CARD</span>
              <span>SAVE CREATES · r1</span>
              <span>SQLITE / APPEND-ONLY</span>
            </div>
          `}

          <form class="vcrEditorForm">
            <label class="vcrEditorField">
              <span>CANONICAL KEY</span>
              <input name="key" class="vcrModalInput" value="${escapeHtml(this.vcrDraftKey)}" maxlength="240" ${editing ? 'readonly' : ''} required />
            </label>

            <label class="vcrEditorField">
              <span>TITLE</span>
              <input name="title" class="vcrModalInput" value="${escapeHtml(title)}" maxlength="500" placeholder="Canonical title" required />
            </label>

            <div class="vcrEditorGrid">
              <label class="vcrEditorField">
                <span>CATEGORY</span>
                <input name="category" class="vcrModalInput" value="${escapeHtml(category)}" maxlength="120" placeholder="GENERAL" required />
              </label>
              <label class="vcrEditorField">
                <span>STATUS</span>
                <input name="status" class="vcrModalInput" value="${escapeHtml(status)}" maxlength="80" placeholder="ACTIVE" required />
              </label>
            </div>

            <label class="vcrEditorField">
              <span>CONTENT</span>
              <textarea name="body" class="vcrModalTextarea" maxlength="100000" placeholder="Canonical content…" required>${escapeHtml(body)}</textarea>
            </label>

            <div class="vcrModalError" role="status" aria-live="polite"></div>

            <footer class="vcrModalFooter">
              <div class="vcrSaveHint">${editing ? 'Existing revision is preserved. Saving creates a new revision.' : 'A new canonical card will be written to the local VCR store.'}</div>
              <div class="vcrModalActions">
                <button class="vcrSecondaryButton" type="button" data-action="close-vcr">CLOSE</button>
                <button class="vcrSaveButton" type="submit">${editing ? 'SAVE NEW REVISION' : 'CREATE VCR'}</button>
              </div>
            </footer>
          </form>
        </section>
      </div>
    `
  }

  private vcaInboxPanel(): string {
    const inbox = this.vcaInbox
    const threads = this.vcaThreads
    const recent = inbox?.items.slice(0, 5) ?? []
    const defaultSession = threads[0]?.sessionId ?? 'vera-01'

    return `
      <section class="vcaInboxPanel">
        <div class="vcaInboxHead">
          <div>
            <span class="assistantEyebrow">VCA MEMORY INBOX</span>
            <strong>SESSION → VERTEX MEMORY BOUNDARY</strong>
          </div>
          <span class="inboxStatus">PENDING ${inbox?.pendingCount ?? '—'}</span>
        </div>
        <div class="vcaInboxStats">
          <span>CURATED ${inbox?.curatedCount ?? '—'}</span>
          <span>DEDUPE HITS ${inbox?.duplicateHits ?? '—'}</span>
          <span>THREADS ${threads.length || '—'}</span>
        </div>
        <form class="vcaInboxForm">
          <label class="fieldLabel" for="vcaInboxSession">VERA SESSION</label>
          <select id="vcaInboxSession" name="sessionId" class="fieldInput">
            ${(threads.length ? threads : [{ sessionId: defaultSession, sessionTitle: 'Vera 01', threadKey: '/', lag: 0 } as VeraSessionThreadBinding]).map(thread => `<option value="${escapeHtml(thread.sessionId)}">${escapeHtml(thread.sessionTitle)} · ${escapeHtml(thread.threadKey)} · ${thread.lag === 0 ? 'SYNC' : `Δ${thread.lag}`}</option>`).join('')}
          </select>
          <label class="fieldLabel" for="vcaInboxActor">MEMORY ACTOR</label>
          <select id="vcaInboxActor" name="actor" class="fieldInput">
            ${(['HUMAN', 'VERA', 'MUTUAL', 'UNKNOWN'] as VcaMemoryActor[]).map(actor => `<option value="${actor}">${actor}</option>`).join('')}
          </select>
          <label class="fieldLabel" for="vcaInboxBody">MEMORY EVENT</label>
          <textarea id="vcaInboxBody" name="body" class="fieldInput vcaInboxBody" placeholder="Paste or capture one meaningful Human / Vera memory event…"></textarea>
          <div class="curatorHint">This is the explicit capture boundary. No ChatGPT DOM scraping is used. Duplicate memories are rejected by fingerprint.</div>
          <button class="primaryButton" type="submit">CAPTURE TO VCA</button>
        </form>
        <div class="vcaInboxRecent">
          ${recent.length ? recent.map(item => `
            <div class="vcaInboxItem" data-status="${item.status}">
              <div><strong>${escapeHtml(item.sessionTitle)}</strong><span>${escapeHtml(item.actor)} · ${escapeHtml(item.status)}</span></div>
              <p>${escapeHtml(item.body.slice(0, 180))}</p>
              <small>${escapeHtml(item.threadKey)}${item.duplicateHits ? ` · DEDUPE ${item.duplicateHits}` : ''}</small>
            </div>
          `).join('') : '<div class="curatorDetail">Inbox is empty.</div>'}
        </div>
      </section>
    `
  }

  private vcaMemoryClockPanel(): string {
    const clock = this.vcaClock
    if (!clock) {
      return `<section class="memoryClockPanel pending"><div class="memoryClockHead"><strong>MEMORY CLOCK</strong><span>FRONTIER —</span></div><div class="memoryClockHint">Vertex-owned memory frontier is loading.</div></section>`
    }

    return `
      <section class="memoryClockPanel">
        <div class="memoryClockHead">
          <strong>MEMORY CLOCK</strong>
          <span>CANONICAL r${clock.canonicalRevision}</span>
        </div>
        <div class="memoryClockRail">
          ${clock.sessions.map((session, index) => `
            <div class="memoryClockLane" data-lag="${session.lag > 0}" title="${escapeHtml(session.sessionTitle)} · observed r${session.observedRevision} · compensated r${session.compensatedRevision}">
              <strong>V${String(index + 1).padStart(2, '0')}</strong>
              <span>${session.lag === 0 ? 'SYNC' : `Δ${session.lag}`}</span>
            </div>
          `).join('')}
        </div>
        <div class="memoryClockHint">Logical clock only. Compensation is not auto-injected into ChatGPT in this foundation patch.</div>
      </section>
    `
  }

  private vcaCuratorPanel(): string {
    const state = this.vcaCurator
    const settings = state?.settings ?? { laneId: 'lane-4' as AiLaneId, autoRun: false, batchSize: 8 }
    const status = !state
      ? 'LOADING'
      : state.ready
        ? 'READY'
        : state.configured
          ? 'NOT READY'
          : 'NO ASSISTANT'
    const provider = state?.provider ? providerName(state.provider) : '—'
    const model = state?.model ?? '—'

    return `
      <section class="vcaCuratorPanel">
        <div class="vcaCuratorHead">
          <div>
            <span class="assistantEyebrow">VCA MEMORY CURATOR</span>
            <strong>DEDICATED AI ASSISTANT</strong>
          </div>
          <span class="curatorStatus" data-ready="${state?.ready === true}">${status}</span>
        </div>
        <div class="vcaCuratorRoute">
          <span>${escapeHtml(settings.laneId.toUpperCase())}</span>
          <span>${escapeHtml(provider)}</span>
          <span>${escapeHtml(model)}</span>
          <span>PENDING ${state?.pendingCount ?? '—'}</span>
        </div>
        <form class="vcaCuratorForm">
          <label class="fieldLabel" for="curatorLane">ASSISTANT LANE</label>
          <select id="curatorLane" name="laneId" class="fieldInput">
            ${(['lane-1', 'lane-2', 'lane-3', 'lane-4', 'lane-5'] as AiLaneId[]).map(laneId => `<option value="${laneId}" ${laneId === settings.laneId ? 'selected' : ''}>${laneId.toUpperCase()}</option>`).join('')}
          </select>
          <label class="fieldLabel" for="curatorBatch">BATCH SIZE</label>
          <select id="curatorBatch" name="batchSize" class="fieldInput">
            ${[4, 8, 12, 16, 24].map(size => `<option value="${size}" ${size === settings.batchSize ? 'selected' : ''}>${size}</option>`).join('')}
          </select>
          <label class="curatorAuto">
            <input type="checkbox" name="autoRun" ${settings.autoRun ? 'checked' : ''} />
            <span>AUTO CURATE NEW VCA MEMORY</span>
          </label>
          <div class="curatorHint">Recommended starting point: a local ~12B Assistant. Human and Vera memories are peer-weighted; age alone never decays gravity.</div>
          <div class="curatorActions">
            <button class="veraButton" type="submit">SAVE CURATOR</button>
            <button class="primaryButton" type="button" data-action="run-curator-pending" ${state?.ready ? '' : 'disabled'}>RUN PENDING</button>
            <button class="veraButton" type="button" data-action="run-curator-reevaluate" ${state?.ready ? '' : 'disabled'}>RE-EVALUATE</button>
          </div>
        </form>
        <div class="curatorDetail">${escapeHtml(state?.detail ?? 'Loading VCA Curator state…')}</div>
      </section>
    `
  }

  private archiveSearch(kind: 'VCR' | 'VCA'): string {
    const results = kind === 'VCR'
      ? this.vcr.map((entry, index) => `
          <article class="resultCard vcrCard" data-vcr-index="${index}" tabindex="0" title="Double-click to open VCR card">
            <div class="resultHead"><strong>${escapeHtml(entry.key)}</strong><span>r${entry.revision}</span></div>
            <div class="resultTitle">${escapeHtml(entry.title)}</div>
            <div class="resultMeta">${escapeHtml(entry.category)} · ${escapeHtml(entry.status)} · ${escapeHtml(entry.updatedUtc)}</div>
            <div class="resultBody">${escapeHtml(entry.body.slice(0, 360))}</div>
            <div class="vcrCardHint">DOUBLE-CLICK · OPEN / EDIT</div>
          </article>
        `).join('')
      : this.vca.map(entry => `
          <article class="resultCard vcaMemoryCard">
            <div class="resultHead">
              <strong>${escapeHtml(entry.sessionTitle)}</strong>
              <span class="gravityBadge">G ${Math.round(entry.memoryGravity)}</span>
            </div>
            <div class="resultMeta">r${entry.memoryRevision} · ${escapeHtml(entry.actor)} · ${escapeHtml(entry.curator)} · ${escapeHtml(entry.createdUtc)}</div>
            <div class="resultBody">${escapeHtml(entry.body.slice(0, 460))}</div>
            <div class="vcaWeightLine">H ${Math.round(entry.humanSignal)} · V ${Math.round(entry.veraSignal)} · M ${Math.round(entry.mutualSignal)} · PURPOSE ${Math.round(entry.purposeRelation)} · IMPL ${Math.round(entry.implementationLink)}</div>
          </article>
        `).join('')

    return `
      ${kind === 'VCA' ? `${this.vcaInboxPanel()}${this.vcaMemoryClockPanel()}${this.vcaCuratorPanel()}` : ''}
      <form class="archiveSearch" data-kind="${kind}">
        <input name="query" class="fieldInput" value="${escapeHtml(this.searchQuery)}" placeholder="Search ${kind}…" autocomplete="off" />
        <button class="searchButton" type="submit">SEARCH</button>
      </form>
      <div class="archiveSummary">${this.loading ? 'LOADING…' : `${kind} · ${kind === 'VCR' ? this.vcr.length : this.vca.length} RESULTS${kind === 'VCA' && this.vcaClock ? ` · FRONTIER r${this.vcaClock.canonicalRevision}` : ''}`}</div>
      <div class="results">${results || `<div class="placeholder compact"><p class="copy">No ${kind} records found.</p></div>`}</div>
      ${kind === 'VCR' ? `
        <button class="vcrAddCard" type="button" data-action="add-vcr" aria-label="Add VCR card" title="Add VCR card">
          <span class="vcrAddGlyph">⊕</span>
          <span class="vcrAddLabel">ADD VCR</span>
        </button>
      ` : ''}
    `
  }

  private render(): void {
    const view = copy[this.activeTab]
    const tabs: SidebarTab[] = ['PROJECT', 'VCR', 'VCA', 'AI']

    let content = this.projectTree()
    if (this.activeTab === 'AI') content = this.providerPanel()
    if (this.activeTab === 'VCR') content = this.archiveSearch('VCR')
    if (this.activeTab === 'VCA') content = this.archiveSearch('VCA')

    this.shadowRoot!.innerHTML = `
      <style>${styles}</style>
      <aside class="explorer">
        <div class="explorerHeader">
          <div><div class="eyebrow">${view.eyebrow}</div><h2 class="title">${view.title}</h2></div>
          <button class="headerAction" title="Explorer actions" type="button">•••</button>
        </div>
        <nav class="tabs">
          ${tabs.map(tab => `<button class="tab" data-tab="${tab}" data-active="${tab === this.activeTab}" type="button">${tab}</button>`).join('')}
        </nav>
        <section class="body">
          ${content}
          ${this.detail ? `<div class="card">${escapeHtml(this.detail)}</div>` : ''}
        </section>
      </aside>
      ${this.vcrEditorModal()}
    `

    for (const button of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('.tab')) {
      button.addEventListener('click', () => {
        this.dispatchEvent(new CustomEvent<SidebarTab>('vertex-sidebar-tab', {
          bubbles: true,
          composed: true,
          detail: button.dataset.tab as SidebarTab
        }))
      })
    }

    if (this.activeTab === 'PROJECT') {
      this.shadowRoot!.querySelector<HTMLButtonElement>('[data-action="project-refresh"]')?.addEventListener('click', () => {
        void this.refreshProjectDirectory()
      })
      this.shadowRoot!.querySelector<HTMLButtonElement>('[data-action="project-up"]')?.addEventListener('click', () => {
        if (this.projectParentPath) void this.navigateProjectRoot(this.projectParentPath)
      })
      this.shadowRoot!.querySelector<HTMLButtonElement>('[data-action="project-home"]')?.addEventListener('click', () => {
        if (this.projectCanonicalRootPath) void this.navigateProjectRoot(this.projectCanonicalRootPath)
      })
      for (const breadcrumb of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('[data-project-breadcrumb]')) {
        breadcrumb.addEventListener('click', () => {
          const path = breadcrumb.dataset.projectBreadcrumb
          if (path) void this.navigateProjectRoot(path)
        })
      }

      for (const toggle of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('[data-tree-toggle]')) {
        toggle.addEventListener('click', event => {
          event.stopPropagation()
          const path = toggle.dataset.treeToggle
          if (path) void this.toggleProjectDirectory(path)
        })
      }

      for (const row of this.shadowRoot!.querySelectorAll<HTMLElement>('.treeRow[data-path]')) {
        const path = row.dataset.path ?? ''
        const kind = row.dataset.kind ?? ''

        row.addEventListener('click', () => {
          this.projectContextMenu = null
          this.selectProjectPath(path)
        })

        row.addEventListener('dblclick', event => {
          if ((event.target as HTMLElement).closest('.treeToggle')) return
          this.selectProjectPath(path)
          if (kind === 'DIRECTORY') {
            if (path !== this.projectRootPath) void this.navigateProjectRoot(path)
          } else {
            void window.vertexPortal.openProjectTreePath(path).catch((error: unknown) => {
              this.detail = error instanceof Error ? error.message : String(error)
              this.render()
            })
          }
        })

        row.addEventListener('keydown', event => {
          if (event.key === 'Enter') {
            event.preventDefault()
            if (kind === 'DIRECTORY') {
              if (path !== this.projectRootPath) void this.navigateProjectRoot(path)
            } else void window.vertexPortal.openProjectTreePath(path)
          } else if (event.key === 'ArrowRight' && kind === 'DIRECTORY') {
            event.preventDefault()
            if (!this.projectExpanded.has(path)) void this.toggleProjectDirectory(path)
          } else if (event.key === 'ArrowLeft' && kind === 'DIRECTORY') {
            event.preventDefault()
            if (this.projectExpanded.has(path)) void this.toggleProjectDirectory(path)
          } else if (event.key === 'F5') {
            event.preventDefault()
            void this.refreshProjectDirectory(path)
          }
        })

        row.addEventListener('contextmenu', event => {
          event.preventDefault()
          this.selectProjectPath(path)
          this.projectContextMenu = {
            x: Math.max(8, Math.min(event.clientX, window.innerWidth - 188)),
            y: Math.max(8, Math.min(event.clientY, window.innerHeight - 168)),
            path
          }
          this.render()
        })
      }

      for (const action of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('[data-tree-menu]')) {
        action.addEventListener('click', event => {
          event.stopPropagation()
          const path = this.projectContextMenu?.path
          const command = action.dataset.treeMenu
          if (!path || !command) return
          this.projectContextMenu = null

          if (command === 'root') {
            void this.navigateProjectRoot(path)
          } else if (command === 'open') {
            void window.vertexPortal.openProjectTreePath(path).catch((error: unknown) => {
              this.detail = error instanceof Error ? error.message : String(error)
              this.render()
            })
          } else if (command === 'reveal') {
            void window.vertexPortal.revealProjectTreePath(path).catch((error: unknown) => {
              this.detail = error instanceof Error ? error.message : String(error)
              this.render()
            })
          } else if (command === 'copy') {
            void window.vertexPortal.copyProjectTreePath(path).then(() => {
              this.detail = `Copied path: ${path}`
              this.render()
            }).catch((error: unknown) => {
              this.detail = error instanceof Error ? error.message : String(error)
              this.render()
            })
          } else if (command === 'refresh') {
            void this.refreshProjectDirectory(path)
          }
        })
      }

      this.shadowRoot!.querySelector<HTMLElement>('.explorer')?.addEventListener('click', event => {
        if (!this.projectContextMenu) return
        if ((event.target as HTMLElement).closest('[data-tree-context]')) return
        this.projectContextMenu = null
        this.render()
      })
    }

    for (const button of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('.laneButton')) {
      button.addEventListener('click', () => {
        this.selectedLaneId = button.dataset.lane as AiLaneId
        this.modelOptions = []
        this.detail = ''
        this.render()
      })
    }

    this.shadowRoot!.querySelector<HTMLButtonElement>('[data-action="add-lane"]')?.addEventListener('click', () => {
      void window.vertexPortal.activateNextMainLane().then(state => {
        this.activeMainLanes = state.sessions.filter(session => session.kind === 'MAIN' && session.active).length
        this.detail = this.activeMainLanes >= 5
          ? 'All five Vera sessions are active.'
          : `Active Vera sessions: ${this.activeMainLanes}/5.`
        this.render()
        this.dispatchEvent(new CustomEvent('vertex-lanes-changed', {
          bubbles: true,
          composed: true,
          detail: state
        }))
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    })

    const settingsForm = this.shadowRoot!.querySelector<HTMLFormElement>('.settingsForm')
    const providerSelect = settingsForm?.querySelector<HTMLSelectElement>('select[name="provider"]')
    const endpointInput = settingsForm?.querySelector<HTMLInputElement>('input[name="endpoint"]')
    const modelInput = settingsForm?.querySelector<HTMLInputElement>('input[name="model"]')
    const apiKeyInput = settingsForm?.querySelector<HTMLInputElement>('input[name="apiKey"]')
    const localField = settingsForm?.querySelector<HTMLElement>('[data-local-field]')
    const localPathInput = settingsForm?.querySelector<HTMLInputElement>('input[name="localModelPath"]')
    const refreshButton = settingsForm?.querySelector<HTMLButtonElement>('[data-action="refresh-models"]')

    providerSelect?.addEventListener('change', () => {
      if (!endpointInput || !modelInput || !apiKeyInput || !localField || !refreshButton) return
      const value = providerSelect.value
      const noAssistant = value === ''
      const local = value === 'local'
      localField.dataset.visible = String(local)
      endpointInput.disabled = noAssistant || local
      modelInput.disabled = noAssistant
      apiKeyInput.disabled = noAssistant || local
      refreshButton.disabled = noAssistant

      if (noAssistant) {
        endpointInput.value = ''
        modelInput.value = ''
        if (localPathInput) localPathInput.value = ''
        return
      }

      const nextProvider = value as ProviderKind
      const knownEndpoints = new Set(Object.values(providerEndpoints))
      if (!local && (!endpointInput.value.trim() || knownEndpoints.has(endpointInput.value.trim()))) {
        endpointInput.value = providerEndpoints[nextProvider]
      }
      if (local) endpointInput.value = ''
      this.clearModelDatalist()
    })

    settingsForm?.querySelector<HTMLButtonElement>('[data-action="browse-local"]')?.addEventListener('click', () => {
      void window.vertexPortal.browseLocalLlm().then(path => {
        if (!path || !localPathInput || !modelInput) return
        localPathInput.value = path
        modelInput.value = basename(path)
        this.setModelDatalist([basename(path)])
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    })

    refreshButton?.addEventListener('click', () => {
      void this.refreshModelOptionsFromForm(settingsForm)
    })

    settingsForm?.addEventListener('submit', event => {
      event.preventDefault()
      const data = new FormData(settingsForm)
      const providerText = String(data.get('provider') ?? '')
      const request = providerText
        ? {
            laneId: this.selectedLaneId,
            provider: providerText as ProviderKind,
            endpoint: String(data.get('endpoint') ?? ''),
            model: String(data.get('model') ?? ''),
            localModelPath: String(data.get('localModelPath') ?? ''),
            apiKey: String(data.get('apiKey') ?? '') || undefined
          }
        : {
            laneId: this.selectedLaneId,
            provider: null
          }

      void window.vertexPortal.saveAiLaneSettings(request).then(state => {
        this.aiSettings = state
        this.modelOptions = []
        this.detail = `${this.selectedLaneId.toUpperCase()} AI Assistant saved.`
        this.render()
        this.dispatchEvent(new CustomEvent('vertex-provider-settings-changed', { bubbles: true, composed: true }))
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    })

    settingsForm?.querySelector<HTMLButtonElement>('[data-action="remove-assistant"]')?.addEventListener('click', () => {
      void window.vertexPortal.saveAiLaneSettings({ laneId: this.selectedLaneId, provider: null }).then(state => {
        this.aiSettings = state
        this.modelOptions = []
        this.detail = `${this.selectedLaneId.toUpperCase()} AI Assistant removed. Vera remains primary.`
        this.render()
        this.dispatchEvent(new CustomEvent('vertex-provider-settings-changed', { bubbles: true, composed: true }))
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    })

    settingsForm?.querySelector<HTMLButtonElement>('[data-action="clear-key"]')?.addEventListener('click', () => {
      void window.vertexPortal.clearAiLaneApiKey(this.selectedLaneId).then(state => {
        this.aiSettings = state
        this.detail = `${this.selectedLaneId.toUpperCase()} stored API key cleared.`
        this.render()
        this.dispatchEvent(new CustomEvent('vertex-provider-settings-changed', { bubbles: true, composed: true }))
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    })

    this.shadowRoot!.querySelector<HTMLButtonElement>('[data-action="add-vcr"]')?.addEventListener('click', () => {
      this.openVcrEditor(null)
    })

    for (const card of this.shadowRoot!.querySelectorAll<HTMLElement>('.vcrCard')) {
      const openCard = (): void => {
        const index = Number(card.dataset.vcrIndex)
        const entry = this.vcr[index]
        if (entry) this.openVcrEditor(entry)
      }
      card.addEventListener('dblclick', openCard)
      card.addEventListener('keydown', event => {
        if (event.key === 'Enter') {
          event.preventDefault()
          openCard()
        }
      })
    }

    for (const closeButton of this.shadowRoot!.querySelectorAll<HTMLButtonElement>('[data-action="close-vcr"]')) {
      closeButton.addEventListener('click', () => this.closeVcrEditor())
    }

    this.shadowRoot!.querySelector<HTMLElement>('[data-vcr-modal-backdrop]')?.addEventListener('mousedown', event => {
      if (event.target === event.currentTarget) this.closeVcrEditor()
    })

    const vcrEditorForm = this.shadowRoot!.querySelector<HTMLFormElement>('.vcrEditorForm')
    vcrEditorForm?.addEventListener('submit', event => {
      event.preventDefault()
      const data = new FormData(vcrEditorForm)
      const key = String(data.get('key') ?? '').trim()
      const title = String(data.get('title') ?? '').trim()
      const category = String(data.get('category') ?? '').trim()
      const status = String(data.get('status') ?? '').trim()
      const body = String(data.get('body') ?? '').trim()
      const errorBox = this.shadowRoot!.querySelector<HTMLElement>('.vcrModalError')
      const saveButton = vcrEditorForm.querySelector<HTMLButtonElement>('.vcrSaveButton')

      if (!key || !title || !category || !status || !body) {
        if (errorBox) errorBox.textContent = 'KEY / TITLE / CATEGORY / STATUS / CONTENT are required.'
        return
      }

      if (saveButton) {
        saveButton.disabled = true
        saveButton.textContent = 'SAVING…'
      }
      if (errorBox) errorBox.textContent = ''

      void window.vertexPortal.upsertVcrEntry({ key, title, category, status, body }).then(saved => {
        this.vcrEditorOpen = false
        this.vcrEditorEntry = null
        this.vcrDraftKey = ''
        this.vcrEditorClosing = false
        this.detail = `${saved.key} · revision ${saved.revision} saved.`
        void this.loadVcr(this.searchQuery)
      }).catch((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error)
        if (errorBox) errorBox.textContent = message
        if (saveButton) {
          saveButton.disabled = false
          saveButton.textContent = this.vcrEditorEntry ? 'SAVE NEW REVISION' : 'CREATE VCR'
        }
      })
    })

    const inboxForm = this.shadowRoot!.querySelector<HTMLFormElement>('.vcaInboxForm')
    inboxForm?.addEventListener('submit', event => {
      event.preventDefault()
      const data = new FormData(inboxForm)
      const body = String(data.get('body') ?? '').trim()
      if (!body) {
        this.detail = 'VCA MEMORY EVENT is required.'
        this.render()
        return
      }
      const sessionId = String(data.get('sessionId') ?? 'vera-01')
      const thread = this.vcaThreads.find(item => item.sessionId === sessionId)
      void window.vertexPortal.enqueueVcaInbox({
        sessionId,
        actor: String(data.get('actor') ?? 'UNKNOWN') as VcaMemoryActor,
        body,
        captureKind: 'MANUAL_BOUNDARY',
        threadUrl: thread?.threadUrl
      }).then(result => {
        this.detail = result.duplicate
          ? `VCA INBOX · duplicate blocked · ${result.item.sessionTitle}`
          : `VCA INBOX · captured · ${result.item.sessionTitle} · ${result.item.status}`
        void this.loadVca(this.searchQuery)
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    })

    const curatorForm = this.shadowRoot!.querySelector<HTMLFormElement>('.vcaCuratorForm')
    curatorForm?.addEventListener('submit', event => {
      event.preventDefault()
      const data = new FormData(curatorForm)
      void window.vertexPortal.saveVcaCuratorSettings({
        laneId: String(data.get('laneId') ?? 'lane-4') as AiLaneId,
        autoRun: data.get('autoRun') === 'on',
        batchSize: Number(data.get('batchSize') ?? 8)
      }).then(state => {
        this.vcaCurator = state
        this.detail = `VCA Curator saved · ${state.settings.laneId.toUpperCase()} · ${state.ready ? 'READY' : state.detail}`
        this.render()
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    })

    const runCurator = (mode: 'PENDING' | 'REEVALUATE'): void => {
      const button = this.shadowRoot!.querySelector<HTMLButtonElement>(mode === 'PENDING' ? '[data-action="run-curator-pending"]' : '[data-action="run-curator-reevaluate"]')
      if (button) {
        button.disabled = true
        button.textContent = 'RUNNING…'
      }
      void window.vertexPortal.runVcaCurator({ mode }).then(result => {
        this.detail = `VCA CURATOR ${result.mode} · ${result.processed}/${result.candidateCount} weighted · ${result.model ?? 'NO MODEL'}`
        if (result.failures.length) this.detail += ` · ${result.failures.join(' | ')}`
        void this.loadVca(this.searchQuery)
      }).catch((error: unknown) => {
        this.detail = error instanceof Error ? error.message : String(error)
        this.render()
      })
    }

    this.shadowRoot!.querySelector<HTMLButtonElement>('[data-action="run-curator-pending"]')?.addEventListener('click', () => runCurator('PENDING'))
    this.shadowRoot!.querySelector<HTMLButtonElement>('[data-action="run-curator-reevaluate"]')?.addEventListener('click', () => runCurator('REEVALUATE'))

    const archive = this.shadowRoot!.querySelector<HTMLFormElement>('.archiveSearch')
    archive?.addEventListener('submit', event => {
      event.preventDefault()
      const query = String(new FormData(archive).get('query') ?? '')
      this.searchQuery = query
      if (archive.dataset.kind === 'VCR') void this.loadVcr(query)
      if (archive.dataset.kind === 'VCA') void this.loadVca(query)
    })
  }

  private async refreshModelOptionsFromForm(form: HTMLFormElement | null | undefined): Promise<void> {
    if (!form) return
    const data = new FormData(form)
    const providerText = String(data.get('provider') ?? '')
    if (!providerText) return
    const button = form.querySelector<HTMLButtonElement>('[data-action="refresh-models"]')
    if (button) {
      button.disabled = true
      button.textContent = '…'
    }
    try {
      const models = await window.vertexPortal.listAiLaneModels({
        laneId: this.selectedLaneId,
        provider: providerText as ProviderKind,
        endpoint: String(data.get('endpoint') ?? ''),
        localModelPath: String(data.get('localModelPath') ?? '')
      })
      this.modelOptions = models
      this.setModelDatalist(models)
      const modelInput = form.querySelector<HTMLInputElement>('input[name="model"]')
      if (modelInput && !modelInput.value.trim() && models.length === 1) modelInput.value = models[0]
      this.detail = models.length ? `${models.length} model(s) available.` : 'No model list returned. Manual entry remains available.'
      const card = this.shadowRoot!.querySelector<HTMLElement>('.card')
      if (card) card.textContent = this.detail
    } catch (error: unknown) {
      this.detail = error instanceof Error ? error.message : String(error)
      this.setModelDatalist([])
    } finally {
      if (button) {
        button.disabled = false
        button.textContent = 'LIST'
      }
    }
  }

  private clearModelDatalist(): void {
    this.modelOptions = []
    this.setModelDatalist([])
  }

  private setModelDatalist(models: string[]): void {
    const list = this.shadowRoot!.querySelector<HTMLDataListElement>('#availableModels')
    if (!list) return
    list.innerHTML = Array.from(new Set(models.filter(Boolean)))
      .map(item => `<option value="${escapeHtml(item)}"></option>`)
      .join('')
  }
}

customElements.define('vertex-explorer', VertexExplorer)
