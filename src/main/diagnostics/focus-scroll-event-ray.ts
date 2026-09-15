// VERTEX_SHELL_LIMITED_WIRING_000080V4B
// VERTEX_INCIDENT_MARKER_HOST_CONTEXT_REPAIR_000079V4E
import { app, webContents, type WebContents } from 'electron'
import '../shell/vertex-shell-host-bridge'
import * as fs from 'node:fs'
import * as path from 'node:path'

type RayRecord = {
  ts: string
  mono_ms: number
  type: string
  wc_id?: number
  wc_type?: string
  partition?: string
  url?: string
  title?: string
  payload?: unknown
}

type WcState = {
  lastHumanInputAt: number
  lastMutationAt: number
  lastBottomAt: number
  lastDistanceBottom: number | null
  compositionActive: boolean
  lastCompositionStartAt: number
  lastCompositionEndAt: number
  lastEnterAt: number
  lastSubmitAt: number
}

const EVENT_RAY_ENABLED = process.env.VERTEX_EVENT_RAY !== '0'
const FLUSH_INTERVAL_MS = 250
const MAX_QUEUE = 4000
const MAX_LOG_BYTES = 25 * 1024 * 1024
const HUMAN_OWNER_TTL_MS = 15_000
const BACKGROUND_MUTATION_FOCUS_WINDOW_MS = 2_500
const BACKLASH_WINDOW_MS = 1_500
const BACKLASH_DISTANCE_PX = 48
const NEAR_BOTTOM_PX = 8
const RECENT_HUMAN_SCROLL_MS = 350
const PAGE_PREFIX = '[VERTEX_EVENT_RAY]'

let started = false
let logPath = ''
let queue: string[] = []
let humanOwner: { wcId: number; at: number; source: string } | null = null
const attached = new Set<number>()
const stateByWc = new Map<number, WcState>()

function monoNow(): number {
  return Date.now()
}

function stateFor(wcId: number): WcState {
  let state = stateByWc.get(wcId)
  if (!state) {
    state = {
      lastHumanInputAt: 0,
      lastMutationAt: 0,
      lastBottomAt: 0,
      lastDistanceBottom: null,
      compositionActive: false,
      lastCompositionStartAt: 0,
      lastCompositionEndAt: 0,
      lastEnterAt: 0,
      lastSubmitAt: 0,
    }
    stateByWc.set(wcId, state)
  }
  return state
}

function safeMeta(wc?: WebContents): Partial<RayRecord> {
  if (!wc || wc.isDestroyed()) return {}
  const anyWc = wc as any
  let partition = ''
  let url = ''
  let title = ''
  let wcType = ''
  try { partition = String(anyWc.session?.getPartition?.() ?? '') } catch {}
  try { url = String(anyWc.getURL?.() ?? '') } catch {}
  try { title = String(anyWc.getTitle?.() ?? '') } catch {}
  try { wcType = String(anyWc.getType?.() ?? '') } catch {}
  return { wc_id: wc.id, wc_type: wcType, partition, url, title }
}

function rotateIfNeeded(): void {
  if (!logPath || !fs.existsSync(logPath)) return
  try {
    if (fs.statSync(logPath).size < MAX_LOG_BYTES) return
    for (let i = 3; i >= 1; i -= 1) {
      const src = `${logPath}.${i}`
      const dst = `${logPath}.${i + 1}`
      if (fs.existsSync(src)) {
        if (fs.existsSync(dst)) fs.unlinkSync(dst)
        fs.renameSync(src, dst)
      }
    }
    const first = `${logPath}.1`
    if (fs.existsSync(first)) fs.unlinkSync(first)
    fs.renameSync(logPath, first)
  } catch {}
}

function flush(): void {
  if (!logPath || queue.length === 0) return
  const batch = queue.splice(0, queue.length).join('\n') + '\n'
  try {
    rotateIfNeeded()
    fs.appendFileSync(logPath, batch, 'utf8')
  } catch {}
}

