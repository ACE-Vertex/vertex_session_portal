import type {
  BrowserWindow,
  NativeImage
} from 'electron'
import {
  mkdirSync,
  writeFileSync
} from 'node:fs'
import { join } from 'node:path'
import type {
  PortalControlCommand
} from '../../shared/contracts'
import {
  dispatchPortalControl
} from '../control/ui-control'

interface UiState {
  preloadBridge: boolean
  sessionCount: number
  priorities: string[]
  widths: Record<string, number>
  sidebarTab: string | null
  explorerDetail: string | null
}

interface StepEvidence {
  command: PortalControlCommand
  state: UiState
}

function delay(
  ms: number
): Promise<void> {
  return new Promise(
    (resolve) => setTimeout(
      resolve,
      ms
    )
  )
}

async function waitForLoad(
  window: BrowserWindow
): Promise<void> {
  if (!window.webContents.isLoading()) {
    return
  }

  await new Promise<void>(
    (resolve, reject) => {
      const timeout = setTimeout(
        () => reject(
          new Error(
            'UI_CONTROL_RENDERER_LOAD_TIMEOUT'
          )
        ),
        15000
      )

      window.webContents.once(
        'did-finish-load',
        () => {
          clearTimeout(timeout)
          resolve()
        }
      )

      window.webContents.once(
        'did-fail-load',
        (
          _event,
          errorCode,
          errorDescription
        ) => {
          clearTimeout(timeout)

          reject(
            new Error(
              `UI_CONTROL_RENDERER_LOAD_FAILED:${errorCode}:${errorDescription}`
            )
          )
        }
      )
    }
  )
}

async function inspect(
  window: BrowserWindow
): Promise<UiState> {
  const json =
    await window.webContents
      .executeJavaScript(
        `
        (() => {
          const frame =
            document.querySelector(
              'vertex-main-frame'
            )

          const root =
            frame && frame.shadowRoot
              ? frame.shadowRoot
              : null

          const sessions =
            root
              ? Array.from(
                  root.querySelectorAll(
                    'vera-session, search-vera'
                  )
                )
              : []

          const widths = {}
          const priorities = []

          for (const element of sessions) {
            const id =
              element.getAttribute(
                'session-id'
              ) || ''

            widths[id] =
              Math.round(
                element
                  .getBoundingClientRect()
                  .width
              )

            if (
              element.hasAttribute(
                'priority'
              )
            ) {
              priorities.push(id)
            }
          }

          const explorer =
            root
              ? root.querySelector(
                  'vertex-explorer'
                )
              : null

          const explorerRoot =
            explorer &&
            explorer.shadowRoot
              ? explorer.shadowRoot
              : null

          const activeButton =
            explorerRoot
              ? explorerRoot.querySelector(
                  '.tab[data-active="true"]'
                )
              : null

          const detail =
            explorerRoot
              ? explorerRoot.querySelector(
                  '.card'
                )
              : null

          return JSON.stringify({
            preloadBridge:
              typeof window.vertexPortal !==
              'undefined',
            sessionCount:
              sessions.length,
            priorities,
            widths,
            sidebarTab:
              activeButton
                ? activeButton.getAttribute(
                    'data-tab'
                  )
                : null,
            explorerDetail:
              detail
                ? detail.textContent
                : null
          })
        })()
        `,
        true
      ) as string

  return JSON.parse(
    json
  ) as UiState
}

async function waitForState(
  window: BrowserWindow,
  label: string,
  predicate: (
    state: UiState
  ) => boolean
): Promise<UiState> {
  let last: UiState | null =
    null

  for (
    let attempt = 1;
    attempt <= 32;
    attempt += 1
  ) {
    last = await inspect(window)

    if (predicate(last)) {
      console.log(
        `WAIT_${label}=PASS attempt=${attempt}`
      )

      return last
    }

    await delay(125)
  }

  throw new Error(
    `WAIT_${label}_TIMEOUT:${JSON.stringify(last)}`
  )
}

function send(
  window: BrowserWindow,
  command: PortalControlCommand
): void {
  const evidence =
    dispatchPortalControl(
      window,
      command
    )

  console.log(
    [
      'CONTROL_DISPATCH=PASS',
      `type=${evidence.type}`,
      `bytes=${evidence.serializedBytes}`
    ].join(' ')
  )
}

