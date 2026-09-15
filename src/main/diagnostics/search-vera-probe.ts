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
  RetrievalHit,
  SessionAgentTurn
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
              'SEARCH_VERA_RENDERER_LOAD_TIMEOUT'
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
              `SEARCH_VERA_RENDERER_LOAD_FAILED:${code}:${description}`
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
      `SEARCH_VERA_NON_STRING_RESULT:${typeof result}`
    )
  }

  return JSON.parse(result) as T
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
          `SEARCH_VERA_SCREENSHOT_ATTEMPT=${attempt} PASS`
        )
        return image
      }
    } catch {
      // screenshot-only retry
    }

    await delay(250)
  }

  throw new Error(
    'SEARCH_VERA_SCREENSHOT_FAILED'
  )
}

export async function runSearchVeraProbe(
  window: BrowserWindow,
  evidenceRoot: string
): Promise<void> {
  mkdirSync(
    evidenceRoot,
    { recursive: true }
  )

  console.log(
    'SEARCH_VERA_PROBE_MODE=ON'
  )

  await waitForLoad(window)

  const query =
    '三人寄れば文殊の知恵'

  const turn =
    await executeJson<SessionAgentTurn>(
      window,
      `
      window.vertexPortal
        .sendSessionMessage({
          sessionId:'vera-search',
          body:
            'Search the local project for the phrase ${query}. State which document contains it and include the token SEARCH_VERA_ONLINE_18S in your answer.'
        })
        .then((turn) =>
          JSON.stringify(turn)
        )
      `
    )

  if (
    turn.sessionId !==
      'vera-search'
  ) {
    throw new Error(
      'SEARCH_VERA_SESSION_ID_FAIL'
    )
  }

  if (
    !turn.assistant.body
      .includes(
        'SEARCH_VERA_ONLINE_18S'
      )
  ) {
    throw new Error(
      `SEARCH_VERA_LLM_TOKEN_MISSING:${turn.assistant.body}`
    )
  }

  console.log(
    'SEARCH_VERA_REAL_LLM=PASS'
  )

  if (
    turn.retrieval.length === 0
  ) {
    throw new Error(
      'SEARCH_VERA_NO_RETRIEVAL_HITS'
    )
  }

  const target =
    turn.retrieval.find(
      (hit) =>
        hit.source ===
          'PROJECT' &&
        hit.relativePath ===
          'docs/ARCHITECTURE/VIRTUAL_ARD_CORE_000016.md' &&
        hit.snippet.includes(
          '三人寄れば文殊の知恵'
        )
    )

  if (!target) {
    throw new Error(
      `SEARCH_VERA_CANONICAL_PROJECT_HIT_MISSING:${JSON.stringify(turn.retrieval)}`
    )
  }

  console.log(
    'SEARCH_VERA_PROJECT_RETRIEVAL=PASS'
  )

  console.log(
    `SEARCH_VERA_TARGET=${target.relativePath}:${target.lineStart}-${target.lineEnd}`
  )

  const persisted =
    await executeJson<RetrievalHit[]>(
      window,
      `
      window.vertexPortal
        .getSessionRetrieval(
          'vera-search'
        )
        .then((hits) =>
          JSON.stringify(hits)
        )
      `
    )

  if (
    persisted.length === 0 ||
    !persisted.some(
      (hit) =>
        hit.relativePath ===
          target.relativePath &&
        hit.lineStart ===
          target.lineStart
    )
  ) {
    throw new Error(
      'SEARCH_VERA_RETRIEVAL_PERSISTENCE_FAIL'
    )
  }

  console.log(
    'SEARCH_VERA_RETRIEVAL_PERSISTENCE=PASS'
  )

  window.webContents.reload()
  await waitForLoad(window)
  await delay(1000)

  const ui =
    await executeJson<{
      messageCount: number
      hitCount: number
      targetVisible: boolean
    }>(
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
        const search =
          root
            ? root.querySelector(
                'search-vera'
              )
            : null
        const sroot =
          search && search.shadowRoot
            ? search.shadowRoot
            : null

        const hitText =
          sroot
            ? Array.from(
                sroot.querySelectorAll(
                  '.hit'
                )
              )
              .map(
                (node) =>
                  node.textContent || ''
              )
              .join('\\n')
            : ''

        return JSON.stringify({
          messageCount:
            sroot
              ? sroot.querySelectorAll(
                  '.message'
                ).length
              : 0,
          hitCount:
            sroot
              ? sroot.querySelectorAll(
                  '.hit'
                ).length
              : 0,
          targetVisible:
            hitText.includes(
              'VIRTUAL_ARD_CORE_000016.md'
            )
        })
      })()
      `
    )

  if (
    ui.messageCount < 2 ||
    ui.hitCount < 1 ||
    !ui.targetVisible
  ) {
    throw new Error(
      `SEARCH_VERA_UI_FAIL:${JSON.stringify(ui)}`
    )
  }

  console.log(
    'SEARCH_VERA_UI=PASS'
  )

  const evidence = {
    query,
    turn,
    persisted,
    ui
  }

  const jsonPath =
    join(
      evidenceRoot,
      'search-vera-probe.json'
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
      'search-vera-local-retrieval.png'
    )

  writeFileSync(
    screenshotPath,
    screenshot.toPNG()
  )

  console.log(
    `SEARCH_VERA_JSON=${jsonPath}`
  )
  console.log(
    `SEARCH_VERA_SCREENSHOT=${screenshotPath}`
  )
  console.log(
    'SEARCH_VERA_SCREENSHOT=PASS'
  )
  console.log(
    'SEARCH_VERA_RETRIEVAL_CORE=PASS'
  )
}