function emit(type: string, wc?: WebContents, payload?: unknown): void {
  if (!EVENT_RAY_ENABLED || !logPath) return
  const record: RayRecord = {
    ts: new Date().toISOString(),
    mono_ms: monoNow(),
    type,
    ...safeMeta(wc),
    ...(payload === undefined ? {} : { payload }),
  }
  queue.push(JSON.stringify(record))
  if (queue.length > MAX_QUEUE) queue.splice(0, queue.length - MAX_QUEUE)
}

function markHumanOwner(wc: WebContents, source: string): void {
  const at = monoNow()
  humanOwner = { wcId: wc.id, at, source }
  stateFor(wc.id).lastHumanInputAt = at
  emit('human_input_owner', wc, { source })
}

function freshHumanOwner(now: number): typeof humanOwner {
  if (!humanOwner) return null
  if (now - humanOwner.at > HUMAN_OWNER_TTL_MS) return null
  return humanOwner
}

function detectFocusCandidate(wc: WebContents, source: string): void {
  const now = monoNow()
  const owner = freshHumanOwner(now)
  const state = stateFor(wc.id)
  if (owner && owner.wcId !== wc.id) {
    emit('focus_authority_violation_candidate', wc, {
      focus_source: source,
      human_owner_wc_id: owner.wcId,
      human_owner_age_ms: now - owner.at,
      human_owner_source: owner.source,
      background_mutation_age_ms: state.lastMutationAt > 0 ? now - state.lastMutationAt : null,
      background_mutation_recent:
        state.lastMutationAt > 0 &&
        now - state.lastMutationAt <= BACKGROUND_MUTATION_FOCUS_WINDOW_MS,
    })
  }
}

function detectScrollBacklash(wc: WebContents, payload: Record<string, unknown>): void {
  const state = stateFor(wc.id)
  const now = monoNow()
  const rawDistance = payload.distanceBottom
  if (typeof rawDistance !== 'number' || !Number.isFinite(rawDistance)) return

  state.lastDistanceBottom = rawDistance

  if (rawDistance <= NEAR_BOTTOM_PX) {
    state.lastBottomAt = now
    emit('scroll_bottom_reached', wc, payload)
    return
  }

  const bottomAge = state.lastBottomAt > 0 ? now - state.lastBottomAt : Number.POSITIVE_INFINITY
  const inputAge = state.lastHumanInputAt > 0 ? now - state.lastHumanInputAt : Number.POSITIVE_INFINITY

  if (
    bottomAge <= BACKLASH_WINDOW_MS &&
    rawDistance >= BACKLASH_DISTANCE_PX &&
    inputAge > RECENT_HUMAN_SCROLL_MS
  ) {
    emit('scroll_backlash_candidate', wc, {
      ...payload,
      bottom_age_ms: bottomAge,
      human_input_age_ms: Number.isFinite(inputAge) ? inputAge : null,
    })
  }
}

function handlePageRecord(wc: WebContents, data: unknown): void {
  if (!data || typeof data !== 'object') return
  const item = data as Record<string, unknown>
  const eventType = typeof item.type === 'string' ? item.type : 'page_event'
  const payload =
    typeof item.payload === 'object' && item.payload !== null
      ? item.payload as Record<string, unknown>
      : {}

  const state = stateFor(wc.id)
  const now = monoNow()

  if (
    eventType === 'pointerdown' ||
    eventType === 'keydown' ||
    eventType === 'wheel' ||
    eventType === 'touchstart' ||
    eventType === 'beforeinput' ||
    eventType === 'compositionstart'
  ) {
    markHumanOwner(wc, `page:${eventType}`)
  }

  if (eventType === 'compositionstart') {
    state.compositionActive = true
    state.lastCompositionStartAt = now
  }

  if (eventType === 'compositionend') {
    state.compositionActive = false
    state.lastCompositionEndAt = now
  }

  if (eventType === 'keydown' && payload.keyClass === 'ENTER') {
    state.lastEnterAt = now
    if (payload.isComposing === true || state.compositionActive) {
      emit('ime_enter_during_composition', wc, {
        composition_active: state.compositionActive,
        page_is_composing: payload.isComposing === true,
        key_code_229: payload.keyCode === 229,
      })
    }
  }

  if (eventType === 'focusout' && state.compositionActive) {
    emit('ime_composition_focus_loss_candidate', wc, {
      composition_age_ms:
        state.lastCompositionStartAt > 0 ? now - state.lastCompositionStartAt : null,
      target: payload.target,
    })
  }

  if (eventType === 'submit') {
    state.lastSubmitAt = now
    const sinceCompositionEnd =
      state.lastCompositionEndAt > 0 ? now - state.lastCompositionEndAt : null
    const sinceEnter = state.lastEnterAt > 0 ? now - state.lastEnterAt : null

    if (
      state.compositionActive ||
      (sinceCompositionEnd !== null && sinceCompositionEnd <= 900) ||
      (payload.compositionActive === true)
    ) {
      emit('ime_submit_collision_candidate', wc, {
        composition_active: state.compositionActive,
        page_composition_active: payload.compositionActive === true,
        since_composition_end_ms: sinceCompositionEnd,
        since_enter_ms: sinceEnter,
        target: payload.target,
      })
    }
  }

  if (eventType === 'mutation') state.lastMutationAt = now
  if (eventType === 'focusin') detectFocusCandidate(wc, 'page:focusin')
  if (eventType === 'scroll') detectScrollBacklash(wc, payload)

  emit(`page:${eventType}`, wc, payload)
}

