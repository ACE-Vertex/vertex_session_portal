import type {
  BrowserWindow,
  NativeImage
} from 'electron'
import {
  mkdirSync,
  writeFileSync
} from 'node:fs'
import {
  join
} from 'node:path'
import type {
  VirtualArdState
} from '../../shared/contracts'

interface UiProjection {
  sessionId: string
  role: string | null
  objective: string | null
}

interface UiState {
  preloadBridge: boolean
  sessionCount: number
  projections: UiProjection[]
}

function delay(
  ms: number
): Promise<void> {
  return new Promise(
    (resolve) =>
      setTimeout(
        resolve,
        ms
      )
  )
}

async function waitForLoad(
  window: BrowserWindow
): Promise<void> {
  if (
    !window.webContents
      .isLoading()
  ) {
    return
  }

  await new Promise<void>(
    (resolve, reject) => {
      const timeout =
        setTimeout(
          () =>
            reject(
              new Error(
                'VIRTUAL_ARD_RENDERER_LOAD_TIMEOUT'
              )
            ),
          15000
        )

      window.webContents
        .once(
          'did-finish-load',
          () => {
            clearTimeout(
              timeout
            )
            resolve()
          }
        )

      window.webContents
        .once(
          'did-fail-load',
          (
            _event,
            errorCode,
            errorDescription
          ) => {
            clearTimeout(
              timeout
            )

            reject(
              new Error(
                `VIRTUAL_ARD_RENDERER_LOAD_FAILED:${errorCode}:${errorDescription}`
              )
            )
          }
        )
    }
  )
}

async function executeJson<T>(
  window: BrowserWindow,
  script: string
): Promise<T> {
  const value =
    await window.webContents
      .executeJavaScript(
        script,
        true
      )

  if (
    typeof value !== 'string'
  ) {
    throw new Error(
      `VIRTUAL_ARD_NON_STRING_RESULT:${typeof value}`
    )
  }

  return JSON.parse(
    value
  ) as T
}

