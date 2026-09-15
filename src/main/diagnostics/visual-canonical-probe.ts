import type { BrowserWindow, NativeImage } from 'electron'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function waitForLoad(window: BrowserWindow): Promise<void> {
  if (!window.webContents.isLoading()) return

  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('VISUAL_000020_RENDERER_TIMEOUT')), 15000)
    window.webContents.once('did-finish-load', () => {
      clearTimeout(timeout)
      resolve()
    })
  })
}

async function capture(window: BrowserWindow): Promise<NativeImage> {
  window.webContents.setBackgroundThrottling(false)
  if (!window.isVisible()) window.showInactive()

  for (let attempt = 1; attempt <= 5; attempt += 1) {
    try {
      window.webContents.invalidate()
      await window.webContents.executeJavaScript(`
        new Promise((resolve) => {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => resolve('FRAME'))
          })
        })
      `, true)

      await delay(250)
      const image = await window.webContents.capturePage()
      if (!image.isEmpty()) {
        console.log(`VISUAL_000020_SCREENSHOT_ATTEMPT=${attempt} PASS`)
        return image
      }
    } catch {
      // retry screenshot only
    }
  }

  throw new Error('VISUAL_000020_SCREENSHOT_FAILED')
}

export async function runVisualCanonicalProbe(
  window: BrowserWindow,
  evidenceRoot: string
): Promise<void> {
  mkdirSync(evidenceRoot, { recursive: true })
  console.log('VISUAL_000020_PROBE_MODE=ON')
  await waitForLoad(window)
  await delay(800)

  const result = await window.webContents.executeJavaScript(`
    (() => {
      const frame = document.querySelector('vertex-main-frame')
      const root = frame && frame.shadowRoot ? frame.shadowRoot : null
      const sessions = root ? Array.from(root.querySelectorAll('vera-session')) : []
      const search = root ? root.querySelector('search-vera') : null
      const sessionRoots = sessions.map(session => session.shadowRoot).filter(Boolean)
      const searchRoot = search && search.shadowRoot ? search.shadowRoot : null
      const before = sessions.map(session => session.hasAttribute('priority'))

      const expandButtons =
        sessionRoots.filter(sroot => Boolean(sroot.querySelector('.expandButton'))).length +
        (searchRoot && searchRoot.querySelector('.expandButton') ? 1 : 0)

      const textAreas = [
        ...sessionRoots.map(sroot => sroot.querySelector('textarea')),
        searchRoot ? searchRoot.querySelector('textarea') : null
      ].filter(Boolean)

      const sendButtons = [
        ...sessionRoots.map(sroot => sroot.querySelector('.sendButton')),
        searchRoot ? searchRoot.querySelector('.sendButton') : null
      ].filter(Boolean).length

      const literalSend = [...sessionRoots, searchRoot]
        .filter(Boolean)
        .some(sroot => Array.from(sroot.querySelectorAll('button'))
          .some(button => button.textContent.trim().toUpperCase() === 'SEND'))

      if (sessions[0] && sessionRoots[0]) {
        sessionRoots[0].querySelector('.session')?.dispatchEvent(
          new MouseEvent('click', { bubbles: true, composed: true })
        )
      }

      const afterCardClick = sessions.map(session => session.hasAttribute('priority'))
      const resizeModes = textAreas.map(textarea => getComputedStyle(textarea).resize)

      return JSON.stringify({
        sessionCount: sessions.length,
        searchPresent: Boolean(search),
        expandButtons,
        sendButtons,
        literalSend,
        before,
        afterCardClick,
        resizeModes,
        topbarPresent: Boolean(root && root.querySelector('.commandSearch')),
        explorerPresent: Boolean(root && root.querySelector('vertex-explorer'))
      })
    })()
  `, true)

  if (typeof result !== 'string') throw new Error('VISUAL_000020_RESULT_NOT_STRING')

  const parsed = JSON.parse(result) as {
    sessionCount: number
    searchPresent: boolean
    expandButtons: number
    sendButtons: number
    literalSend: boolean
    before: boolean[]
    afterCardClick: boolean[]
    resizeModes: string[]
    topbarPresent: boolean
    explorerPresent: boolean
  }

  if (parsed.sessionCount !== 3 || !parsed.searchPresent) {
    throw new Error(`VISUAL_000020_SESSION_TOPOLOGY_FAIL:${result}`)
  }
  console.log('VISUAL_000020_SESSION_TOPOLOGY=PASS')

  if (parsed.expandButtons !== 4 || parsed.sendButtons !== 4) {
    throw new Error(`VISUAL_000020_COMPOSER_CONTROLS_FAIL:${result}`)
  }
  console.log('VISUAL_000020_EXPLICIT_EXPAND=PASS')

  if (parsed.literalSend) throw new Error('VISUAL_000020_LITERAL_SEND_STILL_PRESENT')
  console.log('VISUAL_000020_SEND_TEXT_REMOVED=PASS')

  if (JSON.stringify(parsed.before) !== JSON.stringify(parsed.afterCardClick)) {
    throw new Error(`VISUAL_000020_CARD_CLICK_CHANGED_PRIORITY:${result}`)
  }
  console.log('VISUAL_000020_CARD_CLICK_NO_EXPAND=PASS')

  if (parsed.resizeModes.some(mode => mode !== 'vertical')) {
    throw new Error(`VISUAL_000020_CHAT_RESIZE_FAIL:${result}`)
  }
  console.log('VISUAL_000020_CHAT_RESIZABLE=PASS')

  if (!parsed.topbarPresent || !parsed.explorerPresent) {
    throw new Error(`VISUAL_000020_FRAME_FAIL:${result}`)
  }
  console.log('VISUAL_000020_CANONICAL_FRAME=PASS')

  const screenshot = await capture(window)
  const screenshotPath = join(evidenceRoot, 'visual-canonical-sf.png')
  writeFileSync(screenshotPath, screenshot.toPNG())

  const jsonPath = join(evidenceRoot, 'visual-canonical-sf.json')
  writeFileSync(jsonPath, `${JSON.stringify(parsed, null, 2)}\n`, 'utf-8')

  console.log(`VISUAL_000020_SCREENSHOT=${screenshotPath}`)
  console.log(`VISUAL_000020_JSON=${jsonPath}`)
  console.log('VISUAL_000020_SCREENSHOT=PASS')
  console.log('VISUAL_000020_CORE=PASS')
}