function requirePriority(
  state: UiState,
  sessionId: string
): void {
  if (
    state.priorities.length !== 1 ||
    state.priorities[0] !==
      sessionId
  ) {
    throw new Error(
      `CONTROL_PRIORITY_FAIL:${sessionId}:${JSON.stringify(state.priorities)}`
    )
  }

  const width =
    state.widths[sessionId] ?? 0

  if (width < 1180) {
    throw new Error(
      `CONTROL_PRIORITY_WIDTH_FAIL:${sessionId}:${width}`
    )
  }
}

async function waitPresentedFrame(
  window: BrowserWindow
): Promise<void> {
  window.webContents
    .setBackgroundThrottling(false)

  if (!window.isVisible()) {
    window.showInactive()
  }

  window.webContents.invalidate()

  await window.webContents
    .executeJavaScript(
      `
      new Promise((resolve) => {
        requestAnimationFrame(() => {
          requestAnimationFrame(
            () => resolve(
              'FRAME_PRESENTED'
            )
          )
        })
      })
      `,
      true
    )

  await delay(300)
}

async function capture(
  window: BrowserWindow
): Promise<NativeImage> {
  let lastError = ''

  for (
    let attempt = 1;
    attempt <= 6;
    attempt += 1
  ) {
    try {
      await waitPresentedFrame(
        window
      )

      const image =
        await window.webContents
          .capturePage()

      if (!image.isEmpty()) {
        console.log(
          `UI_CONTROL_SCREENSHOT_ATTEMPT=${attempt} PASS`
        )
        return image
      }

      lastError =
        'EMPTY_NATIVE_IMAGE'
    } catch (error) {
      lastError =
        error instanceof Error
          ? error.stack ??
            error.message
          : String(error)
    }

    await delay(250)
  }

  throw new Error(
    `UI_CONTROL_SCREENSHOT_FAILED:${lastError}`
  )
}

