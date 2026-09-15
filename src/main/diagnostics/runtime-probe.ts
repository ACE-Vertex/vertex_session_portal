import type { BrowserWindow, NativeImage } from 'electron'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

interface SessionProbe {
  tag: string
  id: string | null
  title: string | null
  priority: boolean
  width: number
  height: number
}

interface RendererProbe {
  title: string
  preloadBridge: boolean
  mainFrame: boolean
  explorer: boolean
  sessionCount: number
  mainVeraCount: number
  searchVeraCount: number
  priorityCount: number
  sessions: SessionProbe[]
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function inspectRenderer(window: BrowserWindow): Promise<RendererProbe> {
  const json = await window.webContents.executeJavaScript(
    `
    (() => {
      try {
        const frame = document.querySelector('vertex-main-frame')
        const root = frame && frame.shadowRoot ? frame.shadowRoot : null
        const nodes = root
          ? Array.from(root.querySelectorAll('vera-session, search-vera'))
          : []

        const sessions = nodes.map((element) => {
          const rect = element.getBoundingClientRect()

          return {
            tag: element.tagName.toLowerCase(),
            id: element.getAttribute('session-id'),
            title: element.getAttribute('session-title'),
            priority: element.hasAttribute('priority'),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
          }
        })

        return JSON.stringify({
          title: document.title,
          preloadBridge: typeof window.vertexPortal !== 'undefined',
          mainFrame: Boolean(frame),
          explorer: Boolean(root && root.querySelector('vertex-explorer')),
          sessionCount: sessions.length,
          mainVeraCount: sessions.filter((item) => item.tag === 'vera-session').length,
          searchVeraCount: sessions.filter((item) => item.tag === 'search-vera').length,
          priorityCount: sessions.filter((item) => item.priority).length,
          sessions
        })
      } catch (error) {
        return JSON.stringify({
          __probeError: String(error && error.stack ? error.stack : error)
        })
      }
    })()
    `,
    true
  ) as string

  if (typeof json !== 'string') {
    throw new Error(`RENDERER_PROBE_NON_STRING:${typeof json}`)
  }

  const parsed = JSON.parse(json) as RendererProbe & { __probeError?: string }

  if (parsed.__probeError) {
    throw new Error(`RENDERER_PROBE_SCRIPT_ERROR:${parsed.__probeError}`)
  }

  return parsed
}

async function waitForPresentedFrame(window: BrowserWindow): Promise<void> {
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

  await delay(350)
}

async function captureWithRetry(
  window: BrowserWindow,
  maxAttempts = 8
): Promise<NativeImage> {
  let lastError = ''

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      await waitForPresentedFrame(window)
      const image = await window.webContents.capturePage()

      if (!image.isEmpty()) {
        console.log(`SCREENSHOT_CAPTURE_ATTEMPT=${attempt} PASS`)
        return image
      }

      lastError = 'EMPTY_NATIVE_IMAGE'
      console.log(`SCREENSHOT_CAPTURE_ATTEMPT=${attempt} EMPTY`)
    } catch (error) {
      lastError =
        error instanceof Error ? error.stack ?? error.message : String(error)

      console.log(
        `SCREENSHOT_CAPTURE_ATTEMPT=${attempt} ERROR=${lastError.replace(/\s+/g, ' ')}`
      )
    }

    await delay(300 + attempt * 100)
  }

  throw new Error(`SCREENSHOT_CAPTURE_FAILED:${lastError}`)
}

