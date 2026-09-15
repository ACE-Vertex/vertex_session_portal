import type { BrowserWindow } from 'electron'

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function waitForLoad(window: BrowserWindow): Promise<void> {
  if (!window.webContents.isLoading()) return

  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error('RESPONSIVE_000022_RENDERER_TIMEOUT')),
      15000
    )

    window.webContents.once('did-finish-load', () => {
      clearTimeout(timeout)
      resolve()
    })
  })
}

async function inspect(window: BrowserWindow): Promise<{
  viewport: number
  viewportClientWidth: number
  viewportScrollWidth: number
  widths: Array<{
    id: string
    priority: boolean
    width: number
    minWidth: number
    flexGrow: number
    flexShrink: number
    flexBasis: string
  }>
}> {
  const result = await window.webContents.executeJavaScript(`
    (() => {
      const frame = document.querySelector('vertex-main-frame')
      const root = frame && frame.shadowRoot ? frame.shadowRoot : null
      const viewport = root ? root.querySelector('.sessionViewport') : null
      const hosts = root
        ? Array.from(root.querySelectorAll('vera-session, search-vera'))
        : []

      const widths = hosts.map(host => {
        const style = getComputedStyle(host)
        return {
          id: host.getAttribute('session-id') || '',
          priority: host.hasAttribute('priority'),
          width: Math.round(host.getBoundingClientRect().width),
          minWidth: parseFloat(style.minWidth),
          flexGrow: parseFloat(style.flexGrow),
          flexShrink: parseFloat(style.flexShrink),
          flexBasis: style.flexBasis
        }
      })

      return JSON.stringify({
        viewport: window.innerWidth,
        viewportClientWidth: viewport ? viewport.clientWidth : 0,
        viewportScrollWidth: viewport ? viewport.scrollWidth : 0,
        widths
      })
    })()
  `, true)

  if (typeof result !== 'string') {
    throw new Error('RESPONSIVE_000022_NON_STRING_RESULT')
  }

  return JSON.parse(result)
}

export async function runResponsiveSessionSizingProbe(
  window: BrowserWindow
): Promise<void> {
  console.log('RESPONSIVE_000022_PROBE_MODE=ON')

  await waitForLoad(window)
  await delay(600)

  window.setSize(4200, 1050, false)
  await delay(500)

  const wide = await inspect(window)
  const widePriority = wide.widths.find(item => item.priority)
  const wideNormals = wide.widths.filter(item => !item.priority)

  if (!widePriority || wideNormals.length !== 3) {
    throw new Error(`RESPONSIVE_000022_TOPOLOGY_FAIL:${JSON.stringify(wide)}`)
  }

  if (widePriority.minWidth !== 1200) {
    throw new Error(`RESPONSIVE_000022_PRIORITY_MIN_FAIL:${JSON.stringify(wide)}`)
  }

  if (wideNormals.some(item => item.minWidth !== 600)) {
    throw new Error(`RESPONSIVE_000022_NORMAL_MIN_FAIL:${JSON.stringify(wide)}`)
  }

  console.log('RESPONSIVE_000022_MINIMUM_CONTRACT=PASS')

  if (wideNormals.every(item => item.width <= 600)) {
    throw new Error(`RESPONSIVE_000022_NORMAL_NOT_GROWING:${JSON.stringify(wide)}`)
  }

  if (widePriority.width <= 1200) {
    throw new Error(`RESPONSIVE_000022_PRIORITY_NOT_GROWING:${JSON.stringify(wide)}`)
  }

  console.log('RESPONSIVE_000022_WIDE_GROWTH=PASS')

  if (wide.widths.some(item => item.flexGrow <= 0 || item.flexShrink <= 0)) {
    throw new Error(`RESPONSIVE_000022_FLEX_CONTRACT_FAIL:${JSON.stringify(wide)}`)
  }

  console.log('RESPONSIVE_000022_FLEX_CONTRACT=PASS')

  window.setSize(1900, 1000, false)
  await delay(500)

  const narrow = await inspect(window)
  const narrowPriority = narrow.widths.find(item => item.priority)
  const narrowNormals = narrow.widths.filter(item => !item.priority)

  if (!narrowPriority || narrowPriority.width < 1200) {
    throw new Error(`RESPONSIVE_000022_PRIORITY_CRUSHED:${JSON.stringify(narrow)}`)
  }

  if (narrowNormals.some(item => item.width < 600)) {
    throw new Error(`RESPONSIVE_000022_NORMAL_CRUSHED:${JSON.stringify(narrow)}`)
  }

  console.log('RESPONSIVE_000022_NO_CRUSH=PASS')

  if (narrow.viewportScrollWidth <= narrow.viewportClientWidth) {
    throw new Error(`RESPONSIVE_000022_EXPECTED_HORIZONTAL_SCROLL_MISSING:${JSON.stringify(narrow)}`)
  }

  console.log('RESPONSIVE_000022_NARROW_SCROLL=PASS')
  console.log(`RESPONSIVE_000022_WIDE_STATE=${JSON.stringify(wide)}`)
  console.log(`RESPONSIVE_000022_NARROW_STATE=${JSON.stringify(narrow)}`)
  console.log('RESPONSIVE_000022_CORE=PASS')
}