export async function runUiControlProbe(
  window: BrowserWindow,
  evidenceRoot: string
): Promise<void> {
  mkdirSync(
    evidenceRoot,
    { recursive: true }
  )

  console.log(
    'UI_CONTROL_PROBE_MODE=ON'
  )

  console.log(
    `UI_CONTROL_EVIDENCE_ROOT=${evidenceRoot}`
  )

  await waitForLoad(window)

  const initial =
    await waitForState(
      window,
      'UI_CONTROL_BOOTSTRAP',
      (state) =>
        state.preloadBridge &&
        state.sessionCount === 4
    )

  console.log(
    'UI_CONTROL_PRELOAD_BRIDGE=PASS'
  )
  console.log(
    'UI_CONTROL_SESSION_COUNT=4'
  )

  const steps: StepEvidence[] = []

  const focusCommand:
    PortalControlCommand = {
      type: 'SESSION_FOCUS',
      sessionId: 'vera-03'
    }

  send(
    window,
    focusCommand
  )

  const focused =
    await waitForState(
      window,
      'SESSION_FOCUS',
      (state) =>
        state.priorities.length === 1 &&
        state.priorities[0] ===
          'vera-03' &&
        (
          state.widths['vera-03'] ??
          0
        ) >= 1180
    )

  requirePriority(
    focused,
    'vera-03'
  )

  steps.push({
    command: focusCommand,
    state: focused
  })

  console.log(
    'CONTROL_SESSION_FOCUS=PASS'
  )

  const sidebarCommand:
    PortalControlCommand = {
      type: 'SIDEBAR_SWITCH',
      tab: 'VCA'
    }

  send(
    window,
    sidebarCommand
  )

  const sidebar =
    await waitForState(
      window,
      'SIDEBAR_SWITCH',
      (state) =>
        state.sidebarTab === 'VCA'
    )

  steps.push({
    command: sidebarCommand,
    state: sidebar
  })

  console.log(
    'CONTROL_SIDEBAR_SWITCH=PASS'
  )

  const vcrCommand:
    PortalControlCommand = {
      type: 'VCR_OPEN',
      key: 'VERTEX.VRA'
    }

  send(
    window,
    vcrCommand
  )

  const vcr =
    await waitForState(
      window,
      'VCR_OPEN',
      (state) =>
        state.sidebarTab === 'VCR' &&
        state.explorerDetail ===
          'Open canonical: VERTEX.VRA'
    )

  steps.push({
    command: vcrCommand,
    state: vcr
  })

  console.log(
    'CONTROL_VCR_OPEN=PASS'
  )

  const vcaCommand:
    PortalControlCommand = {
      type: 'VCA_SEARCH',
      query: '超絶採用'
    }

  send(
    window,
    vcaCommand
  )

  const vca =
    await waitForState(
      window,
      'VCA_SEARCH',
      (state) =>
        state.sidebarTab === 'VCA' &&
        state.explorerDetail ===
          'Search conversation: 超絶採用'
    )

  steps.push({
    command: vcaCommand,
    state: vca
  })

  console.log(
    'CONTROL_VCA_SEARCH=PASS'
  )

  const projectCommand:
    PortalControlCommand = {
      type: 'PROJECT_REVEAL',
      path: 'src/main/index.ts'
    }

  send(
    window,
    projectCommand
  )

  const project =
    await waitForState(
      window,
      'PROJECT_REVEAL',
      (state) =>
        state.sidebarTab ===
          'PROJECT' &&
        state.explorerDetail ===
          'Reveal: src/main/index.ts'
    )

  steps.push({
    command: projectCommand,
    state: project
  })

  console.log(
    'CONTROL_PROJECT_REVEAL=PASS'
  )

  const expandCommand:
    PortalControlCommand = {
      type: 'SESSION_EXPAND',
      sessionId: 'vera-search'
    }

  send(
    window,
    expandCommand
  )

  const expanded =
    await waitForState(
      window,
      'SESSION_EXPAND',
      (state) =>
        state.priorities.length === 1 &&
        state.priorities[0] ===
          'vera-search' &&
        (
          state.widths[
            'vera-search'
          ] ?? 0
        ) >= 1180
    )

  requirePriority(
    expanded,
    'vera-search'
  )

  steps.push({
    command: expandCommand,
    state: expanded
  })

  console.log(
    'CONTROL_SESSION_EXPAND=PASS'
  )

  await delay(200)

  console.log(
    'UI_CONTROL_RELOAD_REQUESTED=YES'
  )

  window.webContents.reload()

  await waitForLoad(window)

  const persisted =
    await waitForState(
      window,
      'UI_CONTROL_PERSISTENCE',
      (state) =>
        state.preloadBridge &&
        state.sessionCount === 4 &&
        state.priorities.length === 1 &&
        state.priorities[0] ===
          'vera-search' &&
        state.sidebarTab ===
          'PROJECT'
    )

  requirePriority(
    persisted,
    'vera-search'
  )

  console.log(
    'UI_CONTROL_SQLITE_PERSISTENCE=PASS'
  )

  console.log(
    'PERSISTED_CONTROL_PRIORITY=vera-search'
  )

  console.log(
    'PERSISTED_CONTROL_SIDEBAR=PROJECT'
  )

  const invalidRejected =
    (() => {
      try {
        dispatchPortalControl(
          window,
          {
            type:
              'SHELL_EXECUTE',
            command:
              'whoami'
          }
        )

        return false
      } catch {
        return true
      }
    })()

  if (!invalidRejected) {
    throw new Error(
      'INVALID_CONTROL_COMMAND_ACCEPTED'
    )
  }

  console.log(
    'CONTROL_UNKNOWN_COMMAND_REJECTED=PASS'
  )

  const evidence = {
    initial,
    steps,
    persisted,
    authorityBoundary: {
      visibleChatParsing:
        false,
      shellExecution:
        false,
      projectMutation:
        false,
      canonicalMutation:
        false,
      externalSend:
        false
    }
  }

  const jsonPath = join(
    evidenceRoot,
    'ui-control-probe.json'
  )

  writeFileSync(
    jsonPath,
    `${JSON.stringify(
      evidence,
      null,
      2
    )}\n`,
    'utf-8'
  )

  const screenshot =
    await capture(window)

  const screenshotPath = join(
    evidenceRoot,
    'ui-control-persisted.png'
  )

  writeFileSync(
    screenshotPath,
    screenshot.toPNG()
  )

  console.log(
    `UI_CONTROL_JSON=${jsonPath}`
  )

  console.log(
    `UI_CONTROL_SCREENSHOT=${screenshotPath}`
  )

  console.log(
    'UI_CONTROL_SCREENSHOT=PASS'
  )

  console.log(
    'UI_CONTROL_CHANNEL=PASS'
  )
}