export async function runRuntimeProbe(
  window: BrowserWindow,
  evidenceRoot: string
): Promise<void> {
  mkdirSync(evidenceRoot, { recursive: true })

  console.log('RUNTIME_PROBE_MODE=ON')
  console.log(`RUNTIME_PROBE_EVIDENCE_ROOT=${evidenceRoot}`)

  window.webContents.on('console-message', (_event, level, message) => {
    console.log(`RENDERER_CONSOLE level=${level} message=${message}`)
  })

  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error('RENDERER_LOAD_TIMEOUT')),
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
            `RENDERER_LOAD_FAILED:${errorCode}:${errorDescription}`
          )
        )
      }
    )
  })

  console.log('RENDERER_LOAD=PASS')

  let probe: RendererProbe | null = null
  let lastProbeError = ''

  for (let attempt = 1; attempt <= 32; attempt += 1) {
    try {
      probe = await inspectRenderer(window)

      console.log(
        `PROBE_ATTEMPT=${attempt} bridge=${probe.preloadBridge ? 'YES' : 'NO'} sessions=${probe.sessionCount}`
      )

      if (probe.preloadBridge && probe.sessionCount >= 4) {
        break
      }
    } catch (error) {
      lastProbeError =
        error instanceof Error ? error.stack ?? error.message : String(error)

      console.log(
        `PROBE_ATTEMPT=${attempt} ERROR=${lastProbeError.replace(/\s+/g, ' ')}`
      )
    }

    await delay(250)
  }

  if (!probe) {
    throw new Error(
      `RENDERER_PROBE_EMPTY${lastProbeError ? `:${lastProbeError}` : ''}`
    )
  }

  const jsonPath = join(evidenceRoot, 'runtime-probe.json')

  writeFileSync(
    jsonPath,
    `${JSON.stringify(probe, null, 2)}\n`,
    'utf-8'
  )

  console.log(`WINDOW_TITLE=${probe.title}`)
  console.log(`PRELOAD_BRIDGE=${probe.preloadBridge ? 'PASS' : 'FAIL'}`)
  console.log(`MAIN_FRAME=${probe.mainFrame ? 'PASS' : 'FAIL'}`)
  console.log(`EXPLORER=${probe.explorer ? 'PASS' : 'FAIL'}`)
  console.log(`SESSION_COUNT=${probe.sessionCount}`)
  console.log(`MAIN_VERA_COUNT=${probe.mainVeraCount}`)
  console.log(`SEARCH_VERA_COUNT=${probe.searchVeraCount}`)
  console.log(`PRIORITY_COUNT=${probe.priorityCount}`)

  for (const session of probe.sessions) {
    console.log(
      [
        'SESSION',
        `id=${session.id ?? ''}`,
        `tag=${session.tag}`,
        `priority=${session.priority ? 'YES' : 'NO'}`,
        `width=${session.width}`,
        `height=${session.height}`
      ].join(' ')
    )
  }

  console.log(`RUNTIME_JSON=${jsonPath}`)

  const normalSessions = probe.sessions.filter((session) => !session.priority)
  const prioritySessions = probe.sessions.filter((session) => session.priority)

  const normalWidthsPass =
    normalSessions.length === 3 &&
    normalSessions.every((session) => session.width >= 590)

  const priorityWidthPass =
    prioritySessions.length === 1 &&
    prioritySessions[0].width >= 1180

  const topologyPass =
    probe.preloadBridge &&
    probe.mainFrame &&
    probe.explorer &&
    probe.sessionCount === 4 &&
    probe.mainVeraCount === 3 &&
    probe.searchVeraCount === 1 &&
    probe.priorityCount === 1

  console.log(`NORMAL_WIDTHS=${normalWidthsPass ? 'PASS' : 'FAIL'}`)
  console.log(`PRIORITY_WIDTH=${priorityWidthPass ? 'PASS' : 'FAIL'}`)
  console.log(`SESSION_TOPOLOGY=${topologyPass ? 'PASS' : 'FAIL'}`)

  if (!probe.preloadBridge) {
    throw new Error('PRELOAD_BRIDGE_UNAVAILABLE')
  }

  if (!normalWidthsPass) {
    throw new Error('NORMAL_SESSION_WIDTH_BELOW_600_BASELINE')
  }

  if (!priorityWidthPass) {
    throw new Error('PRIORITY_SESSION_WIDTH_BELOW_1200_BASELINE')
  }

  if (!topologyPass) {
    throw new Error('SESSION_TOPOLOGY_MISMATCH')
  }

  console.log('RUNTIME_CORE=PASS')

  /*
   * H4 proved the runtime core is already healthy:
   * bridge=YES and sessions=4.
   *
   * Screenshot capture is a Chromium Viz surface-copy operation and can fail
   * with UnknownVizError when a never-shown BrowserWindow has not presented a
   * composited frame. Present the diagnostic window without stealing focus,
   * force a frame, and retry capture separately.
   */
  const screenshot = await captureWithRetry(window)
  const screenshotPath = join(evidenceRoot, 'session-portal-runtime.png')

  writeFileSync(screenshotPath, screenshot.toPNG())

  console.log(`SCREENSHOT=${screenshotPath}`)
  console.log('SCREENSHOT_EVIDENCE=PASS')
  console.log('RUNTIME_WINDOW=PASS')
}
