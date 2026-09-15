import './vra/vra-dispatch-destination-bootstrap'
import {
  app,
  BrowserWindow,
  session as electronSession
} from 'electron'
import {
  mkdirSync
} from 'node:fs'
import {
  join,
  resolve
} from 'node:path'
import {
  SessionAgentService
} from './agents/session-agent-service'
import {
  SessionAgentStore
} from './agents/session-agent-store'
import {
  LocalRetrievalService
} from './retrieval/local-retrieval-service'
import {
  ProviderSettingsStore
} from './providers/provider-settings-store'
import {
  ConfiguredProvider
} from './providers/configured-provider'
import {
  VcaCuratorService
} from './memory/vca-curator-service'
import {
  runInteractionProbe
} from './diagnostics/interaction-probe'
import {
  runRealLlmProbe
} from './diagnostics/real-llm-probe'
import {
  runRuntimeProbe
} from './diagnostics/runtime-probe'
import {
  runResponsiveSessionSizingProbe
} from './diagnostics/responsive-session-sizing-probe'
import {
  runPaneComposerProbe
} from './diagnostics/pane-composer-probe'
import {
  runVisualCanonicalProbe
} from './diagnostics/visual-canonical-probe'
import {
  runSearchVeraProbe
} from './diagnostics/search-vera-probe'
import {
  runUiControlProbe
} from './diagnostics/ui-control-probe'
import {
  runVirtualArdProbe
} from './diagnostics/virtual-ard-probe'
import {
  registerSessionAgentIpc
} from './ipc/register-session-agent-ipc'
import {
  registerWorkstationIpc
} from './ipc/register-workstation-ipc'
import {
  registerVraDispatchIpc
} from './ipc/register-vra-dispatch-ipc'
import {
  registerProjectTreeIpc
} from './ipc/register-project-tree-ipc'
import {
  ProjectTreeService
} from './project/project-tree-service'
import {
  VraDispatchService
} from './vra/vra-dispatch-service'
import {
  WorkstationDb
} from './storage/workstation-db'

// VERTEX_SESSION_PORTAL_STREAM_STABILITY_000049_BEGIN
app.commandLine.appendSwitch('disable-renderer-backgrounding')
app.commandLine.appendSwitch('disable-background-timer-throttling')
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows')
// VERTEX_SESSION_PORTAL_STREAM_STABILITY_000049_END

const runtimeProbeMode =
  process.env.VERTEX_RUNTIME_PROBE === '1'

const interactionProbeMode =
  process.env.VERTEX_INTERACTION_PROBE === '1'

const uiControlProbeMode =
  process.env.VERTEX_UI_CONTROL_PROBE === '1'

const virtualArdProbeMode =
  process.env.VERTEX_VIRTUAL_ARD_PROBE === '1'

const realLlmProbeMode =
  process.env.VERTEX_REAL_LLM_PROBE === '1'

const searchVeraProbeMode =
  process.env.VERTEX_SEARCH_VERA_PROBE === '1'

const visualCanonicalProbeMode =
  process.env.VERTEX_VISUAL_CANONICAL_PROBE === '1'

const responsiveSessionProbeMode =
  process.env.VERTEX_RESPONSIVE_SESSION_PROBE === '1'

const paneComposerProbeMode =
  process.env.VERTEX_PANE_COMPOSER_PROBE === '1'

const diagnosticMode =
  runtimeProbeMode ||
  interactionProbeMode ||
  uiControlProbeMode ||
  virtualArdProbeMode ||
  realLlmProbeMode ||
  searchVeraProbeMode ||
  visualCanonicalProbeMode ||
  responsiveSessionProbeMode ||
  paneComposerProbeMode

function evidenceRoot(
  name: string
): string {
  return join(
    process.cwd(),
    'EVIDENCE',
    name
  )
}

const runtimeProbeRoot =
  evidenceRoot('RUNTIME_PROBE_000013')

const interactionProbeRoot =
  evidenceRoot('INTERACTION_PROBE_000014')

const uiControlProbeRoot =
  evidenceRoot('UI_CONTROL_PROBE_000015')

const virtualArdProbeRoot =
  evidenceRoot('VIRTUAL_ARD_PROBE_000016')

const realLlmProbeRoot =
  evidenceRoot('REAL_LLM_PROBE_000017')

const searchVeraProbeRoot =
  evidenceRoot('SEARCH_VERA_PROBE_000018')

const visualCanonicalProbeRoot =
  evidenceRoot('VISUAL_CANONICAL_PROBE_000020')

function isolateDiagnosticUserData(
  root: string
): void {
  mkdirSync(
    root,
    { recursive: true }
  )

  app.setPath(
    'userData',
    join(
      root,
      'userData'
    )
  )
}

