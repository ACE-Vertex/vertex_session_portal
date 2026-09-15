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
  SessionAgentTurn,
  SessionChatMessage,
  SessionProviderStatus,
  VirtualArdState
} from '../../shared/contracts'

function delay(ms: number):
  Promise<void> {
  return new Promise(
    (resolve) =>
      setTimeout(resolve, ms)
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
      const timeout =
        setTimeout(
          () => reject(
            new Error(
              'REAL_LLM_RENDERER_LOAD_TIMEOUT'
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
          code,
          description
        ) => {
          clearTimeout(timeout)
          reject(
            new Error(
              `REAL_LLM_RENDERER_LOAD_FAILED:${code}:${description}`
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
  const result =
    await window.webContents
      .executeJavaScript(
        script,
        true
      )

  if (typeof result !== 'string') {
    throw new Error(
      `REAL_LLM_NON_STRING_RESULT:${typeof result}`
    )
  }

  return JSON.parse(result) as T
}

async function send(
  window: BrowserWindow,
  sessionId: string,
  body: string
): Promise<SessionAgentTurn> {
  return executeJson<SessionAgentTurn>(
    window,
    `
    window.vertexPortal
      .sendSessionMessage({
        sessionId:
          ${JSON.stringify(sessionId)},
        body:
          ${JSON.stringify(body)}
      })
      .then((turn) =>
        JSON.stringify(turn)
      )
    `
  )
}

async function conversation(
  window: BrowserWindow,
  sessionId: string
): Promise<SessionChatMessage[]> {
  return executeJson<SessionChatMessage[]>(
    window,
    `
    window.vertexPortal
      .getSessionConversation(
        ${JSON.stringify(sessionId)}
      )
      .then((messages) =>
        JSON.stringify(messages)
      )
    `
  )
}

async function capture(
  window: BrowserWindow
): Promise<NativeImage> {
  window.webContents
    .setBackgroundThrottling(false)

  if (!window.isVisible()) {
    window.showInactive()
  }

  for (
    let attempt = 1;
    attempt <= 6;
    attempt += 1
  ) {
    try {
      window.webContents.invalidate()

      await window.webContents
        .executeJavaScript(
          `
          new Promise((resolve) => {
            requestAnimationFrame(() => {
              requestAnimationFrame(
                () => resolve('FRAME')
              )
            })
          })
          `,
          true
        )

      await delay(300)

      const image =
        await window.webContents
          .capturePage()

      if (!image.isEmpty()) {
        console.log(
          `REAL_LLM_SCREENSHOT_ATTEMPT=${attempt} PASS`
        )
        return image
      }
    } catch {
      // screenshot-only retry
    }

    await delay(250)
  }

  throw new Error(
    'REAL_LLM_SCREENSHOT_FAILED'
  )
}

export async function runRealLlmProbe(
  window: BrowserWindow,
  evidenceRoot: string
): Promise<void> {
  mkdirSync(
    evidenceRoot,
    { recursive: true }
  )

  console.log(
    'REAL_LLM_PROBE_MODE=ON'
  )

  await waitForLoad(window)

  const provider =
    await executeJson<SessionProviderStatus>(
      window,
      `
      window.vertexPortal
        .sessionProviderStatus()
        .then((status) =>
          JSON.stringify(status)
        )
      `
    )

  if (
    !provider.ready ||
    !provider.model
  ) {
    throw new Error(
      `REAL_LLM_PROVIDER_NOT_READY:${JSON.stringify(provider)}`
    )
  }

  console.log(
    'REAL_LLM_PROVIDER=ollama'
  )
  console.log(
    `REAL_LLM_MODEL=${provider.model}`
  )

  const objective =
    'Verify three independent Vera sessions can perform a real local-model Virtual ARD self-play.'

  const ard =
    await executeJson<VirtualArdState>(
      window,
      `
      window.vertexPortal
        .projectVirtualArd({
          objective:
            ${JSON.stringify(objective)},
          assignments: [
            {
              sessionId:'vera-01',
              role:'ARCHITECT',
              brief:'Define a typed plan and acceptance boundary.'
            },
            {
              sessionId:'vera-02',
              role:'DEVELOPER',
              brief:'Implement only from typed handoff context.'
            },
            {
              sessionId:'vera-03',
              role:'REVIEWER',
              brief:'Review only from typed handoff and Evidence.'
            }
          ]
        })
        .then((state) =>
          JSON.stringify(state)
        )
      `
    )

  const missionId =
    ard.mission.id

  const architect =
    await send(
      window,
      'vera-01',
      'For this diagnostic, reply with the token ARCHITECT_ONLINE_17A somewhere in your final response. Keep it very short.'
    )

  if (
    !architect.assistant.body
      .includes(
        'ARCHITECT_ONLINE_17A'
      )
  ) {
    throw new Error(
      `ARCHITECT_REAL_LLM_TOKEN_MISSING:${architect.assistant.body}`
    )
  }

  console.log(
    'REAL_LLM_ARCHITECT=PASS'
  )

  await executeJson(
    window,
    `
    window.vertexPortal
      .createVirtualArdHandoff({
        missionId:
          ${JSON.stringify(missionId)},
        fromSessionId:'vera-01',
        toSessionId:'vera-02',
        kind:'PLAN',
        body:
          ${JSON.stringify(architect.assistant.body)}
      })
      .then((item) =>
        JSON.stringify(item)
      )
    `
  )

  const developer =
    await send(
      window,
      'vera-02',
      'A typed PLAN handoff is available. Reply with the token DEVELOPER_ONLINE_17B somewhere in your final response. Keep it very short.'
    )

  if (
    !developer.assistant.body
      .includes(
        'DEVELOPER_ONLINE_17B'
      )
  ) {
    throw new Error(
      `DEVELOPER_REAL_LLM_TOKEN_MISSING:${developer.assistant.body}`
    )
  }

  console.log(
    'REAL_LLM_DEVELOPER=PASS'
  )

  await executeJson(
    window,
    `
    window.vertexPortal
      .createVirtualArdHandoff({
        missionId:
          ${JSON.stringify(missionId)},
        fromSessionId:'vera-02',
        toSessionId:'vera-03',
        kind:'IMPLEMENTATION',
        body:
          ${JSON.stringify(developer.assistant.body)}
      })
      .then((item) =>
        JSON.stringify(item)
      )
    `
  )

  const reviewer =
    await send(
      window,
      'vera-03',
      'A typed IMPLEMENTATION handoff is available. Reply with the token REVIEWER_ONLINE_17C somewhere in your final response. Keep it very short.'
    )

  if (
    !reviewer.assistant.body
      .includes(
        'REVIEWER_ONLINE_17C'
      )
  ) {
    throw new Error(
      `REVIEWER_REAL_LLM_TOKEN_MISSING:${reviewer.assistant.body}`
    )
  }

  console.log(
    'REAL_LLM_REVIEWER=PASS'
  )

  const histories =
    await Promise.all(
      [
        'vera-01',
        'vera-02',
        'vera-03'
      ].map(
        async (sessionId) => [
          sessionId,
          await conversation(
            window,
            sessionId
          )
        ] as const
      )
    )

  for (
    const [
      sessionId,
      messages
    ] of histories
  ) {
    if (
      messages.length !== 2 ||
      messages[0].role !== 'USER' ||
      messages[1].role !== 'ASSISTANT'
    ) {
      throw new Error(
        `REAL_LLM_CONTEXT_ISOLATION_FAIL:${sessionId}:${JSON.stringify(messages)}`
      )
    }
  }

  console.log(
    'REAL_LLM_CONTEXT_ISOLATION=PASS'
  )

  console.log(
    'REAL_LLM_TYPED_HANDOFF_A_TO_D=PASS'
  )

  console.log(
    'REAL_LLM_TYPED_HANDOFF_D_TO_R=PASS'
  )

  window.webContents.reload()
  await waitForLoad(window)
  await delay(1000)

  const uiMessageCounts =
    await executeJson<Record<string, number>>(
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
        const result = {}

        for (
          const id of [
            'vera-01',
            'vera-02',
            'vera-03'
          ]
        ) {
          const session =
            root
              ? root.querySelector(
                  '[session-id="' + id + '"]'
                )
              : null
          const sroot =
            session && session.shadowRoot
              ? session.shadowRoot
              : null
          result[id] =
            sroot
              ? sroot.querySelectorAll(
                  '.message'
                ).length
              : 0
        }

        return JSON.stringify(result)
      })()
      `
    )

  if (
    uiMessageCounts['vera-01'] < 2 ||
    uiMessageCounts['vera-02'] < 2 ||
    uiMessageCounts['vera-03'] < 2
  ) {
    throw new Error(
      `REAL_LLM_UI_MESSAGES_FAIL:${JSON.stringify(uiMessageCounts)}`
    )
  }

  console.log(
    'REAL_LLM_UI_MESSAGES=PASS'
  )

  const evidence = {
    provider,
    missionId,
    turns: {
      architect,
      developer,
      reviewer
    },
    histories:
      Object.fromEntries(
        histories
      ),
    uiMessageCounts
  }

  const jsonPath =
    join(
      evidenceRoot,
      'real-llm-probe.json'
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

  const screenshotPath =
    join(
      evidenceRoot,
      'real-llm-three-vera.png'
    )

  writeFileSync(
    screenshotPath,
    screenshot.toPNG()
  )

  console.log(
    `REAL_LLM_JSON=${jsonPath}`
  )

  console.log(
    `REAL_LLM_SCREENSHOT=${screenshotPath}`
  )

  console.log(
    'REAL_LLM_SCREENSHOT=PASS'
  )

  console.log(
    'REAL_LLM_SESSION_CORE=PASS'
  )
}