const injectedObserver = String.raw`
(() => {
  const FLAG = '__VERTEX_FOCUS_SCROLL_IME_SUBMIT_EVENT_RAY_V2__'
  if (window[FLAG]) return 'already-installed'
  window[FLAG] = true

  const PREFIX = '[VERTEX_EVENT_RAY]'
  let mutationTimer = 0
  let resizeTimer = 0
  let compositionActive = false
  let lastCompositionEndPerf = 0
  const scrollTimers = new WeakMap()

  const elementMeta = (node) => {
    if (!node || node === document) return { kind: 'document' }
    if (node === window) return { kind: 'window' }
    if (!(node instanceof Element)) return { kind: typeof node }
    return {
      kind: 'element',
      tag: node.tagName || null,
      id: node.id || null,
      role: node.getAttribute('role'),
      testid: node.getAttribute('data-testid'),
      inputType: node.getAttribute('type'),
    }
  }

  const activeMeta = () => elementMeta(document.activeElement)

  const emit = (type, payload = {}) => {
    try {
      console.debug(PREFIX + JSON.stringify({
        type,
        payload: {
          ...payload,
          documentHasFocus: document.hasFocus(),
          visibilityState: document.visibilityState,
          activeElement: activeMeta(),
          perfNow: performance.now(),
        },
      }))
    } catch {}
  }


  const INCIDENT_MARKER_ID = 'vertex-observability-human-incident-marker'

  const installIncidentMarker = () => {
    try {
      if (!document.body) return false
      if (document.getElementById(INCIDENT_MARKER_ID)) return true

      // Host Session Portal only. Do not inject this control into Vera/ChatGPT webcontents.
      if (window.__VERTEX_EVENT_RAY_HOST_PORTAL__ !== true) return false

      const button = document.createElement('button')
      button.id = INCIDENT_MARKER_ID
      button.type = 'button'
      button.textContent = 'MARK INCIDENT'
      button.title = 'Freeze recent Vertex observability evidence'
      button.setAttribute('aria-label', 'Mark incident')

      Object.assign(button.style, {
        position: 'fixed',
        right: '12px',
        bottom: '10px',
        zIndex: '2147483646',
        minHeight: '28px',
        padding: '5px 10px',
        borderRadius: '7px',
        border: '1px solid #26394B',
        background: '#111923',
        color: '#CBD5DF',
        fontSize: '11px',
        fontWeight: '650',
        letterSpacing: '0.04em',
        cursor: 'pointer',
        opacity: '0.78',
        boxShadow: '0 4px 18px rgba(0,0,0,0.28)',
      })

      button.addEventListener('mouseenter', () => { button.style.opacity = '1' })
      button.addEventListener('mouseleave', () => { button.style.opacity = '0.78' })
      button.addEventListener('click', () => {
        emit('human_incident_marker', {
          source: 'human_button',
          marker_id: INCIDENT_MARKER_ID,
        })
        const original = button.textContent
        button.textContent = 'MARKED'
        button.style.borderColor = '#F1B85B'
        window.setTimeout(() => {
          button.textContent = original || 'MARK INCIDENT'
          button.style.borderColor = '#26394B'
        }, 1400)
      })

      document.body.appendChild(button)
      emit('incident_marker_installed', { marker_id: INCIDENT_MARKER_ID })
      return true
    } catch {
      return false
    }
  }

  const scrollMetrics = (target) => {
    let el = null
    if (target === document || target === window) {
      el = document.scrollingElement || document.documentElement
    } else if (target instanceof Element) {
      el = target
    } else {
      el = document.scrollingElement || document.documentElement
    }
    if (!el) return null

    const scrollTop = Number(el.scrollTop || 0)
    const scrollHeight = Number(el.scrollHeight || 0)
    const clientHeight = Number(el.clientHeight || 0)
    return {
      scrollTop,
      scrollHeight,
      clientHeight,
      distanceBottom: Math.max(0, scrollHeight - clientHeight - scrollTop),
      target: elementMeta(el),
    }
  }

  const classifyKey = (event) => {
    if (event.key === 'Enter') return 'ENTER'
    if (event.key === 'Escape') return 'ESCAPE'
    if (event.key === 'Tab') return 'TAB'
    if (event.key === 'Backspace' || event.key === 'Delete') return 'EDIT'
    if (
      event.key === 'ArrowUp' ||
      event.key === 'ArrowDown' ||
      event.key === 'ArrowLeft' ||
      event.key === 'ArrowRight' ||
      event.key === 'Home' ||
      event.key === 'End' ||
      event.key === 'PageUp' ||
      event.key === 'PageDown'
    ) return 'NAVIGATION'
    if (
      event.key === 'Shift' ||
      event.key === 'Control' ||
      event.key === 'Alt' ||
      event.key === 'Meta'
    ) return 'MODIFIER'
    if (typeof event.key === 'string' && event.key.length === 1) return 'CHAR'
    return 'OTHER'
  }

  const dataLength = (data) =>
    typeof data === 'string' ? data.length : 0

  document.addEventListener('focusin', (event) => {
    emit('focusin', {
      target: elementMeta(event.target),
      compositionActive,
    })
  }, true)

  document.addEventListener('focusout', (event) => {
    emit('focusout', {
      target: elementMeta(event.target),
      compositionActive,
      sinceCompositionEndMs:
        lastCompositionEndPerf > 0 ? performance.now() - lastCompositionEndPerf : null,
    })
  }, true)

  document.addEventListener('pointerdown', (event) => {
    emit('pointerdown', { target: elementMeta(event.target), button: event.button })
  }, true)

  document.addEventListener('touchstart', (event) => {
    emit('touchstart', { target: elementMeta(event.target) })
  }, { capture: true, passive: true })

  document.addEventListener('wheel', (event) => {
    emit('wheel', {
      target: elementMeta(event.target),
      deltaX: event.deltaX,
      deltaY: event.deltaY,
    })
  }, { capture: true, passive: true })

  document.addEventListener('compositionstart', (event) => {
    compositionActive = true
    emit('compositionstart', {
      target: elementMeta(event.target),
      dataLength: dataLength(event.data),
    })
  }, true)

  document.addEventListener('compositionupdate', (event) => {
    emit('compositionupdate', {
      target: elementMeta(event.target),
      dataLength: dataLength(event.data),
      compositionActive,
    })
  }, true)

  document.addEventListener('compositionend', (event) => {
    compositionActive = false
    lastCompositionEndPerf = performance.now()
    emit('compositionend', {
      target: elementMeta(event.target),
      dataLength: dataLength(event.data),
    })
  }, true)

  document.addEventListener('beforeinput', (event) => {
    emit('beforeinput', {
      target: elementMeta(event.target),
      inputType: event.inputType || null,
      isComposing: event.isComposing === true,
      dataPresent: typeof event.data === 'string' && event.data.length > 0,
      dataLength: dataLength(event.data),
      compositionActive,
    })
  }, true)

  document.addEventListener('input', (event) => {
    emit('input', {
      target: elementMeta(event.target),
      inputType: event.inputType || null,
      isComposing: event.isComposing === true,
      dataPresent: typeof event.data === 'string' && event.data.length > 0,
      dataLength: dataLength(event.data),
      compositionActive,
    })
  }, true)

  document.addEventListener('keydown', (event) => {
    emit('keydown', {
      target: elementMeta(event.target),
      keyClass: classifyKey(event),
      isComposing: event.isComposing === true,
      keyCode: Number(event.keyCode || 0),
      ctrlKey: event.ctrlKey,
      altKey: event.altKey,
      shiftKey: event.shiftKey,
      metaKey: event.metaKey,
      compositionActive,
    })
  }, true)

  document.addEventListener('submit', (event) => {
    emit('submit', {
      target: elementMeta(event.target),
      defaultPrevented: event.defaultPrevented,
      compositionActive,
      sinceCompositionEndMs:
        lastCompositionEndPerf > 0 ? performance.now() - lastCompositionEndPerf : null,
    })
  }, true)

  document.addEventListener('click', (event) => {
    const target = event.target instanceof Element ? event.target.closest('button,[role="button"],input[type="submit"]') : null
    if (!target) return
    emit('button_click', {
      target: elementMeta(target),
      compositionActive,
      sinceCompositionEndMs:
        lastCompositionEndPerf > 0 ? performance.now() - lastCompositionEndPerf : null,
    })
  }, true)

  document.addEventListener('scroll', (event) => {
    const target = event.target === document ? document : event.target
    const key = target && typeof target === 'object' ? target : document
    const old = scrollTimers.get(key)
    if (old) clearTimeout(old)
    const timer = setTimeout(() => {
      const metrics = scrollMetrics(target)
      if (metrics) emit('scroll', metrics)
    }, 70)
    scrollTimers.set(key, timer)
  }, true)

  document.addEventListener('visibilitychange', () => emit('visibilitychange', {}), true)

  const mutationObserver = new MutationObserver((records) => {
    if (mutationTimer) clearTimeout(mutationTimer)
    mutationTimer = setTimeout(() => {
      emit('mutation', {
        recordCount: records.length,
        childListCount: records.filter((r) => r.type === 'childList').length,
        characterDataCount: records.filter((r) => r.type === 'characterData').length,
        attributeCount: records.filter((r) => r.type === 'attributes').length,
      })
      installIncidentMarker()
    }, 100)
  })

  const observeMutationRoot = () => {
    const root = document.body || document.documentElement
    if (!root) return
    mutationObserver.observe(root, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ['style', 'class', 'aria-expanded', 'aria-busy'],
    })
  }

  if (document.body || document.documentElement) observeMutationRoot()
  else document.addEventListener('DOMContentLoaded', observeMutationRoot, { once: true })

  const resizeObserver = new ResizeObserver((entries) => {
    if (resizeTimer) clearTimeout(resizeTimer)
    resizeTimer = setTimeout(() => {
      emit('resize', {
        entryCount: entries.length,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        documentScrollHeight:
          (document.scrollingElement || document.documentElement)?.scrollHeight || 0,
      })
    }, 100)
  })

  if (document.documentElement) resizeObserver.observe(document.documentElement)
  if (document.body) resizeObserver.observe(document.body)

  installIncidentMarker()

  emit('observer_installed', { hrefOrigin: location.origin, readyState: document.readyState })
  return 'installed'
})()
`