if (runtimeProbeMode) {
  isolateDiagnosticUserData(runtimeProbeRoot)
}

if (interactionProbeMode) {
  isolateDiagnosticUserData(interactionProbeRoot)
}

if (uiControlProbeMode) {
  isolateDiagnosticUserData(uiControlProbeRoot)
}

if (virtualArdProbeMode) {
  isolateDiagnosticUserData(virtualArdProbeRoot)
}

if (realLlmProbeMode) {
  isolateDiagnosticUserData(realLlmProbeRoot)
}

if (searchVeraProbeMode) {
  isolateDiagnosticUserData(searchVeraProbeRoot)
}

if (visualCanonicalProbeMode) {
  isolateDiagnosticUserData(visualCanonicalProbeRoot)
}

if (responsiveSessionProbeMode) {
  isolateDiagnosticUserData(evidenceRoot('RESPONSIVE_SESSION_PROBE_000022'))
}

if (paneComposerProbeMode) {
  isolateDiagnosticUserData(evidenceRoot('PANE_COMPOSER_PROBE_000024'))
}

let mainWindow:
  BrowserWindow | null = null

let workstationDb:
  WorkstationDb | null = null

let sessionAgentStore:
  SessionAgentStore | null = null

let providerSettingsStore:
  ProviderSettingsStore | null = null

let vcaCuratorService:
  VcaCuratorService | null = null

let vraDispatchService:
  VraDispatchService | null = null

const VERA_CHATGPT_PARTITION =
  'persist:vertex-vera-chatgpt'

function isHttpsNavigation(
  value: string
): boolean {
  try {
    return new URL(value).protocol === 'https:'
  } catch {
    return false
  }
}

function isChatGptAttachUrl(
  value: string
): boolean {
  try {
    const url = new URL(value)
    return (
      url.protocol === 'https:' &&
      url.hostname === 'chatgpt.com'
    )
  } catch {
    return false
  }
}

function createWindow():
  BrowserWindow {
  const window =
    new BrowserWindow({
      width: 3200,
      height: 1300,
      minWidth: 1100,
      minHeight: 720,
      backgroundColor:'#090b10',
      show: false,
      autoHideMenuBar: true,
      webPreferences: {
        preload: join(
          __dirname,
          '../preload/index.cjs'
        ),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
        webSecurity: true,
        backgroundThrottling: false,
        webviewTag: true
      }
    })

  window.webContents.on(
    'will-attach-webview',
    (
      event,
      webPreferences,
      params
    ) => {
      if (
        !isChatGptAttachUrl(params.src) ||
        params.partition !== VERA_CHATGPT_PARTITION
      ) {
        event.preventDefault()
        return
      }

      delete webPreferences.preload
      webPreferences.nodeIntegration = false
      webPreferences.nodeIntegrationInSubFrames = false
      webPreferences.contextIsolation = true
      webPreferences.sandbox = true
      webPreferences.webSecurity = true
      webPreferences.backgroundThrottling = false
      webPreferences.allowRunningInsecureContent = false
    }
  )

  window.webContents.on(
    'did-attach-webview',
    (
      _event,
      contents
    ) => {
      contents.on(
        'will-navigate',
        (
          event,
          url
        ) => {
          if (!isHttpsNavigation(url)) {
            event.preventDefault()
          }
        }
      )

      contents.setWindowOpenHandler(
        ({ url }) => {
          if (!isHttpsNavigation(url)) {
            return { action: 'deny' }
          }

          return {
            action: 'allow',
            overrideBrowserWindowOptions: {
              autoHideMenuBar: true,
              backgroundColor: '#090b10',
              webPreferences: {
                partition: VERA_CHATGPT_PARTITION,
                contextIsolation: true,
                nodeIntegration: false,
                sandbox: true,
                webSecurity: true,
                backgroundThrottling: false // POPUP_BACKGROUND_THROTTLING_000049
              }
            }
          }
        }
      )
    }
  )

  if (!diagnosticMode) {
    window.once(
      'ready-to-show',
      () => {
        window.show()
      }
    )
  }

  const rendererUrl =
    process.env.ELECTRON_RENDERER_URL

  if (rendererUrl) {
    void window.loadURL(rendererUrl)
  } else {
    void window.loadFile(
      join(
        __dirname,
        '../renderer/index.html'
      )
    )
  }

  return window
}

function finishProbe(
  marker: string,
  code: number,
  action: Promise<void>
): void {
  void action
    .then(() => {
      console.log(`${marker}=PASS`)
      app.exit(0)
    })
    .catch((error: unknown) => {
      const message =
        error instanceof Error
          ? error.stack ?? error.message
          : String(error)

      console.error(message)
      console.log(`${marker}=FAIL`)
      app.exit(code)
    })
}

