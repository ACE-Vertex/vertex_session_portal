type DestinationState = {
  path: string
  isDefault: boolean
}

type DestinationChooseState = DestinationState & {
  canceled: boolean
}

type DestinationBridge = {
  get(): Promise<DestinationState>
  choose(): Promise<DestinationChooseState>
}

type LaneElement = HTMLElement & {
  shadowRoot: ShadowRoot | null
}

// Compatibility marker retained for publisher 000047: reload.insertAdjacentElement('afterend', button)
const PANEL_ATTR = 'data-vra-dispatch-destination-panel'
const STYLE_ATTR = 'data-vra-dispatch-destination-panel-style'
const observers = new WeakMap<ShadowRoot, MutationObserver>()

function api(): DestinationBridge | undefined {
  return (window as unknown as { vertexDispatchDestination?: DestinationBridge })
    .vertexDispatchDestination
}

function panelCss(): string {
  return `
    [${PANEL_ATTR}] {
      display: grid;
      gap: 8px;
      padding: 11px 12px 12px;
      border-bottom: 1px solid #1C2935;
      background:
        radial-gradient(circle at 90% 0%, rgba(58,184,255,.08), transparent 44%),
        linear-gradient(180deg, rgba(12,18,26,.98), rgba(7,11,16,.98));
    }
    [${PANEL_ATTR}] .vraDestinationHead { display:flex; align-items:center; justify-content:space-between; gap:10px; }
    [${PANEL_ATTR}] .vraDestinationTitle { color:#CBD5DF; font-size:10px; font-weight:850; letter-spacing:.03em; }
    [${PANEL_ATTR}] .vraDestinationScope { padding:2px 6px; border:1px solid rgba(85,214,158,.34); border-radius:999px; color:#55D69E; font-size:7px; font-weight:800; letter-spacing:.08em; }
    [${PANEL_ATTR}] .vraDestinationRow { display:grid; grid-template-columns:30px minmax(0,1fr) 30px; align-items:center; gap:6px; }
    [${PANEL_ATTR}] .vraDestinationIcon,
    [${PANEL_ATTR}] .vraDestinationBrowse { display:grid; place-items:center; width:30px; height:28px; padding:0; border:1px solid #26394B; border-radius:7px; background:#111923; color:#3AB8FF; font:inherit; }
    [${PANEL_ATTR}] .vraDestinationBrowse { cursor:pointer; transition:border-color 120ms ease, box-shadow 120ms ease, background 120ms ease; }
    [${PANEL_ATTR}] .vraDestinationBrowse:hover,
    [${PANEL_ATTR}] .vraDestinationBrowse:focus-visible { border-color:#3AB8FF; background:#14202C; box-shadow:0 0 14px rgba(22,140,255,.18); outline:none; }
    [${PANEL_ATTR}] .vraDestinationBrowse:disabled { cursor:default; opacity:.58; }
    [${PANEL_ATTR}] .vraDestinationPath { min-width:0; height:28px; display:flex; align-items:center; overflow:hidden; padding:0 9px; border:1px solid #1C2935; border-radius:7px; background:#070B10; color:#CBD5DF; text-overflow:ellipsis; white-space:nowrap; font-size:9px; box-shadow:inset 0 1px 0 rgba(255,255,255,.015); }
    [${PANEL_ATTR}] .vraDestinationHelp { color:#718195; font-size:7.5px; line-height:1.45; }
  `
}

function ensureStyle(root: ShadowRoot): void {
  if (root.querySelector(`style[${STYLE_ATTR}]`)) return
  const style = document.createElement('style')
  style.setAttribute(STYLE_ATTR, '')
  style.textContent = panelCss()
  root.appendChild(style)
}

function updatePanel(panel: HTMLElement, state: DestinationState): void {
  const path = panel.querySelector<HTMLElement>('.vraDestinationPath')
  if (path) {
    path.textContent = state.path
    path.title = state.path
  }
}

function watch(lane: LaneElement, root: ShadowRoot): void {
  if (observers.has(root)) return
  const observer = new MutationObserver(() => {
    if (!root.querySelector(`[${PANEL_ATTR}]`)) queueMicrotask(() => void install(lane))
  })
  observer.observe(root, { childList: true, subtree: true })
  observers.set(root, observer)
}

async function install(lane: LaneElement): Promise<void> {
  const root = lane.shadowRoot
  const bridge = api()
  if (!root || !bridge) return

  watch(lane, root)
  ensureStyle(root)
  root.querySelector('[data-vra-dispatch-destination-control]')?.remove()

  const existing = root.querySelector<HTMLElement>(`[${PANEL_ATTR}]`)
  if (existing) {
    try { updatePanel(existing, await bridge.get()) } catch {}
    return
  }

  const panel = document.createElement('section')
  panel.setAttribute(PANEL_ATTR, '')
  panel.innerHTML = `
    <div class="vraDestinationHead">
      <span class="vraDestinationTitle">VRA Save Path</span>
      <span class="vraDestinationScope">EXPORT</span>
    </div>
    <div class="vraDestinationRow">
      <span class="vraDestinationIcon" aria-hidden="true">▣</span>
      <div class="vraDestinationPath" title="Resolving export destination…">Resolving export destination…</div>
      <button class="vraDestinationBrowse" type="button" title="Choose VRA export folder" aria-label="Choose VRA export folder">…</button>
    </div>
    <div class="vraDestinationHelp">Human export destination only. Browser .vra downloads are captured into Portal staging and shown in Dispatch Bay first.</div>
  `

  const contract = root.querySelector('.contract')
  const queue = root.querySelector('.queue')
  if (contract) contract.insertAdjacentElement('afterend', panel)
  else if (queue) queue.insertAdjacentElement('beforebegin', panel)
  else root.querySelector('header')?.insertAdjacentElement('afterend', panel)

  const browse = panel.querySelector<HTMLButtonElement>('.vraDestinationBrowse')
  browse?.addEventListener('click', async () => {
    if (browse.dataset.busy === 'true') return
    browse.dataset.busy = 'true'
    browse.disabled = true
    try {
      const selected = await bridge.choose()
      if (!selected.canceled) updatePanel(panel, selected)
    } finally {
      browse.dataset.busy = 'false'
      browse.disabled = false
    }
  })

  try { updatePanel(panel, await bridge.get()) } catch {}
}

function scan(): void {
  document.querySelectorAll<LaneElement>('vertex-vra-dispatch-lane').forEach(lane => void install(lane))
}

const documentObserver = new MutationObserver(scan)
documentObserver.observe(document.documentElement, { childList: true, subtree: true })
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', scan, { once: true })
else scan()
