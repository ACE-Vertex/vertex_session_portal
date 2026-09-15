import type { BrowserWindow, NativeImage } from 'electron'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

interface InteractionState {
  preloadBridge: boolean
  sessionCount: number
  priorities: string[]
  widths: Record<string, number>
  sidebarTab: string | null
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function waitForLoad(window: BrowserWindow): Promise<void> {
  if (!window.webContents.isLoading()) {
    return
  }

  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error('INTERACTION_RENDERER_LOAD_TIMEOUT')),
      15000
    )

    window.webContents.once('did-finish-load', () => {
      clearTimeout(timeout)
      resolve()
    })

    window.webContents.once(
      'did-fail-load',
      (_event, errorCode, errorDescription) => {
        clearTimeout(timeout)
        reject(
          new Error(
            `INTERACTION_RENDERER_LOAD_FAILED:${errorCode}:${errorDescription}`
          )
        )
      }
    )
  })
}

async function inspect(window: BrowserWindow): Promise<InteractionState> {
  const json = await window.webContents.executeJavaScript(
    `
    (() => {
      const frame = document.querySelector('vertex-main-frame')
      const root = frame && frame.shadowRoot ? frame.shadowRoot : null
      const sessions = root
        ? Array.from(root.querySelectorAll('vera-session, search-vera'))
        : []

      const widths = {}
      const priorities = []

      for (const element of sessions) {
        const id = element.getAttribute('session-id') || ''
        widths[id] = Math.round(element.getBoundingClientRect().width)

        if (element.hasAttribute('priority')) {
          priorities.push(id)
        }
      }

      const explorer = root ? root.querySelector('vertex-explorer') : null
      const explorerRoot = explorer && explorer.shadowRoot ? explorer.shadowRoot : null
      const activeButton = explorerRoot
        ? explorerRoot.querySelector('.tab[data-active="true"]')
        : null

      return JSON.stringify({
        preloadBridge: typeof window.vertexPortal !== 'undefined',
        sessionCount: sessions.length,
        priorities,
        widths,
        sidebarTab: activeButton ? activeButton.getAttribute('data-tab') : null
      })
    })()
    `,
    true
  ) as string

  return JSON.parse(json) as InteractionState
}

async function waitForState(
  window: BrowserWindow,
  predicate: (state: InteractionState) => boolean,
  label: string
): Promise<InteractionState> {
  let last: InteractionState | null = null

  for (let attempt = 1; attempt <= 32; attempt += 1) {
    last = await inspect(window)

    if (predicate(last)) {
      console.log(`WAIT_${label}=PASS attempt=${attempt}`)
      return last
    }

    await delay(125)
  }

  throw new Error(
    `WAIT_${label}_TIMEOUT:${JSON.stringify(last)}`
  )
}

async function clickPrioritySession(
  window: BrowserWindow,
  sessionId: string
): Promise<void> {
  const result = await window.webContents.executeJavaScript(
    `
    (() => {
      const frame = document.querySelector('vertex-main-frame')
      const root = frame && frame.shadowRoot ? frame.shadowRoot : null
      const target = root
        ? root.querySelector('[session-id="${sessionId}"]')
        : null

      if (!target) {
        return 'NOT_FOUND'
      }

      target.click()
      return 'CLICKED'
    })()
    `,
    true
  ) as string

  if (result !== 'CLICKED') {
    throw new Error(`SESSION_CLICK_FAILED:${sessionId}:${result}`)
  }
}

async function clickSidebarTab(
  window: BrowserWindow,
  tab: string
): Promise<void> {
  const result = await window.webContents.executeJavaScript(
    `
    (() => {
      const frame = document.querySelector('vertex-main-frame')
      const root = frame && frame.shadowRoot ? frame.shadowRoot : null
      const explorer = root ? root.querySelector('vertex-explorer') : null
      const explorerRoot = explorer && explorer.shadowRoot ? explorer.shadowRoot : null
      const target = explorerRoot
        ? explorerRoot.querySelector('.tab[data-tab="${tab}"]')
        : null

      if (!target) {
        return 'NOT_FOUND'
      }

      target.click()
      return 'CLICKED'
    })()
    `,
    true
  ) as string

  if (result !== 'CLICKED') {
    throw new Error(`SIDEBAR_CLICK_FAILED:${tab}:${result}`)
  }
}

async function waitPresentedFrame(window: BrowserWindow): Promise<void> {
  window.webContents.setBackgroundThrottling(false)

  if (!window.isVisible()) {
    window.showInactive()
  }

  window.webContents.invalidate()

  await window.webContents.executeJavaScript(
    `
    new Promise((resolve) => {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => resolve('FRAME_PRESENTED'))
      })
    })
    `,
    true
  )

  await delay(300)
}

async function capture(window: BrowserWindow): Promise<NativeImage> {
  let lastError = ''

  for (let attempt = 1; attempt <= 6; attempt += 1) {
    try {
      await waitPresentedFrame(window)
      const image = await window.webContents.capturePage()

      if (!image.isEmpty()) {
        console.log(`INTERACTION_SCREENSHOT_ATTEMPT=${attempt} PASS`)
        return image
      }

      lastError = 'EMPTY'
    } catch (error) {
      lastError =
        error instanceof Error ? error.stack ?? error.message : String(error)
    }

    await delay(250)
  }

  throw new Error(`INTERACTION_SCREENSHOT_FAILED:${lastError}`)
}