app.whenReady().then(() => {
  const dbPath =
    join(
      app.getPath('userData'),
      'vertex-session-portal.sqlite3'
    )

  workstationDb =
    new WorkstationDb(dbPath)

  sessionAgentStore =
    new SessionAgentStore(dbPath)

  providerSettingsStore =
    new ProviderSettingsStore(dbPath)

  const configuredProvider =
    new ConfiguredProvider(
      providerSettingsStore
    )

  const sessionAgentService =
    new SessionAgentService(
      sessionAgentStore,
      new LocalRetrievalService(
        process.cwd()
      ),
      providerSettingsStore,
      configuredProvider
    )

  vcaCuratorService =
    new VcaCuratorService(
      workstationDb,
      providerSettingsStore,
      configuredProvider
    )

  const worksIncomingRoot =
    process.env.VERTEX_WORKS_INCOMING?.trim() ||
    resolve(process.cwd(), '..', '_incoming')

  vraDispatchService =
    new VraDispatchService(
      app.getPath('userData'),
      worksIncomingRoot
    )

  vraDispatchService.attachToSession(
    electronSession.fromPartition(VERA_CHATGPT_PARTITION)
  )

  registerWorkstationIpc(
    workstationDb,
    vcaCuratorService
  )

  registerVraDispatchIpc(vraDispatchService)
  // VERTEX_SYSTEM_POLICY_RESOLVER_000062V2
  registerSystemPolicyIpc()

  registerProjectTreeIpc(
    new ProjectTreeService(process.cwd())
  )

  registerSessionAgentIpc(
    sessionAgentService
  )

  if (!diagnosticMode) {
    vcaCuratorService.start()
  }

  mainWindow = createWindow()

  vraDispatchService.onChanged(() => {
    mainWindow?.webContents.send('vra-dispatch:changed')
  })

  if (runtimeProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_RUNTIME_PROBE_000013',
      5,
      runRuntimeProbe(
        mainWindow,
        runtimeProbeRoot
      )
    )
    return
  }

  if (interactionProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_INTERACTION_PROBE_000014',
      6,
      runInteractionProbe(
        mainWindow,
        interactionProbeRoot
      )
    )
    return
  }

  if (uiControlProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_UI_CONTROL_PROBE_000015',
      7,
      runUiControlProbe(
        mainWindow,
        uiControlProbeRoot
      )
    )
    return
  }

  if (virtualArdProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_VIRTUAL_ARD_PROBE_000016',
      8,
      runVirtualArdProbe(
        mainWindow,
        virtualArdProbeRoot
      )
    )
    return
  }

  if (realLlmProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_REAL_LLM_PROBE_000017',
      9,
      runRealLlmProbe(
        mainWindow,
        realLlmProbeRoot
      )
    )
    return
  }

  if (searchVeraProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_SEARCH_VERA_PROBE_000018',
      10,
      runSearchVeraProbe(
        mainWindow,
        searchVeraProbeRoot
      )
    )
    return
  }

  if (visualCanonicalProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_VISUAL_CANONICAL_PROBE_000020',
      11,
      runVisualCanonicalProbe(
        mainWindow,
        visualCanonicalProbeRoot
      )
    )
    return
  }

  if (responsiveSessionProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_RESPONSIVE_SESSION_PROBE_000022',
      12,
      runResponsiveSessionSizingProbe(mainWindow)
    )
    return
  }

  if (paneComposerProbeMode) {
    finishProbe(
      'VERTEX_SESSION_PORTAL_PANE_COMPOSER_PROBE_000024',
      13,
      runPaneComposerProbe(mainWindow)
    )
    return
  }

  app.on(
    'activate',
    () => {
      if (
        BrowserWindow.getAllWindows().length === 0
      ) {
        mainWindow = createWindow()
      }
    }
  )
})

app.on(
  'window-all-closed',
  () => {
    if (
      !diagnosticMode &&
      process.platform !== 'darwin'
    ) {
      app.quit()
    }
  }
)

app.on(
  'before-quit',
  () => {
    vcaCuratorService?.stop()
    vcaCuratorService = null

    vraDispatchService = null

    sessionAgentStore?.close()
    sessionAgentStore = null

    providerSettingsStore?.close()
    providerSettingsStore = null

    workstationDb?.close()
    workstationDb = null
  }
)

// VERTEX_FOCUS_SCROLL_EVENT_RAY_000076V4H1
import './diagnostics/focus-scroll-event-ray'

// VERTEX_OBSERVABILITY_CORE_000078V4
import './observability'
import { registerSystemPolicyIpc } from './ipc/register-system-policy-ipc'