async function inspectUi(
  window: BrowserWindow
): Promise<UiState> {
  return executeJson<UiState>(
    window,
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

      return JSON.stringify({
        preloadBridge:
          typeof window.vertexPortal !==
            'undefined',
        sessionCount:
          sessions.length,
        projections:
          sessions
            .filter(
              (element) =>
                element.tagName
                  .toLowerCase() ===
                'vera-session'
            )
            .map(
              (element) => ({
                sessionId:
                  element.getAttribute(
                    'session-id'
                  ) || '',
                role:
                  element.getAttribute(
                    'session-role'
                  ),
                objective:
                  element.getAttribute(
                    'mission-objective'
                  )
              })
            )
      })
    })()
    `
  )
}

async function waitForUiProjection(
  window: BrowserWindow,
  objective: string
): Promise<UiState> {
  let last:
    UiState | null = null

  for (
    let attempt = 1;
    attempt <= 32;
    attempt += 1
  ) {
    last =
      await inspectUi(
        window
      )

    const byId =
      new Map(
        last.projections
          .map(
            (projection) => [
              projection.sessionId,
              projection
            ]
          )
      )

    const pass =
      last.preloadBridge &&
      last.sessionCount === 4 &&
      byId.get(
        'vera-01'
      )?.role ===
        'ARCHITECT' &&
      byId.get(
        'vera-02'
      )?.role ===
        'DEVELOPER' &&
      byId.get(
        'vera-03'
      )?.role ===
        'REVIEWER' &&
      last.projections
        .every(
          (projection) =>
            projection.objective ===
            objective
        )

    if (pass) {
      console.log(
        `WAIT_VIRTUAL_ARD_UI=PASS attempt=${attempt}`
      )

      return last
    }

    await delay(125)
  }

  throw new Error(
    `VIRTUAL_ARD_UI_TIMEOUT:${JSON.stringify(last)}`
  )
}

async function capture(
  window: BrowserWindow
): Promise<NativeImage> {
  window.webContents
    .setBackgroundThrottling(
      false
    )

  if (!window.isVisible()) {
    window.showInactive()
  }

  for (
    let attempt = 1;
    attempt <= 6;
    attempt += 1
  ) {
    try {
      window.webContents
        .invalidate()

      await window.webContents
        .executeJavaScript(
          `
          new Promise((resolve) => {
            requestAnimationFrame(() => {
              requestAnimationFrame(
                () => resolve(
                  'FRAME'
                )
              )
            })
          })
          `,
          true
        )

      await delay(250)

      const image =
        await window.webContents
          .capturePage()

      if (!image.isEmpty()) {
        console.log(
          `VIRTUAL_ARD_SCREENSHOT_ATTEMPT=${attempt} PASS`
        )

        return image
      }
    } catch {
      // retry only screenshot surface copy
    }

    await delay(250)
  }

  throw new Error(
    'VIRTUAL_ARD_SCREENSHOT_FAILED'
  )
}

function assertState(
  state: VirtualArdState
): void {
  if (
    state.projections.length !==
    3
  ) {
    throw new Error(
      `ARD_PROJECTION_COUNT_FAIL:${state.projections.length}`
    )
  }

  if (
    state.messages.length !== 3
  ) {
    throw new Error(
      `ARD_MESSAGE_COUNT_FAIL:${state.messages.length}`
    )
  }

  if (
    state.handoffs.length !== 2
  ) {
    throw new Error(
      `ARD_HANDOFF_COUNT_FAIL:${state.handoffs.length}`
    )
  }

  const roleBySession =
    new Map(
      state.projections
        .map(
          (item) => [
            item.sessionId,
            item.role
          ]
        )
    )

  if (
    roleBySession.get(
      'vera-01'
    ) !== 'ARCHITECT' ||
    roleBySession.get(
      'vera-02'
    ) !== 'DEVELOPER' ||
    roleBySession.get(
      'vera-03'
    ) !== 'REVIEWER'
  ) {
    throw new Error(
      'ARD_ROLE_PROJECTION_FAIL'
    )
  }

  const messagesBySession =
    new Map<string, number>()

  for (
    const message
    of state.messages
  ) {
    messagesBySession.set(
      message.sessionId,
      (
        messagesBySession.get(
          message.sessionId
        ) ?? 0
      ) + 1
    )
  }

  for (
    const sessionId of [
      'vera-01',
      'vera-02',
      'vera-03'
    ]
  ) {
    if (
      messagesBySession.get(
        sessionId
      ) !== 1
    ) {
      throw new Error(
        `ARD_CONTEXT_ISOLATION_FAIL:${sessionId}`
      )
    }
  }

  const first =
    state.handoffs[0]

  const second =
    state.handoffs[1]

  if (
    first.fromSessionId !==
      'vera-01' ||
    first.toSessionId !==
      'vera-02' ||
    first.kind !== 'PLAN'
  ) {
    throw new Error(
      'ARD_ARCHITECT_TO_DEVELOPER_HANDOFF_FAIL'
    )
  }

  if (
    second.fromSessionId !==
      'vera-02' ||
    second.toSessionId !==
      'vera-03' ||
    second.kind !==
      'IMPLEMENTATION'
  ) {
    throw new Error(
      'ARD_DEVELOPER_TO_REVIEWER_HANDOFF_FAIL'
    )
  }
}

export async function runVirtualArdProbe(
  window: BrowserWindow,
  evidenceRoot: string
): Promise<void> {
  mkdirSync(
    evidenceRoot,
    { recursive: true }
  )

  console.log(
    'VIRTUAL_ARD_PROBE_MODE=ON'
  )

  console.log(
    `VIRTUAL_ARD_EVIDENCE_ROOT=${evidenceRoot}`
  )

  await waitForLoad(window)

  const initial =
    await executeJson<{
      sessionCount: number
      virtualArd: null
    }>(
      window,
      `
      window.vertexPortal
        .bootstrap()
        .then((state) =>
          JSON.stringify({
            sessionCount:
              state.sessions.length,
            virtualArd:
              state.virtualArd
          })
        )
      `
    )

  if (
    initial.sessionCount !== 4 ||
    initial.virtualArd !== null
  ) {
    throw new Error(
      `VIRTUAL_ARD_INITIAL_STATE_FAIL:${JSON.stringify(initial)}`
    )
  }

  console.log(
    'VIRTUAL_ARD_INITIAL_SESSION_COUNT=4'
  )

  console.log(
    'VIRTUAL_ARD_INITIAL_MISSION=NONE'
  )

  const objective =
    'Complete VERTEX Session Portal with three independent Vera sessions and typed ARD handoffs.'

  const stateAfterProjection =
    await executeJson<VirtualArdState>(
      window,
      `
      window.vertexPortal
        .projectVirtualArd({
          objective:
            ${JSON.stringify(objective)},
          assignments: [
            {
              sessionId:
                'vera-01',
              role:
                'ARCHITECT',
              brief:
                'Define mission, boundaries and acceptance criteria.'
            },
            {
              sessionId:
                'vera-02',
              role:
                'DEVELOPER',
              brief:
                'Implement against the typed plan and preserve boundaries.'
            },
            {
              sessionId:
                'vera-03',
              role:
                'REVIEWER',
              brief:
                'Review implementation, Evidence and regression risk.'
            }
          ]
        })
        .then((state) =>
          JSON.stringify(state)
        )
      `
    )

  const missionId =
    stateAfterProjection
      .mission.id

  if (
    stateAfterProjection
      .projections.length !== 3
  ) {
    throw new Error(
      'VIRTUAL_ARD_PROJECTION_FAIL'
    )
  }

  console.log(
    'VIRTUAL_ARD_ROLE_PROJECTION=PASS'
  )

  await executeJson(
    window,
    `
    window.vertexPortal
      .appendSessionMessage({
        missionId:
          ${JSON.stringify(missionId)},
        sessionId:
          'vera-01',
        actor:
          'VERA',
        body:
          'Architect note: define the typed handoff contract before implementation.'
      })
      .then((message) =>
        JSON.stringify(message)
      )
    `
  )

  await executeJson(
    window,
    `
    window.vertexPortal
      .appendSessionMessage({
        missionId:
          ${JSON.stringify(missionId)},
        sessionId:
          'vera-02',
        actor:
          'VERA',
        body:
          'Developer note: implement only inside the assigned boundary.'
      })
      .then((message) =>
        JSON.stringify(message)
      )
    `
  )

  await executeJson(
    window,
    `
    window.vertexPortal
      .appendSessionMessage({
        missionId:
          ${JSON.stringify(missionId)},
        sessionId:
          'vera-03',
        actor:
          'VERA',
        body:
          'Reviewer note: accept only with Evidence and rollback safety.'
      })
      .then((message) =>
        JSON.stringify(message)
      )
    `
  )

  console.log(
    'VIRTUAL_ARD_INDEPENDENT_MESSAGES=3'
  )

  await executeJson(
    window,
    `
    window.vertexPortal
      .createVirtualArdHandoff({
        missionId:
          ${JSON.stringify(missionId)},
        fromSessionId:
          'vera-01',
        toSessionId:
          'vera-02',
        kind:
          'PLAN',
        body:
          'Typed plan: keep three independent Vera contexts and preserve Search Vera as a separate retrieval role.'
      })
      .then((handoff) =>
        JSON.stringify(handoff)
      )
    `
  )

  await executeJson(
    window,
    `
    window.vertexPortal
      .createVirtualArdHandoff({
        missionId:
          ${JSON.stringify(missionId)},
        fromSessionId:
          'vera-02',
        toSessionId:
          'vera-03',
        kind:
          'IMPLEMENTATION',
        body:
          'Implementation handoff: role projections, context ledgers and typed handoff persistence are installed.'
      })
      .then((handoff) =>
        JSON.stringify(handoff)
      )
    `
  )

  console.log(
    'VIRTUAL_ARD_TYPED_HANDOFFS=2'
  )

  const persisted =
    await executeJson<VirtualArdState>(
      window,
      `
      window.vertexPortal
        .getVirtualArdState(
          ${JSON.stringify(missionId)}
        )
        .then((state) =>
          JSON.stringify(state)
        )
      `
    )

  assertState(
    persisted
  )

  console.log(
    'VIRTUAL_ARD_CONTEXT_ISOLATION=PASS'
  )

  console.log(
    'VIRTUAL_ARD_HANDOFF_A_TO_D=PASS'
  )

  console.log(
    'VIRTUAL_ARD_HANDOFF_D_TO_R=PASS'
  )

  window.webContents.reload()

  await waitForLoad(window)

  const ui =
    await waitForUiProjection(
      window,
      objective
    )

  console.log(
    'VIRTUAL_ARD_UI_ROLE_PROJECTION=PASS'
  )

  const bootstrapAfterReload =
    await executeJson<{
      missionId: string | null
      projectionCount: number
      messageCount: number
      handoffCount: number
    }>(
      window,
      `
      window.vertexPortal
        .bootstrap()
        .then((state) =>
          JSON.stringify({
            missionId:
              state.virtualArd
                ? state.virtualArd.mission.id
                : null,
            projectionCount:
              state.virtualArd
                ? state.virtualArd.projections.length
                : 0,
            messageCount:
              state.virtualArd
                ? state.virtualArd.messages.length
                : 0,
            handoffCount:
              state.virtualArd
                ? state.virtualArd.handoffs.length
                : 0
          })
        )
      `
    )

  if (
    bootstrapAfterReload
      .missionId !== missionId ||
    bootstrapAfterReload
      .projectionCount !== 3 ||
    bootstrapAfterReload
      .messageCount !== 3 ||
    bootstrapAfterReload
      .handoffCount !== 2
  ) {
    throw new Error(
      `VIRTUAL_ARD_SQLITE_PERSISTENCE_FAIL:${JSON.stringify(bootstrapAfterReload)}`
    )
  }

  console.log(
    'VIRTUAL_ARD_SQLITE_PERSISTENCE=PASS'
  )

  const invalidSelfHandoffRejected =
    await executeJson<{
      rejected: boolean
    }>(
      window,
      `
      window.vertexPortal
        .createVirtualArdHandoff({
          missionId:
            ${JSON.stringify(missionId)},
          fromSessionId:
            'vera-01',
          toSessionId:
            'vera-01',
          kind:
            'NOTE',
          body:
            'self handoff should be rejected'
        })
        .then(
          () =>
            JSON.stringify({
              rejected:
                false
            })
        )
        .catch(
          () =>
            JSON.stringify({
              rejected:
                true
            })
        )
      `
    )

  if (
    !invalidSelfHandoffRejected
      .rejected
  ) {
    throw new Error(
      'VIRTUAL_ARD_SELF_HANDOFF_NOT_REJECTED'
    )
  }

  console.log(
    'VIRTUAL_ARD_SELF_HANDOFF_REJECTED=PASS'
  )

  const jsonPath =
    join(
      evidenceRoot,
      'virtual-ard-probe.json'
    )

  writeFileSync(
    jsonPath,
    `${JSON.stringify(
      {
        missionId,
        state:
          persisted,
        ui,
        bootstrapAfterReload
      },
      null,
      2
    )}\n`,
    'utf-8'
  )

  const screenshot =
    await capture(
      window
    )

  const screenshotPath =
    join(
      evidenceRoot,
      'virtual-ard-self-play.png'
    )

  writeFileSync(
    screenshotPath,
    screenshot.toPNG()
  )

  console.log(
    `VIRTUAL_ARD_JSON=${jsonPath}`
  )

  console.log(
    `VIRTUAL_ARD_SCREENSHOT=${screenshotPath}`
  )

  console.log(
    'VIRTUAL_ARD_SCREENSHOT=PASS'
  )

  console.log(
    'VIRTUAL_ARD_CORE=PASS'
  )
}