function isPortalHostWebContents(wc: WebContents): boolean {
  if (wc.isDestroyed()) return false
  try {
    return String((wc as any).getType?.() ?? '') === 'window'
  } catch {
    return false
  }
}

async function injectPageObserver(wc: WebContents, reason: string): Promise<void> {
  if (wc.isDestroyed()) return
  try {
    const hostPortal = isPortalHostWebContents(wc)
    const hostPrelude =
      `window.__VERTEX_EVENT_RAY_HOST_PORTAL__ = ${hostPortal ? 'true' : 'false'};\n`
    const result = await wc.executeJavaScript(hostPrelude + injectedObserver, true)
    emit('page_observer_injection', wc, { reason, result, hostPortal })
  } catch (error) {
    emit('page_observer_injection_failed', wc, {
      reason,
      error: error instanceof Error ? error.message : String(error),
    })
  }
}

function attach(wc: WebContents): void {
  if (!EVENT_RAY_ENABLED || wc.isDestroyed() || attached.has(wc.id)) return

  const wcAny = wc as any
  let type = ''
  try { type = String(wcAny.getType?.() ?? '') } catch {}
  if (type === 'devTools') return

  attached.add(wc.id)
  stateFor(wc.id)
  emit('webcontents_attached', wc)

  wcAny.on('focus', () => {
    emit('webcontents_focus', wc)
    detectFocusCandidate(wc, 'webcontents:focus')
  })

  wcAny.on('blur', () => emit('webcontents_blur', wc))

  wcAny.on('before-input-event', (_event: unknown, input: any) => {
    if (input?.type === 'keyDown') {
      markHumanOwner(wc, 'before-input-event:keyDown')
      const keyClass =
        input?.key === 'Enter' ? 'ENTER' :
        input?.key === 'Escape' ? 'ESCAPE' :
        input?.key === 'Tab' ? 'TAB' :
        typeof input?.key === 'string' && input.key.length === 1 ? 'CHAR' :
        'OTHER'
      emit('native_keydown_meta', wc, {
        keyClass,
        isAutoRepeat: input?.isAutoRepeat === true,
      })
    }
  })

  wcAny.on('did-start-loading', () => emit('did_start_loading', wc))
  wcAny.on('did-stop-loading', () => emit('did_stop_loading', wc))

  wcAny.on('dom-ready', () => {
    emit('dom_ready', wc)
    void injectPageObserver(wc, 'dom-ready')
  })

  wcAny.on('did-finish-load', () => {
    emit('did_finish_load', wc)
    void injectPageObserver(wc, 'did-finish-load')
  })

  wcAny.on('did-navigate', (_event: unknown, url: string) => {
    emit('did_navigate', wc, { url })
    void injectPageObserver(wc, 'did-navigate')
  })

  // Electron changed the console-message event shape across releases.
  // Accept both historical (event, level, message, ...) and newer
  // (event, details) contracts without binding the Ray to one Electron minor.
  wcAny.on('console-message', (...args: any[]) => {
    let message: unknown = null
    if (typeof args[2] === 'string') {
      message = args[2]
    } else if (args[1] && typeof args[1] === 'object' && typeof args[1].message === 'string') {
      message = args[1].message
    }

    if (typeof message !== 'string' || !message.startsWith(PAGE_PREFIX)) return
    try {
      handlePageRecord(wc, JSON.parse(message.slice(PAGE_PREFIX.length)))
    } catch {
      emit('page_record_parse_failed', wc, { sample: message.slice(0, 300) })
    }
  })

  wcAny.once('destroyed', () => {
    emit('webcontents_destroyed', wc)
    attached.delete(wc.id)
    stateByWc.delete(wc.id)
    if (humanOwner?.wcId === wc.id) humanOwner = null
  })

  void injectPageObserver(wc, 'attach')
}

function start(): void {
  if (started || !EVENT_RAY_ENABLED) return
  started = true

  const logDir = path.join(app.getPath('userData'), 'event-ray')
  fs.mkdirSync(logDir, { recursive: true })
  logPath = path.join(logDir, 'focus-scroll-event-ray.jsonl')

  emit('event_ray_started', undefined, {
    schema: 'vertex-session-portal/focus-scroll-event-ray-1',
    log_path: logPath,
    passive_observer: true,
    content_dom_scrape: false,
    focus_or_scroll_api_override: false,
  })

  for (const wc of webContents.getAllWebContents()) attach(wc)

  app.on('web-contents-created', (_event, contents) => attach(contents))

  const timer = setInterval(flush, FLUSH_INTERVAL_MS)
  timer.unref()

  app.on('before-quit', () => {
    emit('event_ray_stopping')
    flush()
  })

  console.log(`[VERTEX EVENT RAY] focus/scroll observer active: ${logPath}`)
}

if (EVENT_RAY_ENABLED) {
  void app.whenReady().then(start)
}