function requireInitial(state: InteractionState): void {
  if (!state.preloadBridge) {
    throw new Error('INITIAL_PRELOAD_BRIDGE_FAIL')
  }

  if (state.sessionCount !== 4) {
    throw new Error(`INITIAL_SESSION_COUNT_FAIL:${state.sessionCount}`)
  }

  if (state.priorities.length !== 1 || state.priorities[0] !== 'vera-02') {
    throw new Error(`INITIAL_PRIORITY_FAIL:${JSON.stringify(state.priorities)}`)
  }

  if (state.sidebarTab !== 'PROJECT') {
    throw new Error(`INITIAL_SIDEBAR_FAIL:${state.sidebarTab}`)
  }
}

function requirePriority(state: InteractionState, sessionId: string): void {
  if (state.priorities.length !== 1 || state.priorities[0] !== sessionId) {
    throw new Error(
      `PRIORITY_STATE_FAIL:${sessionId}:${JSON.stringify(state.priorities)}`
    )
  }

  const priorityWidth = state.widths[sessionId] ?? 0

  if (priorityWidth < 1180) {
    throw new Error(
      `PRIORITY_WIDTH_FAIL:${sessionId}:${priorityWidth}`
    )
  }

  for (const [id, width] of Object.entries(state.widths)) {
    if (id !== sessionId && width < 590) {
      throw new Error(`NORMAL_WIDTH_FAIL:${id}:${width}`)
    }
  }
}

export async function runInteractionProbe(
  window: BrowserWindow,
  evidenceRoot: string
): Promise<void> {
  mkdirSync(evidenceRoot, { recursive: true })

  console.log('INTERACTION_PROBE_MODE=ON')
  console.log(`INTERACTION_EVIDENCE_ROOT=${evidenceRoot}`)

  await waitForLoad(window)

  const initial = await waitForState(
    window,
    (state) => state.preloadBridge && state.sessionCount === 4,
    'INITIAL_BOOTSTRAP'
  )

  requireInitial(initial)

  console.log('INITIAL_PRELOAD_BRIDGE=PASS')
  console.log('INITIAL_SESSION_COUNT=4')
  console.log('INITIAL_PRIORITY=vera-02')
  console.log('INITIAL_SIDEBAR=PROJECT')

  await clickPrioritySession(window, 'vera-01')

  const afterPriorityClick = await waitForState(
    window,
    (state) =>
      state.priorities.length === 1 &&
      state.priorities[0] === 'vera-01' &&
      (state.widths['vera-01'] ?? 0) >= 1180,
    'PRIORITY_VERA_01'
  )

  requirePriority(afterPriorityClick, 'vera-01')

  console.log('PRIORITY_CLICK=PASS')
  console.log('PRIORITY_AFTER_CLICK=vera-01')
  console.log(`PRIORITY_WIDTH_AFTER_CLICK=${afterPriorityClick.widths['vera-01']}`)
  console.log(`VERA_02_WIDTH_AFTER_CLICK=${afterPriorityClick.widths['vera-02']}`)

  await clickSidebarTab(window, 'VCR')

  const afterSidebarClick = await waitForState(
    window,
    (state) => state.sidebarTab === 'VCR',
    'SIDEBAR_VCR'
  )

  console.log('SIDEBAR_CLICK=PASS')
  console.log(`SIDEBAR_AFTER_CLICK=${afterSidebarClick.sidebarTab}`)

  await delay(250)

  console.log('RELOAD_REQUESTED=YES')
  window.webContents.reload()
  await waitForLoad(window)

  const afterReload = await waitForState(
    window,
    (state) =>
      state.preloadBridge &&
      state.sessionCount === 4 &&
      state.priorities.length === 1 &&
      state.priorities[0] === 'vera-01' &&
      state.sidebarTab === 'VCR',
    'PERSISTED_RELOAD_STATE'
  )

  requirePriority(afterReload, 'vera-01')

  console.log('SQLITE_PRIORITY_PERSISTENCE=PASS')
  console.log('SQLITE_SIDEBAR_PERSISTENCE=PASS')
  console.log('PERSISTED_PRIORITY=vera-01')
  console.log('PERSISTED_SIDEBAR=VCR')

  const evidence = {
    initial,
    afterPriorityClick,
    afterSidebarClick,
    afterReload
  }

  const jsonPath = join(
    evidenceRoot,
    'interaction-probe.json'
  )

  writeFileSync(
    jsonPath,
    `${JSON.stringify(evidence, null, 2)}\n`,
    'utf-8'
  )

  const screenshot = await capture(window)
  const screenshotPath = join(
    evidenceRoot,
    'interaction-persisted-vcr.png'
  )

  writeFileSync(
    screenshotPath,
    screenshot.toPNG()
  )

  console.log(`INTERACTION_JSON=${jsonPath}`)
  console.log(`INTERACTION_SCREENSHOT=${screenshotPath}`)
  console.log('INTERACTION_SCREENSHOT=PASS')
  console.log('INTERACTION_STATE=PASS')
}
