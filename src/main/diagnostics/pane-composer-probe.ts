import type { BrowserWindow } from 'electron'

function delay(ms: number): Promise<void> {
  return new Promise(
    resolve => setTimeout(resolve, ms)
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
              'PANE_COMPOSER_000024_RENDERER_TIMEOUT'
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
    }
  )
}

export async function runPaneComposerProbe(
  window: BrowserWindow
): Promise<void> {
  console.log(
    'PANE_COMPOSER_000024_PROBE_MODE=ON'
  )

  await waitForLoad(window)

  window.setSize(
    4200,
    1050,
    false
  )

  await delay(700)

  const result =
    await window.webContents
      .executeJavaScript(
        `
        (async () => {
          const sleep =
            (ms) =>
              new Promise(
                resolve =>
                  setTimeout(resolve, ms)
              )

          const frame =
            document.querySelector(
              'vertex-main-frame'
            )

          const root =
            frame && frame.shadowRoot
              ? frame.shadowRoot
              : null

          const hosts =
            root
              ? Array.from(
                  root.querySelectorAll(
                    'vera-session, search-vera'
                  )
                )
              : []

          const normalHosts =
            hosts.filter(
              host =>
                !host.hasAttribute(
                  'priority'
                )
            )

          const priorityHost =
            hosts.find(
              host =>
                host.hasAttribute(
                  'priority'
                )
            )

          const measureHost =
            (host) => ({
              id:
                host.getAttribute(
                  'session-id'
                ) || '',
              width:
                Math.round(
                  host.getBoundingClientRect()
                    .width
                ),
              minWidth:
                parseFloat(
                  getComputedStyle(host)
                    .minWidth
                ),
              priority:
                host.hasAttribute(
                  'priority'
                )
            })

          const initial =
            hosts.map(measureHost)

          const handles =
            hosts.map(
              host =>
                host.shadowRoot
                  ? host.shadowRoot
                      .querySelector(
                        '.resizeRail'
                      )
                  : null
            )

          const composers =
            hosts.map(
              host =>
                host.shadowRoot
                  ? host.shadowRoot
                      .querySelector(
                        '.composer'
                      )
                  : null
            )

          const textareas =
            hosts.map(
              host =>
                host.shadowRoot
                  ? host.shadowRoot
                      .querySelector(
                        'textarea'
                      )
                  : null
            )

          const composerHeightsBefore =
            composers.map(
              composer =>
                composer
                  ? Math.round(
                      composer
                        .getBoundingClientRect()
                        .height
                    )
                  : 0
            )

          for (
            const textarea
            of textareas
          ) {
            if (!textarea) continue

            textarea.value =
              Array
                .from(
                  { length: 20 },
                  (_, i) =>
                    'line-' + i
                )
                .join('\\n')

            textarea.dispatchEvent(
              new Event(
                'input',
                {
                  bubbles: true,
                  composed: true
                }
              )
            )
          }

          await sleep(80)

          const composerHeightsAfter =
            composers.map(
              composer =>
                composer
                  ? Math.round(
                      composer
                        .getBoundingClientRect()
                        .height
                    )
                  : 0
            )

          const textareaHeights =
            textareas.map(
              textarea =>
                textarea
                  ? Math.round(
                      textarea
                        .getBoundingClientRect()
                        .height
                    )
                  : 0
            )

          const firstNormal =
            normalHosts[0]

          if (firstNormal) {
            firstNormal.setAttribute(
              'manual-size',
              ''
            )

            firstNormal.style
              .setProperty(
                '--session-user-width',
                '850px'
              )
          }

          await sleep(80)

          const manual850 =
            firstNormal
              ? measureHost(
                  firstNormal
                )
              : null

          if (firstNormal) {
            firstNormal.style
              .setProperty(
                '--session-user-width',
                '420px'
              )
          }

          await sleep(80)

          const clamped600 =
            firstNormal
              ? measureHost(
                  firstNormal
                )
              : null

          if (firstNormal) {
            firstNormal.removeAttribute(
              'manual-size'
            )

            firstNormal.style
              .removeProperty(
                '--session-user-width'
              )
          }

          await sleep(80)

          const reset600 =
            firstNormal
              ? measureHost(
                  firstNormal
                )
              : null

          return JSON.stringify({
            hostCount:
              hosts.length,
            normalCount:
              normalHosts.length,
            initial,
            priority:
              priorityHost
                ? measureHost(
                    priorityHost
                  )
                : null,
            handleCount:
              handles.filter(Boolean)
                .length,
            composerHeightsBefore,
            composerHeightsAfter,
            textareaHeights,
            manual850,
            clamped600,
            reset600
          })
        })()
        `,
        true
      )

  if (
    typeof result !== 'string'
  ) {
    throw new Error(
      'PANE_COMPOSER_000024_RESULT_NOT_STRING'
    )
  }

  const state =
    JSON.parse(result) as {
      hostCount: number
      normalCount: number
      initial: Array<{
        id: string
        width: number
        minWidth: number
        priority: boolean
      }>
      priority:
        | {
            id: string
            width: number
            minWidth: number
            priority: boolean
          }
        | null
      handleCount: number
      composerHeightsBefore: number[]
      composerHeightsAfter: number[]
      textareaHeights: number[]
      manual850:
        | {
            width: number
            minWidth: number
          }
        | null
      clamped600:
        | {
            width: number
            minWidth: number
          }
        | null
      reset600:
        | {
            width: number
            minWidth: number
          }
        | null
    }

  if (
    state.hostCount !== 4 ||
    state.normalCount !== 3 ||
    !state.priority
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_TOPOLOGY_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_TOPOLOGY=PASS'
  )

  const normals =
    state.initial.filter(
      item => !item.priority
    )

  if (
    normals.some(
      item =>
        item.minWidth !== 600 ||
        item.width < 599 ||
        item.width > 602
    )
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_NORMAL_600_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_NORMAL_DEFAULT_600=PASS'
  )

  if (
    state.priority.minWidth !== 1200 ||
    state.priority.width < 1200
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_PRIORITY_1200_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_PRIORITY_MIN_1200=PASS'
  )

  if (
    state.handleCount !== 4
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_RESIZE_HANDLE_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_RESIZE_HANDLES=PASS'
  )

  if (
    !state.manual850 ||
    state.manual850.width < 848 ||
    state.manual850.width > 852
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_MANUAL_850_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_MANUAL_RESIZE=PASS'
  )

  if (
    !state.clamped600 ||
    state.clamped600.width < 599 ||
    state.clamped600.width > 602
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_CLAMP_600_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_MANUAL_CLAMP_600=PASS'
  )

  if (
    !state.reset600 ||
    state.reset600.width < 599 ||
    state.reset600.width > 602
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_RESET_600_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_RESIZE_RESET=PASS'
  )

  const allComposerHeights = [
    ...state.composerHeightsBefore,
    ...state.composerHeightsAfter
  ]

  if (
    allComposerHeights.some(
      height =>
        height <= 0 ||
        height > 115
    )
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_COMPOSER_CAP_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_COMPOSER_MAX_115=PASS'
  )

  if (
    state.textareaHeights.some(
      height =>
        height <= 0 ||
        height > 72
    )
  ) {
    throw new Error(
      `PANE_COMPOSER_000024_TEXTAREA_CAP_FAIL:${result}`
    )
  }

  console.log(
    'PANE_COMPOSER_000024_TEXTAREA_MAX_72=PASS'
  )

  console.log(
    `PANE_COMPOSER_000024_STATE=${result}`
  )

  console.log(
    'PANE_COMPOSER_000024_CORE=PASS'
  )
}
