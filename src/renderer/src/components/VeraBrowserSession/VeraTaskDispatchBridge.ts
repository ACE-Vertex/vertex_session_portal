type ElectronWebviewElement = HTMLElement & {
  executeJavaScript: (code: string, userGesture?: boolean) => Promise<unknown>
}

type TaskEnvelope = {
  schema: 'vertex-task-dispatch/1'
  dispatch_id: string
  source_session: string
  delivery?: 'AUTO' | 'MANUAL'
  targets: Record<string, string>
  notes?: string
}

type SourceProbe = {
  raw: string | null
  busy: boolean
}

type VxsRequestEnvelope = {
  schema: 'vertex-vxs-request/1'
  request_id: string
  origin_session: string
  action: 'git.publish' | 'git.bootstrap'
  project_root: string
  message?: string
  remote_url?: string
}

type VxsRequestProbe = {
  raw: string | null
  busy: boolean
}

type PendingDelivery = {
  kind: 'TASK' | 'RESULT'
  dispatchId: string
  source: string
  target: string
  body: string
  queuedAt: number
  attempts: number
  lastReason: string
  resultSource?: string
  autoAuthorityId?: string
  resultStatus?: string
  resultFingerprint?: string
}

type ArdAutoAuthorityLease = {
  schema: 'vertex-session-portal/auto-authority-1'
  authority_id: string
  controller_session: string
  allowed_sessions: string[]
  granted_utc: string
  expires_utc: string
  status: 'ACTIVE' | 'REVOKED'
}

type ArdAutoTaskContext = {
  schema: 'vertex-session-portal/ard-task-context-1'
  authority_id: string
  parent_dispatch_id: string
  controller_session: string
  delegated_session: string
  activated_utc: string
}

type AwaitingResult = {
  dispatchId: string
  source: string
  target: string
  sentAt: number
}

type TaskResultEnvelope = {
  schema: 'vertex-task-result/1'
  dispatch_id: string
  source_session: string
  return_to: string
  status: 'DONE' | 'BLOCKED' | 'FAILED' | string
  message: string
}

type AutoVraArtifactEnvelope = {
  schema: 'vertex-vra-artifact/1'
  artifact_id: string
  filename: string
  source_session: string
  dispatch_id?: string
  auto_dispatch: true
}

type AutoVraArtifactProbe = {
  raws: string[]
  busy: boolean
}

const VALID_SESSIONS = new Set(['vera-01', 'vera-02', 'vera-03', 'vera-04', 'vera-05'])
const START = '[VERTEX_TASK_DISPATCH/1]'
const END = '[/VERTEX_TASK_DISPATCH/1]'
const RESULT_START = '[VERTEX_TASK_RESULT/1]'
const RESULT_END = '[/VERTEX_TASK_RESULT/1]'
const VRA_ARTIFACT_START = '[VERTEX_VRA_ARTIFACT/1]'
const VRA_ARTIFACT_END = '[/VERTEX_VRA_ARTIFACT/1]'
const VXS_REQUEST_START = '[VERTEX_VXS_REQUEST/1]'
const VXS_REQUEST_END = '[/VERTEX_VXS_REQUEST/1]'
const VXS_RESULT_START = '[VERTEX_VXS_RESULT/1]'
const VXS_RESULT_END = '[/VERTEX_VXS_RESULT/1]'
const RECEIPT_KEY = 'vertex.portal.task-dispatch.receipts.v1'
const RESULT_RECEIPT_KEY = 'vertex.portal.task-dispatch.result-receipts.v1'
const BLOCKED_RESULT_RECEIPT_KEY = 'vertex.portal.task-dispatch.blocked-result-receipts.v1'
const AUTO_VRA_RECEIPT_KEY = 'vertex.portal.ard-auto-vra-receipts.v1'
const AUTO_AUTHORITY_KEY = 'vertex.portal.ard-auto-authority.v1'
const AUTO_TASK_CONTEXT_KEY = 'vertex.portal.ard-auto-task-context.v1'
const AUTO_AUTHORITY_CHANGED_EVENT = 'vertex-ard-auto-authority-changed'
const AUTO_AUTHORITY_COMMAND_PREFIX = 'vertex-auto-authority:'
const VXS_REQUEST_COMMAND_PREFIX = 'vertex-vxs-request:'
const VXS_REQUEST_RECEIPT_KEY = 'vertex.portal.vxs-request.receipts.v1'
const POLL_MS = 900
const STABLE_POLLS_REQUIRED = 2

// AUTO is a Human Gate, not a durable unattended privilege.
// Renderer reload/restart always requires a fresh Human AUTO arm.
try {
  localStorage.removeItem(AUTO_AUTHORITY_KEY)
  localStorage.removeItem(AUTO_TASK_CONTEXT_KEY)
} catch {
  // Main process independently revokes ACTIVE authority on process restart.
}

const armedSources = new Set<string>()
const armBaseline = new Map<string, string>()
const probeStable = new Map<string, { dispatchId: string; count: number }>()
const deliveryQueues = new Map<string, PendingDelivery[]>()
const processingTargets = new Set<string>()
const awaitingResults = new Map<string, AwaitingResult>()
const autoVraBaselines = new Map<string, Set<string>>()
const vxsRequestBaselines = new Map<string, string>()
const vxsRequestStable = new Map<string, { requestId: string; count: number }>()
let autoVraScanInFlight = false
let autoTimer: number | null = null
let deliveryTimer: number | null = null
let resultTimer: number | null = null

function sid(value: string | null | undefined): string {
  return (value ?? '').trim().toLowerCase()
}

function loadAutoAuthorities(): ArdAutoAuthorityLease[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(AUTO_AUTHORITY_KEY) ?? '[]') as unknown
    if (!Array.isArray(parsed)) return []
    const now = Date.now()
    return parsed.filter((row): row is ArdAutoAuthorityLease => {
      if (!row || typeof row !== 'object') return false
      const lease = row as Partial<ArdAutoAuthorityLease>
      return lease.schema === 'vertex-session-portal/auto-authority-1'
        && typeof lease.authority_id === 'string'
        && typeof lease.controller_session === 'string'
        && Array.isArray(lease.allowed_sessions)
        && typeof lease.granted_utc === 'string'
        && typeof lease.expires_utc === 'string'
        && lease.status === 'ACTIVE'
        && Number.isFinite(Date.parse(lease.expires_utc))
        && Date.parse(lease.expires_utc) > now
    })
  } catch {
    return []
  }
}

function saveAutoAuthorities(leases: ArdAutoAuthorityLease[]): void {
  try {
    localStorage.setItem(AUTO_AUTHORITY_KEY, JSON.stringify(leases.filter(row => row.status === 'ACTIVE')))
  } catch {
    // Trusted main-process authority remains canonical; local state is routing convenience only.
  }
  window.dispatchEvent(new CustomEvent(AUTO_AUTHORITY_CHANGED_EVENT))
}

function authorityForController(source: string): ArdAutoAuthorityLease | null {
  const matches = loadAutoAuthorities().filter(row => sid(row.controller_session) === source)
  return matches.length === 1 ? matches[0] : null
}

function authorityForSession(source: string): ArdAutoAuthorityLease | null {
  const matches = loadAutoAuthorities().filter(row =>
    row.allowed_sessions.map(sid).includes(source)
  )
  const self = matches.filter(row => sid(row.controller_session) === source)
  if (self.length === 1) return self[0]
  if (self.length > 1) return null
  return matches.length === 1 ? matches[0] : null
}

function loadStringSet(key: string): Set<string> {
  try {
    const parsed = JSON.parse(localStorage.getItem(key) ?? '[]')
    return new Set(Array.isArray(parsed) ? parsed.filter(item => typeof item === 'string') : [])
  } catch {
    return new Set()
  }
}

function saveStringSet(key: string, set: Set<string>, limit: number): void {
  try {
    localStorage.setItem(key, JSON.stringify(Array.from(set).slice(-limit)))
  } catch {
    // Main authority and immutable Capture remain canonical.
  }
}

function stringFingerprint(value: string): string {
  let hash = 2166136261
  for (let i = 0; i < value.length; i += 1) {
    hash ^= value.charCodeAt(i)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(16).padStart(8, '0')
}

function blockedResultFingerprint(result: TaskResultEnvelope): string {
  return [
    result.dispatch_id,
    sid(result.source_session),
    result.status,
    stringFingerprint(result.message),
  ].join('::')
}

function autoVraLogicalKey(env: AutoVraArtifactEnvelope): string {
  return [
    sid(env.source_session),
    env.dispatch_id ?? '',
    env.artifact_id,
    env.filename,
  ].join('::')
}

function loadAutoTaskContexts(): Record<string, ArdAutoTaskContext> {
  try {
    const parsed = JSON.parse(localStorage.getItem(AUTO_TASK_CONTEXT_KEY) ?? '{}') as unknown
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed as Record<string, ArdAutoTaskContext>
      : {}
  } catch {
    return {}
  }
}

function saveAutoTaskContexts(value: Record<string, ArdAutoTaskContext>): void {
  try {
    localStorage.setItem(AUTO_TASK_CONTEXT_KEY, JSON.stringify(value))
  } catch {
    // Main-process authority still fail-closes actual VRA dispatch.
  }
  window.dispatchEvent(new CustomEvent(AUTO_AUTHORITY_CHANGED_EVENT))
}

function setAutoTaskContext(
  delegatedSession: string,
  controllerSession: string,
  dispatchId: string,
  authorityId: string
): void {
  const contexts = loadAutoTaskContexts()
  contexts[delegatedSession] = {
    schema: 'vertex-session-portal/ard-task-context-1',
    authority_id: authorityId,
    parent_dispatch_id: dispatchId,
    controller_session: controllerSession,
    delegated_session: delegatedSession,
    activated_utc: new Date().toISOString(),
  }
  saveAutoTaskContexts(contexts)
}

function clearAutoTaskContext(delegatedSession: string, dispatchId?: string): void {
  const contexts = loadAutoTaskContexts()
  const current = contexts[delegatedSession]
  if (!current) return
  if (dispatchId && current.parent_dispatch_id !== dispatchId) return
  delete contexts[delegatedSession]
  saveAutoTaskContexts(contexts)
}

function clearContextsForAuthority(authorityId: string): void {
  const contexts = loadAutoTaskContexts()
  let changed = false
  for (const [session, context] of Object.entries(contexts)) {
    if (context?.authority_id !== authorityId) continue
    delete contexts[session]
    changed = true
  }
  if (changed) saveAutoTaskContexts(contexts)
}

async function grantAutoAuthority(source: string): Promise<ArdAutoAuthorityLease> {
  const authorityId = crypto.randomUUID()
  const payload = encodeURIComponent(JSON.stringify({
    authority_id: authorityId,
    controller_session: source,
    allowed_sessions: Array.from(VALID_SESSIONS).sort(),
  }))
  const raw = await window.vertexPortal.exportVraCard(
    `${AUTO_AUTHORITY_COMMAND_PREFIX}grant:${payload}`
  )
  const lease = JSON.parse(raw) as ArdAutoAuthorityLease
  if (
    lease.schema !== 'vertex-session-portal/auto-authority-1'
    || lease.authority_id !== authorityId
    || sid(lease.controller_session) !== source
    || lease.status !== 'ACTIVE'
  ) throw new Error('ARD_AUTO_AUTHORITY_GRANT_INVALID')

  const remaining = loadAutoAuthorities()
    .filter(row => sid(row.controller_session) !== source && row.authority_id !== lease.authority_id)
  remaining.push(lease)
  saveAutoAuthorities(remaining)
  return lease
}

async function revokeAutoAuthority(source: string): Promise<void> {
  const lease = authorityForController(source)
  if (!lease) return
  await window.vertexPortal.exportVraCard(
    `${AUTO_AUTHORITY_COMMAND_PREFIX}revoke:${encodeURIComponent(lease.authority_id)}`
  )
  saveAutoAuthorities(loadAutoAuthorities().filter(row => row.authority_id !== lease.authority_id))
  clearContextsForAuthority(lease.authority_id)
}

function loadReceipts(): Set<string> {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECEIPT_KEY) ?? '[]')
    return new Set(Array.isArray(parsed) ? parsed.filter(item => typeof item === 'string') : [])
  } catch {
    return new Set()
  }
}

function saveReceipts(set: Set<string>): void {
  try {
    localStorage.setItem(RECEIPT_KEY, JSON.stringify(Array.from(set).slice(-512)))
  } catch {
    // Durable receipts are best-effort; inflight guards still stop duplicate concurrent sends.
  }
}

function receiptKey(dispatchId: string, target: string): string {
  return `${dispatchId}::${target}`
}

function loadResultReceipts(): Set<string> {
  try {
    const parsed = JSON.parse(localStorage.getItem(RESULT_RECEIPT_KEY) ?? '[]')
    return new Set(Array.isArray(parsed) ? parsed.filter(item => typeof item === 'string') : [])
  } catch {
    return new Set()
  }
}

function saveResultReceipts(set: Set<string>): void {
  try {
    localStorage.setItem(RESULT_RECEIPT_KEY, JSON.stringify(Array.from(set).slice(-512)))
  } catch {
    // Best effort. In-memory awaiting/queue guards still prevent duplicate live delivery.
  }
}

function resultKey(dispatchId: string, target: string): string {
  return `${dispatchId}::${target}`
}

function parseEnvelope(raw: string, source: string): TaskEnvelope {
  const data = JSON.parse(raw) as TaskEnvelope
  if (data.schema !== 'vertex-task-dispatch/1') throw new Error('TASK_SCHEMA_UNSUPPORTED')
  if (!data.dispatch_id || data.dispatch_id.trim().length < 8) throw new Error('TASK_DISPATCH_ID_INVALID')
  if (sid(data.source_session) !== source) throw new Error('TASK_SOURCE_SESSION_MISMATCH')
  if (data.delivery && !['AUTO', 'MANUAL'].includes(data.delivery)) throw new Error('TASK_DELIVERY_INVALID')

  const rows = Object.entries(data.targets ?? {})
  if (rows.length < 1 || rows.length > 4) throw new Error('TASK_TARGET_COUNT_INVALID')

  for (const [targetRaw, task] of rows) {
    const target = sid(targetRaw)
    if (!VALID_SESSIONS.has(target)) throw new Error(`TASK_TARGET_INVALID:${targetRaw}`)
    if (target === source) throw new Error('TASK_SELF_DISPATCH_FORBIDDEN')
    if (typeof task !== 'string' || !task.trim()) throw new Error(`TASK_BODY_EMPTY:${target}`)
    if (task.length > 16000) throw new Error(`TASK_BODY_TOO_LARGE:${target}`)
  }

  return data
}

function parseVxsRequestEnvelope(raw: string, source: string): VxsRequestEnvelope {
  const data = JSON.parse(raw) as VxsRequestEnvelope
  if (data.schema !== 'vertex-vxs-request/1') throw new Error('VXS_REQUEST_SCHEMA_UNSUPPORTED')
  if (!/^[A-Za-z0-9._:-]{8,160}$/.test(String(data.request_id ?? ''))) {
    throw new Error('VXS_REQUEST_ID_INVALID')
  }
  if (sid(data.origin_session) !== source) throw new Error('VXS_REQUEST_ORIGIN_MISMATCH')
  if (data.action !== 'git.publish' && data.action !== 'git.bootstrap') {
    throw new Error('VXS_REQUEST_ACTION_FORBIDDEN')
  }
  if (typeof data.project_root !== 'string' || !data.project_root.trim() || data.project_root.length > 512) {
    throw new Error('VXS_REQUEST_PROJECT_ROOT_INVALID')
  }

  if (data.action === 'git.publish') {
    if (typeof data.message !== 'string' || !data.message.trim()) throw new Error('VXS_REQUEST_MESSAGE_REQUIRED')
    if (data.message.length > 240 || /[\r\n]/.test(data.message)) {
      throw new Error('VXS_REQUEST_MESSAGE_INVALID')
    }
    if (data.remote_url !== undefined) throw new Error('VXS_REQUEST_REMOTE_URL_FORBIDDEN')
    return {
      ...data,
      origin_session: source,
      project_root: data.project_root.trim(),
      message: data.message.trim(),
    }
  }

  if (typeof data.remote_url !== 'string' || !/^https:\/\/github\.com\/[^/\s]+\/[^/\s]+(?:\.git)?$/i.test(data.remote_url.trim())) {
    throw new Error('VXS_REQUEST_REMOTE_URL_INVALID')
  }
  if (data.message !== undefined) throw new Error('VXS_REQUEST_MESSAGE_FORBIDDEN')

  return {
    ...data,
    origin_session: source,
    project_root: data.project_root.trim(),
    remote_url: data.remote_url.trim(),
  }
}

function panes(): HTMLElement[] {
  const frame = document.querySelector('vertex-main-frame') as HTMLElement | null
  return Array.from(frame?.shadowRoot?.querySelectorAll<HTMLElement>('vera-browser-session') ?? [])
}

function paneFor(sessionId: string): HTMLElement | null {
  return panes().find(pane => sid(pane.getAttribute('session-id')) === sessionId) ?? null
}

function webview(pane: HTMLElement): ElectronWebviewElement | null {
  return pane.shadowRoot?.querySelector('webview') as ElectronWebviewElement | null
}

function probeScript(): string {
  return `(() => {
    const START=${JSON.stringify(START)};
    const END=${JSON.stringify(END)};
    const busy=Boolean(
      document.querySelector('[data-testid="stop-button"]')
      || document.querySelector('button[aria-label*="Stop generating"]')
      || document.querySelector('button[aria-label*="停止"]')
    );
    const nodes=[...document.querySelectorAll('[data-message-author-role="assistant"], article')];
    for(let i=nodes.length-1;i>=0;i--){
      const text=(nodes[i].innerText||nodes[i].textContent||'').trim();
      const a=text.lastIndexOf(START), b=text.lastIndexOf(END);
      if(a>=0 && b>a){
        return {raw:text.slice(a+START.length,b).trim(),busy};
      }
    }
    return {raw:null,busy};
  })()`
}

function vxsRequestProbeScript(): string {
  return `(() => {
    const START=${JSON.stringify(VXS_REQUEST_START)};
    const END=${JSON.stringify(VXS_REQUEST_END)};
    const busy=Boolean(
      document.querySelector('[data-testid="stop-button"]')
      || document.querySelector('button[aria-label*="Stop generating"]')
      || document.querySelector('button[aria-label*="停止"]')
    );
    const nodes=[...document.querySelectorAll('[data-message-author-role="assistant"], article')];
    for(let i=nodes.length-1;i>=0;i--){
      const text=(nodes[i].innerText||nodes[i].textContent||'').trim();
      const a=text.lastIndexOf(START), b=text.lastIndexOf(END);
      if(a>=0 && b>a){
        return {raw:text.slice(a+START.length,b).trim(),busy};
      }
    }
    return {raw:null,busy};
  })()`
}

function targetReadinessScript(stagedMarker: string): string {
  return `(() => {
    const marker=${JSON.stringify(stagedMarker)};
    const busy=Boolean(
      document.querySelector('[data-testid="stop-button"]')
      ||document.querySelector('button[aria-label*="Stop generating"]')
      ||document.querySelector('button[aria-label*="Stop"]')
      ||document.querySelector('button[aria-label*="停止"]')
    );
    if(busy) return {ready:false,reason:'TARGET_BUSY_GENERATING'};

    const composer=
      document.querySelector('#prompt-textarea')
      ||document.querySelector('textarea[data-testid="prompt-textarea"]')
      ||document.querySelector('textarea')
      ||document.querySelector('[contenteditable="true"][data-virtualkeyboard="true"]')
      ||document.querySelector('[contenteditable="true"]');

    if(!composer) return {ready:false,reason:'TARGET_COMPOSER_NOT_FOUND'};

    if(
      composer.disabled===true
      ||composer.getAttribute('aria-disabled')==='true'
      ||composer.getAttribute('contenteditable')==='false'
    ){
      return {ready:false,reason:'TARGET_COMPOSER_DISABLED'};
    }

    const current=(
      composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement
        ? composer.value
        : (composer.textContent||'')
    ).trim();

    if(current && !current.includes(marker)){
      return {ready:false,reason:'TARGET_COMPOSER_OCCUPIED'};
    }

    return {
      ready:true,
      reason:current.includes(marker) ? 'TARGET_READY_STAGED' : 'TARGET_READY_EMPTY'
    };
  })()`
}

async function targetReadiness(target: string, stagedMarker: string): Promise<{
  ready: boolean
  reason: string
}> {
  const pane = paneFor(target)
  const view = pane ? webview(pane) : null
  if (!view) return { ready: false, reason: 'TARGET_WEBVIEW_NOT_READY' }

  try {
    const result = await view.executeJavaScript(
      targetReadinessScript(stagedMarker),
      false
    ) as { ready?: boolean; reason?: string } | null

    return {
      ready: Boolean(result?.ready),
      reason: result?.reason ?? 'TARGET_READINESS_UNKNOWN',
    }
  } catch {
    return { ready: false, reason: 'TARGET_READINESS_PROBE_FAILED' }
  }
}

function sendMessageScript(body: string, stagedMarker: string): string {
  return `(async () => {
    const text=${JSON.stringify(body)};
    const marker=${JSON.stringify(stagedMarker)};

    const busy=Boolean(
      document.querySelector('[data-testid="stop-button"]')
      ||document.querySelector('button[aria-label*="Stop generating"]')
      ||document.querySelector('button[aria-label*="Stop"]')
      ||document.querySelector('button[aria-label*="停止"]')
    );
    if(busy) return {ok:false,reason:'TARGET_BUSY_GENERATING'};

    const composer=
      document.querySelector('#prompt-textarea')
      ||document.querySelector('textarea[data-testid="prompt-textarea"]')
      ||document.querySelector('textarea')
      ||document.querySelector('[contenteditable="true"][data-virtualkeyboard="true"]')
      ||document.querySelector('[contenteditable="true"]');

    if(!composer) return {ok:false,reason:'TARGET_COMPOSER_NOT_FOUND'};
    if(
      composer.disabled===true
      ||composer.getAttribute('aria-disabled')==='true'
      ||composer.getAttribute('contenteditable')==='false'
    ){
      return {ok:false,reason:'TARGET_COMPOSER_DISABLED'};
    }

    composer.focus();

    const existing=(
      composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement
        ? composer.value
        : (composer.textContent||'')
    );

    if(existing.trim() && !existing.includes(marker)){
      return {ok:false,reason:'TARGET_COMPOSER_OCCUPIED'};
    }

    // Retry safe: if the same delivery is already staged, do not duplicate it.
    if(!existing.includes(marker)){
      if(composer instanceof HTMLTextAreaElement || composer instanceof HTMLInputElement){
        const proto=composer instanceof HTMLTextAreaElement
          ? HTMLTextAreaElement.prototype
          : HTMLInputElement.prototype;
        const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;
        if(setter) setter.call(composer,text); else composer.value=text;
        composer.dispatchEvent(new Event('input',{bubbles:true}));
        composer.dispatchEvent(new Event('change',{bubbles:true}));
      } else {
        composer.textContent=text;
        composer.dispatchEvent(new InputEvent('input',{
          bubbles:true,inputType:'insertText',data:text
        }));
      }
    }

    const delay=(ms)=>new Promise(resolve=>setTimeout(resolve,ms));
    const visible=(node)=>{
      if(!node) return false;
      const style=getComputedStyle(node);
      const rect=node.getBoundingClientRect();
      return style.display!=='none'
        && style.visibility!=='hidden'
        && rect.width>0
        && rect.height>0;
    };

    const findSend=()=>{
      const roots=[];
      const form=composer.closest('form');
      if(form) roots.push(form);
      roots.push(document);

      const selectors=[
        '[data-testid="send-button"]',
        'button[data-testid*="send"]',
        'button[type="submit"]',
        'button[aria-label*="Send"]',
        'button[aria-label*="send"]',
        'button[aria-label*="送信"]'
      ];

      for(const root of roots){
        for(const selector of selectors){
          for(const button of root.querySelectorAll(selector)){
            if(
              button instanceof HTMLButtonElement
              && !button.disabled
              && button.getAttribute('aria-disabled')!=='true'
              && visible(button)
            ){
              return {button,selector};
            }
          }
        }
      }

      if(form){
        for(const button of form.querySelectorAll('button[type="submit"]')){
          if(
            button instanceof HTMLButtonElement
            && !button.disabled
            && button.getAttribute('aria-disabled')!=='true'
            && visible(button)
          ){
            return {button,selector:'form button[type="submit"]'};
          }
        }
      }
      return null;
    };

    await delay(80);

    for(let attempt=0; attempt<40; attempt+=1){
      const becameBusy=Boolean(
        document.querySelector('[data-testid="stop-button"]')
        ||document.querySelector('button[aria-label*="Stop generating"]')
        ||document.querySelector('button[aria-label*="Stop"]')
        ||document.querySelector('button[aria-label*="停止"]')
      );
      if(becameBusy) return {ok:false,reason:'TARGET_BUSY_GENERATING'};

      const found=findSend();
      if(found){
        found.button.click();
        await delay(140);
        return {
          ok:true,
          reason:'SEND_COMMIT_CLICKED',
          selector:found.selector,
          attempts:attempt+1
        };
      }
      await delay(75);
    }

    return {
      ok:false,
      reason:'TARGET_SEND_CONTROL_TIMEOUT',
      waited_ms:3080
    };
  })()`
}

function buildTaskBody(
  task: string,
  source: string,
  target: string,
  dispatchId: string,
  autoAuthorityId: string | null = null
): string {
  return [
    '[VERTEX TASK DISPATCH]',
    `dispatch_id=${dispatchId}`,
    `origin_session=${source}`,
    `target_session=${target}`,
    ...(autoAuthorityId
      ? [
          'ard_mode=AUTO_DELEGATED',
          `parent_task_id=${dispatchId}`,
          'auto_vra_dispatch=ENABLED',
          'human_gate=AUTO_AUTHORITY',
        ]
      : []),
    '',
    task,
    '',
    ...(autoAuthorityId
      ? [
          '[VERTEX AUTO VRA HANDOFF CONTRACT]',
          'このTaskでVRAを生成した場合、VRAファイルリンクと同じassistant回答内に次のEnvelopeを必ず1個だけ出してください。',
          'filenameは実際に生成した.vraファイル名、artifact_idはmanifestのartifact_id、source_sessionは自分、dispatch_idはこのTaskのdispatch_idを使用します。',
          'HumanへVRAリンクのクリックや発注クリックを要求しないでください。Session PortalがAUTO authority下でCaptureし、既存Human-approved publication transactionへ渡します。',
          VRA_ARTIFACT_START,
          JSON.stringify({
            schema: 'vertex-vra-artifact/1',
            artifact_id: '実際のartifact_id',
            filename: '実際のfilename.vra',
            source_session: target,
            dispatch_id: dispatchId,
            auto_dispatch: true,
          }),
          VRA_ARTIFACT_END,
          '',
        ]
      : []),
    '[VERTEX RETURN CONTRACT]',
    'このTaskの処理が完了したら、回答の最後に必ず次の形式の結果ブロックを1個だけ付けてください。',
    'status は DONE / BLOCKED / FAILED のいずれか。message には発信元VERAが把握すべき結果を簡潔に記載してください。',
    RESULT_START,
    JSON.stringify({
      schema: 'vertex-task-result/1',
      dispatch_id: dispatchId,
      source_session: target,
      return_to: source,
      status: 'DONE',
      message: 'ここを実際の結果に置き換える'
    }),
    RESULT_END,
  ].join('\n')
}

function buildResultReturnBody(result: TaskResultEnvelope): string {
  return [
    '[VERTEX TASK RESULT RETURN]',
    `dispatch_id=${result.dispatch_id}`,
    `from=${sid(result.source_session)}`,
    `status=${result.status}`,
    '',
    result.message,
  ].join('\n')
}

function resultProbeScript(dispatchId: string): string {
  return `(() => {
    const START=${JSON.stringify('[VERTEX_TASK_RESULT/1]')};
    const END=${JSON.stringify('[/VERTEX_TASK_RESULT/1]')};
    const DISPATCH=${JSON.stringify(dispatchId)};

    const busy=Boolean(
      document.querySelector('[data-testid="stop-button"]')
      ||document.querySelector('button[aria-label*="Stop generating"]')
      ||document.querySelector('button[aria-label*="Stop"]')
      ||document.querySelector('button[aria-label*="停止"]')
    );
    if(busy) return {raw:null,busy:true};

    const nodes=[...document.querySelectorAll('[data-message-author-role="assistant"], article')];
    for(let i=nodes.length-1;i>=0;i--){
      const text=(nodes[i].innerText||nodes[i].textContent||'').trim();
      if(!text.includes(DISPATCH)) continue;
      const a=text.lastIndexOf(START), b=text.lastIndexOf(END);
      if(a>=0 && b>a){
        return {raw:text.slice(a+START.length,b).trim(),busy:false};
      }
    }
    return {raw:null,busy:false};
  })()`
}

function autoVraArtifactProbeScript(): string {
  return `(() => {
    const START=${JSON.stringify('[VERTEX_VRA_ARTIFACT/1]')};
    const END=${JSON.stringify('[/VERTEX_VRA_ARTIFACT/1]')};
    const busy=Boolean(
      document.querySelector('[data-testid="stop-button"]')
      ||document.querySelector('button[aria-label*="Stop generating"]')
      ||document.querySelector('button[aria-label*="Stop"]')
      ||document.querySelector('button[aria-label*="停止"]')
    );
    const raws=[];
    const nodes=[...document.querySelectorAll('[data-message-author-role="assistant"], article')];
    for(const node of nodes){
      const text=(node.innerText||node.textContent||'').trim();
      let from=0;
      while(from<text.length){
        const a=text.indexOf(START,from);
        if(a<0) break;
        const b=text.indexOf(END,a+START.length);
        if(b<a) break;
        raws.push(text.slice(a+START.length,b).trim());
        from=b+END.length;
      }
    }
    return {raws,busy};
  })()`
}

function autoVraArtifactClickScript(
  artifactId: string,
  filename: string,
  sourceSession: string,
  dispatchId: string | null
): string {
  return `(() => {
    const START=${JSON.stringify('[VERTEX_VRA_ARTIFACT/1]')};
    const END=${JSON.stringify('[/VERTEX_VRA_ARTIFACT/1]')};
    const ARTIFACT=${JSON.stringify(artifactId)};
    const FILE=${JSON.stringify(filename)};
    const SOURCE=${JSON.stringify(sourceSession)};
    const DISPATCH=${JSON.stringify(dispatchId)};
    const nodes=[...document.querySelectorAll('[data-message-author-role="assistant"], article')];
    for(let i=nodes.length-1;i>=0;i--){
      const node=nodes[i];
      const text=(node.innerText||node.textContent||'').trim();
      let from=0;
      while(from<text.length){
        const a=text.indexOf(START,from);
        if(a<0) break;
        const b=text.indexOf(END,a+START.length);
        if(b<a) break;
        const raw=text.slice(a+START.length,b).trim();
        from=b+END.length;
        let env=null;
        try{ env=JSON.parse(raw); }catch{ continue; }
        if(
          env?.schema!=='vertex-vra-artifact/1'
          ||env?.artifact_id!==ARTIFACT
          ||env?.filename!==FILE
          ||String(env?.source_session||'').trim().toLowerCase()!==SOURCE
          ||(DISPATCH!==null && env?.dispatch_id!==DISPATCH)
          ||env?.auto_dispatch!==true
        ) continue;

        const anchors=[...node.querySelectorAll('a[href]')];
        const candidates=anchors.filter(anchor=>{
          const href=decodeURIComponent(String(anchor.getAttribute('href')||'')).toLowerCase();
          const download=String(anchor.getAttribute('download')||'').toLowerCase();
          const label=String(anchor.textContent||'').trim().toLowerCase();
          const f=FILE.toLowerCase();
          return href.includes(f)
            ||download===f
            ||label===f
            ||href.includes('.vra')
            ||download.endsWith('.vra')
            ||label.endsWith('.vra');
        });
        if(candidates.length!==1) {
          return {ok:false,reason:candidates.length===0?'VRA_LINK_NOT_FOUND':'VRA_LINK_AMBIGUOUS'};
        }
        candidates[0].click();
        return {ok:true,reason:'VRA_LINK_CLICKED'};
      }
    }
    return {ok:false,reason:'VRA_MARKER_NOT_FOUND'};
  })()`
}

function parseAutoVraArtifact(raw: string, expectedSession: string): AutoVraArtifactEnvelope {
  const data = JSON.parse(raw) as Partial<AutoVraArtifactEnvelope>
  if (data.schema !== 'vertex-vra-artifact/1') throw new Error('AUTO_VRA_SCHEMA_UNSUPPORTED')
  if (sid(data.source_session) !== expectedSession) throw new Error('AUTO_VRA_SOURCE_MISMATCH')
  if (data.auto_dispatch !== true) throw new Error('AUTO_VRA_AUTO_DISPATCH_REQUIRED')
  if (
    typeof data.artifact_id !== 'string'
    || !/^[A-Za-z0-9._-]{1,220}$/.test(data.artifact_id)
  ) throw new Error('AUTO_VRA_ARTIFACT_ID_INVALID')
  if (
    typeof data.filename !== 'string'
    || !/^[^\\/]{1,240}\.vra$/i.test(data.filename)
  ) throw new Error('AUTO_VRA_FILENAME_INVALID')
  if (
    data.dispatch_id !== undefined
    && (
      typeof data.dispatch_id !== 'string'
      || data.dispatch_id.length < 1
      || data.dispatch_id.length > 256
    )
  ) throw new Error('AUTO_VRA_DISPATCH_ID_INVALID')
  return data as AutoVraArtifactEnvelope
}

async function probeAutoVraArtifacts(sessionId: string): Promise<AutoVraArtifactProbe> {
  const pane = paneFor(sessionId)
  const view = pane ? webview(pane) : null
  if (!view) return { raws: [], busy: false }
  try {
    const result = await view.executeJavaScript(
      autoVraArtifactProbeScript(),
      false
    ) as AutoVraArtifactProbe | null
    return {
      raws: Array.isArray(result?.raws)
        ? result!.raws.filter(item => typeof item === 'string')
        : [],
      busy: Boolean(result?.busy),
    }
  } catch {
    return { raws: [], busy: false }
  }
}

async function seedAutoVraBaseline(sessionId: string): Promise<void> {
  if (autoVraBaselines.has(sessionId)) return
  const probe = await probeAutoVraArtifacts(sessionId)
  const baseline = new Set<string>()
  for (const raw of probe.raws) {
    try {
      baseline.add(autoVraLogicalKey(parseAutoVraArtifact(raw, sessionId)))
    } catch {
      // Only strict VRA artifact envelopes participate.
    }
  }
  autoVraBaselines.set(sessionId, baseline)
}

async function seedAutoVraBaselines(sessions: string[]): Promise<void> {
  await Promise.all(sessions.map(sessionId => seedAutoVraBaseline(sid(sessionId))))
}

function autoVraExecutionContext(
  sessionId: string,
  env: AutoVraArtifactEnvelope
): { lease: ArdAutoAuthorityLease; context: ArdAutoTaskContext | null } | null {
  const lease = authorityForSession(sessionId)
  if (!lease) return null
  if (!lease.allowed_sessions.map(sid).includes(sessionId)) return null

  const contexts = loadAutoTaskContexts()
  const context = contexts[sessionId] ?? null
  if (sid(lease.controller_session) === sessionId) {
    if (env.dispatch_id && context && context.parent_dispatch_id !== env.dispatch_id) return null
    return { lease, context }
  }

  if (!context) return null
  if (context.authority_id !== lease.authority_id) return null
  if (sid(context.delegated_session) !== sessionId) return null
  if (env.dispatch_id !== context.parent_dispatch_id) return null
  return { lease, context }
}

async function pollAutoVraArtifacts(): Promise<void> {
  if (autoVraScanInFlight) return
  autoVraScanInFlight = true
  try {
    const authorities = loadAutoAuthorities()
    const sessions = Array.from(new Set(
      authorities.flatMap(lease => lease.allowed_sessions.map(sid))
    )).filter(sessionId => VALID_SESSIONS.has(sessionId))

    const receipts = loadStringSet(AUTO_VRA_RECEIPT_KEY)

    for (const sessionId of sessions) {
      if (!autoVraBaselines.has(sessionId)) {
        await seedAutoVraBaseline(sessionId)
        continue
      }

      const probe = await probeAutoVraArtifacts(sessionId)
      if (probe.busy) continue

      const baseline = autoVraBaselines.get(sessionId) ?? new Set<string>()
      for (const raw of probe.raws) {
        let env: AutoVraArtifactEnvelope
        try {
          env = parseAutoVraArtifact(raw, sessionId)
        } catch {
          continue
        }

        const logical = autoVraLogicalKey(env)
        if (baseline.has(logical) || receipts.has(logical)) continue

        const execution = autoVraExecutionContext(sessionId, env)
        if (!execution) continue

        const pane = paneFor(sessionId)
        const view = pane ? webview(pane) : null
        if (!view) continue

        const clicked = await view.executeJavaScript(
          autoVraArtifactClickScript(
            env.artifact_id,
            env.filename,
            sessionId,
            env.dispatch_id ?? null
          ),
          true
        ) as { ok?: boolean; reason?: string } | null

        if (!clicked?.ok) {
          toast(
            'VERTEX // AUTO VRA CAPTURE HOLD',
            `${sessionId.toUpperCase()} / ${env.artifact_id}\n${clicked?.reason ?? 'AUTO_VRA_CAPTURE_UNKNOWN'}`,
            'red'
          )
          continue
        }

        receipts.add(logical)
        saveStringSet(AUTO_VRA_RECEIPT_KEY, receipts, 1024)
        baseline.add(logical)
        autoVraBaselines.set(sessionId, baseline)

        toast(
          'VERTEX // AUTO VRA CAPTURE',
          `${sessionId.toUpperCase()} / ${env.artifact_id}\nVRA link committed → will-download Capture`,
          'green'
        )
      }
    }
  } finally {
    autoVraScanInFlight = false
  }
}

function parseTaskResult(
  raw: string,
  expected: AwaitingResult
): TaskResultEnvelope {
  const data = JSON.parse(raw) as TaskResultEnvelope
  if (data.schema !== 'vertex-task-result/1') throw new Error('RESULT_SCHEMA_UNSUPPORTED')
  if (data.dispatch_id !== expected.dispatchId) throw new Error('RESULT_DISPATCH_MISMATCH')
  if (sid(data.source_session) !== expected.target) throw new Error('RESULT_SOURCE_MISMATCH')
  if (sid(data.return_to) !== expected.source) throw new Error('RESULT_RETURN_TO_MISMATCH')
  if (typeof data.message !== 'string' || !data.message.trim()) throw new Error('RESULT_MESSAGE_EMPTY')
  return data
}
function ensureHud(): HTMLElement {
  let hud = document.querySelector<HTMLElement>('[data-vertex-task-hud]')
  if (hud) return hud

  hud = document.createElement('div')
  hud.dataset.vertexTaskHud = '1'
  hud.style.cssText = [
    'position:fixed',
    'inset:0',
    'z-index:2147483647',
    'display:none',
    'align-items:center',
    'justify-content:center',
    'background:rgba(7,11,16,.62)',
    'backdrop-filter:blur(8px)',
    'font-family:Inter,Segoe UI,system-ui,sans-serif'
  ].join(';')
  document.body.append(hud)
  return hud
}

function vertexDialog(options: {
  eyebrow: string
  title: string
  body: string
  confirmText?: string
  cancelText?: string
  accent?: 'blue' | 'green' | 'red'
}): Promise<boolean> {
  const hud = ensureHud()
  hud.innerHTML = ''

  const accent = options.accent === 'green'
    ? '#55D69E'
    : options.accent === 'red'
      ? '#FF6F7C'
      : '#168CFF'

  const panel = document.createElement('div')
  panel.style.cssText = [
    'width:min(760px,calc(100vw - 64px))',
    'max-height:min(78vh,720px)',
    'overflow:auto',
    'background:linear-gradient(180deg,#111923 0%,#0C121A 100%)',
    'border:1px solid #26394B',
    'border-radius:14px',
    'box-shadow:0 28px 90px rgba(0,0,0,.55),0 0 0 1px rgba(22,140,255,.08),0 0 36px rgba(22,140,255,.12)',
    'color:#CBD5DF'
  ].join(';')

  const top = document.createElement('div')
  top.style.cssText = `height:3px;background:linear-gradient(90deg,transparent,${accent},#3AB8FF,transparent);opacity:.95`

  const content = document.createElement('div')
  content.style.cssText = 'padding:22px 24px 18px'

  const eyebrow = document.createElement('div')
  eyebrow.textContent = options.eyebrow
  eyebrow.style.cssText = `font:700 10px/1.4 ui-monospace,monospace;letter-spacing:1.6px;color:${accent};text-transform:uppercase;margin-bottom:9px`

  const title = document.createElement('div')
  title.textContent = options.title
  title.style.cssText = 'font-size:20px;font-weight:700;letter-spacing:.2px;color:#E5EDF5;margin-bottom:12px'

  const body = document.createElement('pre')
  body.textContent = options.body
  body.style.cssText = [
    'white-space:pre-wrap',
    'word-break:break-word',
    'margin:0',
    'padding:14px 16px',
    'border:1px solid #1C2935',
    'border-radius:9px',
    'background:#070B10',
    'color:#9EADBD',
    'font:12px/1.7 ui-monospace,SFMono-Regular,Consolas,monospace'
  ].join(';')

  const actions = document.createElement('div')
  actions.style.cssText = 'display:flex;justify-content:flex-end;gap:10px;padding:0 24px 22px'

  const cancel = document.createElement('button')
  cancel.textContent = options.cancelText ?? 'CANCEL'
  cancel.style.cssText = [
    'height:34px',
    'padding:0 15px',
    'border:1px solid #26394B',
    'border-radius:7px',
    'background:#0C121A',
    'color:#718195',
    'font:700 11px/32px ui-monospace,monospace',
    'letter-spacing:.8px',
    'cursor:pointer'
  ].join(';')

  const confirm = document.createElement('button')
  confirm.textContent = options.confirmText ?? 'DISPATCH'
  confirm.style.cssText = [
    'height:34px',
    'padding:0 17px',
    `border:1px solid ${accent}`,
    'border-radius:7px',
    `background:${accent}18`,
    `color:${accent === '#168CFF' ? '#A9D7FF' : accent}`,
    'font:800 11px/32px ui-monospace,monospace',
    'letter-spacing:.8px',
    `box-shadow:0 0 18px ${accent}22`,
    'cursor:pointer'
  ].join(';')

  panel.append(top, content, actions)
  content.append(eyebrow, title, body)
  actions.append(cancel, confirm)
  hud.append(panel)
  hud.style.display = 'flex'

  return new Promise(resolve => {
    const finish = (value: boolean): void => {
      hud.style.display = 'none'
      hud.innerHTML = ''
      resolve(value)
    }
    cancel.addEventListener('click', () => finish(false), { once: true })
    confirm.addEventListener('click', () => finish(true), { once: true })
    hud.addEventListener('click', event => {
      if (event.target === hud) finish(false)
    }, { once: true })
  })
}

function toast(title: string, body: string, tone: 'blue' | 'green' | 'red' = 'blue'): void {
  const color = tone === 'green' ? '#55D69E' : tone === 'red' ? '#FF6F7C' : '#168CFF'
  const node = document.createElement('div')
  node.style.cssText = [
    'position:fixed',
    'right:22px',
    'bottom:22px',
    'z-index:2147483646',
    'width:min(420px,calc(100vw - 44px))',
    'padding:13px 15px',
    'border-radius:9px',
    'background:#0C121AF2',
    'border:1px solid #26394B',
    `border-left:3px solid ${color}`,
    'box-shadow:0 14px 44px rgba(0,0,0,.45)',
    'color:#CBD5DF',
    'font-family:Inter,Segoe UI,system-ui,sans-serif',
    'transition:opacity .25s ease,transform .25s ease'
  ].join(';')
  node.innerHTML = `
    <div style="font:800 10px/1.4 ui-monospace,monospace;letter-spacing:1.2px;color:${color};margin-bottom:4px">${title}</div>
    <div style="font-size:12px;line-height:1.55;color:#9EADBD"></div>
  `
  const bodyNode = node.querySelector('div:last-child') as HTMLElement
  bodyNode.textContent = body
  document.body.append(node)
  window.setTimeout(() => {
    node.style.opacity = '0'
    node.style.transform = 'translateY(8px)'
    window.setTimeout(() => node.remove(), 260)
  }, 3600)
}

async function probePane(pane: HTMLElement): Promise<SourceProbe> {
  const view = webview(pane)
  if (!view) return { raw: null, busy: false }
  try {
    const result = await view.executeJavaScript(probeScript(), false) as SourceProbe | null
    return {
      raw: typeof result?.raw === 'string' ? result.raw : null,
      busy: Boolean(result?.busy),
    }
  } catch {
    return { raw: null, busy: false }
  }
}

async function probeVxsRequest(pane: HTMLElement): Promise<VxsRequestProbe> {
  const view = webview(pane)
  if (!view) return { raw: null, busy: false }
  try {
    const result = await view.executeJavaScript(vxsRequestProbeScript(), false) as VxsRequestProbe | null
    return {
      raw: typeof result?.raw === 'string' ? result.raw : null,
      busy: Boolean(result?.busy),
    }
  } catch {
    return { raw: null, busy: false }
  }
}

async function seedVxsRequestBaselines(sessionIds: string[]): Promise<void> {
  for (const source of sessionIds.map(sid).filter(value => VALID_SESSIONS.has(value))) {
    const pane = paneFor(source)
    if (!pane) continue
    const probe = await probeVxsRequest(pane)
    if (!probe.raw) continue
    try {
      const env = parseVxsRequestEnvelope(probe.raw, source)
      vxsRequestBaselines.set(source, env.request_id)
    } catch {
      // Existing malformed/non-canonical VXS text is never armed retroactively.
    }
  }
}

function vxsReceiptKey(source: string, requestId: string): string {
  return `${source}::${requestId}`
}

function buildVxsResultBody(env: VxsRequestEnvelope, status: 'SUCCEEDED' | 'FAILED', message: string): string {
  return [
    VXS_RESULT_START,
    JSON.stringify({
      schema: 'vertex-vxs-result/1',
      request_id: env.request_id,
      origin_session: env.origin_session,
      action: env.action,
      project_root: env.project_root,
      status,
      message,
    }),
    VXS_RESULT_END,
    '',
  ].join('\n')
}

async function dispatchVxsRequest(env: VxsRequestEnvelope, source: string): Promise<void> {
  const receipt = vxsReceiptKey(source, env.request_id)
  const receipts = loadStringSet(VXS_REQUEST_RECEIPT_KEY)
  if (receipts.has(receipt)) return

  let status: 'SUCCEEDED' | 'FAILED' = 'FAILED'
  let message = ''
  try {
    const raw = await window.vertexPortal.exportVraCard(
      `${VXS_REQUEST_COMMAND_PREFIX}${encodeURIComponent(JSON.stringify(env))}`
    )
    status = 'SUCCEEDED'
    message = raw
    try {
      const parsed = JSON.parse(raw) as { status?: unknown }
      if (parsed.status !== 'SUCCEEDED' && parsed.status !== 'IDEMPOTENT_SUCCEEDED') status = 'FAILED'
    } catch {
      status = 'FAILED'
    }
  } catch (error) {
    message = error instanceof Error ? error.message : String(error)
  }

  receipts.add(receipt)
  saveStringSet(VXS_REQUEST_RECEIPT_KEY, receipts, 512)

  enqueueDelivery({
    kind: 'RESULT',
    dispatchId: env.request_id,
    source: 'vxs',
    target: source,
    body: buildVxsResultBody(env, status, message),
    queuedAt: Date.now(),
    attempts: 0,
    lastReason: '',
    resultSource: 'vxs',
    resultStatus: status === 'SUCCEEDED' ? 'DONE' : 'FAILED',
  })
  ensureDeliveryLoop()
  void processDeliveryQueues()

  toast(
    status === 'SUCCEEDED' ? 'VERTEX // VXS REQUEST' : 'VERTEX // VXS REQUEST FAILED',
    `${source.toUpperCase()} / ${env.request_id}\n${status}\nResult is queued back to the originating VERA.`,
    status === 'SUCCEEDED' ? 'green' : 'red'
  )
}

async function pollVxsRequests(): Promise<void> {
  const activeSessions = Array.from(VALID_SESSIONS).filter(source => authorityForSession(source) !== null)
  for (const source of activeSessions) {
    const pane = paneFor(source)
    if (!pane) continue
    const probe = await probeVxsRequest(pane)
    if (!probe.raw || probe.busy) continue

    let env: VxsRequestEnvelope
    try {
      env = parseVxsRequestEnvelope(probe.raw, source)
    } catch {
      continue
    }

    const receipt = vxsReceiptKey(source, env.request_id)
    if (loadStringSet(VXS_REQUEST_RECEIPT_KEY).has(receipt)) continue
    if (vxsRequestBaselines.get(source) === env.request_id) continue

    const stable = vxsRequestStable.get(source)
    if (!stable || stable.requestId !== env.request_id) {
      vxsRequestStable.set(source, { requestId: env.request_id, count: 1 })
      continue
    }

    stable.count += 1
    if (stable.count < STABLE_POLLS_REQUIRED) continue

    vxsRequestStable.delete(source)
    vxsRequestBaselines.set(source, env.request_id)
    await dispatchVxsRequest(env, source)
  }
}

function queueFor(target: string): PendingDelivery[] {
  let queue = deliveryQueues.get(target)
  if (!queue) {
    queue = []
    deliveryQueues.set(target, queue)
  }
  return queue
}

function deliveryMarker(item: PendingDelivery): string {
  return item.kind === 'TASK'
    ? `dispatch_id=${item.dispatchId}`
    : `dispatch_id=${item.dispatchId}`
}

function enqueueDelivery(item: PendingDelivery): boolean {
  const queue = queueFor(item.target)
  const unique = `${item.kind}:${item.dispatchId}:${item.source}:${item.target}`

  if (queue.some(row =>
    `${row.kind}:${row.dispatchId}:${row.source}:${row.target}` === unique
  )) return false

  queue.push(item)
  return true
}

function queuedTotal(): number {
  let total = 0
  for (const queue of deliveryQueues.values()) total += queue.length
  return total
}

async function processTargetQueue(target: string): Promise<void> {
  if (processingTargets.has(target)) return

  const queue = queueFor(target)
  if (!queue.length) return

  processingTargets.add(target)
  try {
    const item = queue[0]
    const marker = deliveryMarker(item)

    if (item.kind === 'TASK') {
      const done = loadReceipts()
      if (done.has(receiptKey(item.dispatchId, item.target))) {
        queue.shift()
        return
      }
    } else {
      const done = loadResultReceipts()
      if (done.has(resultKey(item.dispatchId, item.resultSource ?? item.source))) {
        queue.shift()
        return
      }
    }

    const readiness = await targetReadiness(target, marker)
    if (!readiness.ready) {
      item.attempts += 1
      if (item.lastReason !== readiness.reason) {
        item.lastReason = readiness.reason
        toast(
          'VERTEX // QUEUE HOLD',
          `${target.toUpperCase()} / ${item.dispatchId}\n${readiness.reason}\nReadyになったら自動送信します。`,
          'blue'
        )
      }
      return
    }

    const pane = paneFor(target)
    const view = pane ? webview(pane) : null
    if (!view) {
      item.lastReason = 'TARGET_WEBVIEW_NOT_READY'
      item.attempts += 1
      return
    }

    const result = await view.executeJavaScript(
      sendMessageScript(item.body, marker),
      false
    ) as { ok?: boolean; reason?: string } | null

    if (!result?.ok) {
      const reason = result?.reason ?? 'TARGET_SEND_FAILED'
      item.attempts += 1
      if (item.lastReason !== reason) {
        item.lastReason = reason
        toast(
          'VERTEX // QUEUE HOLD',
          `${target.toUpperCase()} / ${item.dispatchId}\n${reason}\n再送待機中。`,
          reason === 'TARGET_COMPOSER_OCCUPIED' || reason === 'TARGET_BUSY_GENERATING'
            ? 'blue'
            : 'red'
        )
      }
      return
    }

    if (item.kind === 'TASK') {
      const done = loadReceipts()
      done.add(receiptKey(item.dispatchId, item.target))
      saveReceipts(done)

      if (item.autoAuthorityId) {
        setAutoTaskContext(
          item.target,
          item.source,
          item.dispatchId,
          item.autoAuthorityId
        )
      }

      awaitingResults.set(
        resultKey(item.dispatchId, item.target),
        {
          dispatchId: item.dispatchId,
          source: item.source,
          target: item.target,
          sentAt: Date.now(),
        }
      )

      toast(
        'VERTEX // TASK SENT',
        `${item.source.toUpperCase()} → ${item.target.toUpperCase()}\n${item.dispatchId}\nRESULT WAITING`,
        'green'
      )
    } else {
      const sourceOfResult = item.resultSource ?? item.source
      if (item.resultStatus === 'BLOCKED') {
        if (item.resultFingerprint) {
          const progress = loadStringSet(BLOCKED_RESULT_RECEIPT_KEY)
          progress.add(item.resultFingerprint)
          saveStringSet(BLOCKED_RESULT_RECEIPT_KEY, progress, 256)
        }
        // BLOCKED is a progress return, not terminal completion. Keep the
        // AwaitingResult + AUTO task context alive so Evidence can lead to DONE.
        toast(
          'VERTEX // RESULT BLOCKED',
          `${sourceOfResult.toUpperCase()} → ${item.target.toUpperCase()}\n${item.dispatchId}\nCONTEXT HELD`,
          'blue'
        )
      } else {
        const done = loadResultReceipts()
        done.add(resultKey(item.dispatchId, sourceOfResult))
        saveResultReceipts(done)
        awaitingResults.delete(resultKey(item.dispatchId, sourceOfResult))
        clearAutoTaskContext(sourceOfResult, item.dispatchId)

        toast(
          'VERTEX // RESULT RETURNED',
          `${sourceOfResult.toUpperCase()} → ${item.target.toUpperCase()}\n${item.dispatchId}`,
          'green'
        )
      }
    }

    queue.shift()
  } catch (error) {
    const item = queue[0]
    if (item) {
      item.attempts += 1
      item.lastReason = `ERROR ${String(error)}`
    }
  } finally {
    processingTargets.delete(target)
  }
}

async function processDeliveryQueues(): Promise<void> {
  await Promise.all(
    Array.from(deliveryQueues.keys()).map(target => processTargetQueue(target))
  )
}

function ensureDeliveryLoop(): void {
  if (deliveryTimer !== null) return
  deliveryTimer = window.setInterval(() => {
    if (!queuedTotal()) return
    void processDeliveryQueues()
  }, POLL_MS)
}

async function pollTaskResults(): Promise<void> {
  for (const expected of Array.from(awaitingResults.values())) {
    const resultReceipt = loadResultReceipts()
    if (resultReceipt.has(resultKey(expected.dispatchId, expected.target))) {
      awaitingResults.delete(resultKey(expected.dispatchId, expected.target))
      continue
    }

    const pane = paneFor(expected.target)
    const view = pane ? webview(pane) : null
    if (!view) continue

    try {
      const probe = await view.executeJavaScript(
        resultProbeScript(expected.dispatchId),
        false
      ) as { raw?: string | null; busy?: boolean } | null

      if (probe?.busy || typeof probe?.raw !== 'string' || !probe.raw.trim()) {
        continue
      }

      const result = parseTaskResult(probe.raw, expected)
      const returnBody = buildResultReturnBody(result)
      const blockedFingerprint = result.status === 'BLOCKED'
        ? blockedResultFingerprint(result)
        : null
      if (
        blockedFingerprint
        && loadStringSet(BLOCKED_RESULT_RECEIPT_KEY).has(blockedFingerprint)
      ) {
        continue
      }

      enqueueDelivery({
        kind: 'RESULT',
        dispatchId: expected.dispatchId,
        source: expected.target,
        target: expected.source,
        body: returnBody,
        queuedAt: Date.now(),
        attempts: 0,
        lastReason: '',
        resultSource: expected.target,
        resultStatus: result.status,
        resultFingerprint: blockedFingerprint ?? undefined,
      })

      toast(
        'VERTEX // RESULT CAPTURED',
        `${expected.target.toUpperCase()} → ${expected.source.toUpperCase()}\n${expected.dispatchId}\n発信元がReadyになったら自動返送します。`,
        'green'
      )
    } catch {
      // Only a strict RESULT envelope is accepted. Ordinary assistant text is ignored.
    }
  }
}

function ensureResultLoop(): void {
  if (resultTimer !== null) return
  resultTimer = window.setInterval(() => {
    if (!awaitingResults.size) return
    void pollTaskResults()
  }, POLL_MS)
}

async function dispatchEnvelope(
  env: TaskEnvelope,
  source: string,
  mode: 'AUTO' | 'MANUAL'
): Promise<void> {
  const done = loadReceipts()

  // Sparse targets are intentional: only sessions listed in `targets` receive work.
  // Each target has its own prompt string, so one dispatch can carry completely
  // different instructions for VERA1 / VERA3 / VERA4 / VERA5.
  const targetRows = Object.entries(env.targets).map(([targetRaw, task]) => ({
    target: sid(targetRaw),
    task,
  }))

  const pending = targetRows.filter(
    row => !done.has(receiptKey(env.dispatch_id, row.target))
  )

  if (!pending.length) {
    if (mode === 'MANUAL') {
      toast('VERTEX // TASK', `${env.dispatch_id} は送信済みです。`, 'blue')
    }
    return
  }

  if (mode === 'MANUAL') {
    const preview = pending
      .map(row => `${row.target.toUpperCase()}\n${row.task.slice(0, 420)}`)
      .join('\n\n────────────────────────\n\n')

    const approved = await vertexDialog({
      eyebrow: 'VERTEX // TARGET ROUTER',
      title: `${source.toUpperCase()} → ${pending.map(row => row.target.toUpperCase()).join(' / ')}`,
      body: `DISPATCH ID\n${env.dispatch_id}\n\n${preview}`,
      confirmText: 'QUEUE / DISPATCH',
      cancelText: 'CANCEL',
      accent: 'blue',
    })
    if (!approved) return
  }

  const autoAuthority = mode === 'AUTO' ? authorityForController(source) : null
  if (mode === 'AUTO' && !autoAuthority) {
    toast(
      'VERTEX // AUTO AUTHORITY',
      `${source.toUpperCase()} AUTO authority is not active. Re-arm AUTO with Human Gate.`,
      'red'
    )
    return
  }

  let queued = 0
  for (const row of pending) {
    const body = buildTaskBody(
      row.task,
      source,
      row.target,
      env.dispatch_id,
      autoAuthority?.authority_id ?? null
    )
    if (enqueueDelivery({
      kind: 'TASK',
      dispatchId: env.dispatch_id,
      source,
      target: row.target,
      body,
      queuedAt: Date.now(),
      attempts: 0,
      lastReason: '',
      autoAuthorityId: autoAuthority?.authority_id,
    })) {
      queued += 1
    }
  }

  ensureDeliveryLoop()
  ensureResultLoop()
  void processDeliveryQueues()

  toast(
    mode === 'AUTO' ? 'VERTEX // AUTO ROUTE' : 'VERTEX // TASK ROUTE',
    `${env.dispatch_id}\nTARGETS: ${pending.map(row => row.target.toUpperCase()).join(' / ')}\nQUEUED: ${queued}\n各targetを個別Ready判定し、結果も発信元へ自動返送します。`,
    'green'
  )
}
async function manualDispatch(pane: HTMLElement): Promise<void> {
  const source = sid(pane.getAttribute('session-id'))
  if (!VALID_SESSIONS.has(source)) {
    toast('VERTEX // TASK ERROR', 'Source session is unresolved.', 'red')
    return
  }

  const probe = await probePane(pane)
  if (!probe.raw) {
    toast('VERTEX // TASK', `最新Vera回答に ${START} ブロックがありません。`, 'red')
    return
  }

  try {
    const env = parseEnvelope(probe.raw, source)
    await dispatchEnvelope(env, source, 'MANUAL')
  } catch (error) {
    toast('VERTEX // TASK ERROR', String(error), 'red')
  }
}

async function armAuto(pane: HTMLElement, button: HTMLButtonElement): Promise<void> {
  const source = sid(pane.getAttribute('session-id'))
  if (!VALID_SESSIONS.has(source)) return

  if (armedSources.has(source)) {
    armedSources.delete(source)
    armBaseline.delete(source)
    probeStable.delete(source)
    vxsRequestStable.clear()
    vxsRequestBaselines.clear()
    try {
      await revokeAutoAuthority(source)
    } catch (error) {
      toast('VERTEX // AUTO REVOKE', String(error), 'red')
    }
    button.dataset.armed = '0'
    button.textContent = 'AUTO'
    button.style.borderColor = '#26394B'
    button.style.color = '#718195'
    button.style.background = '#111923'
    button.style.boxShadow = 'none'
    toast('VERTEX // AUTO', `${source.toUpperCase()} AUTO DISARMED`, 'blue')
    return
  }

  const probe = await probePane(pane)
  if (probe.raw) {
    try {
      const env = parseEnvelope(probe.raw, source)
      armBaseline.set(source, env.dispatch_id)
    } catch {
      // Existing non-task content does not affect arming.
    }
  }

  let authority: ArdAutoAuthorityLease
  try {
    authority = await grantAutoAuthority(source)
  } catch (error) {
    toast('VERTEX // AUTO AUTHORITY FAILED', String(error), 'red')
    return
  }

  armedSources.add(source)
  probeStable.delete(source)
  // 000111V5: Human AUTO arm defines the old-artifact baseline for every
  // allowed Vera. Anything already visible is never auto-downloaded.
  await seedAutoVraBaselines(authority.allowed_sessions)
  await seedVxsRequestBaselines(authority.allowed_sessions)
  button.dataset.armed = '1'
  button.textContent = 'AUTO●'
  button.style.borderColor = '#168CFF'
  button.style.color = '#9FD1FF'
  button.style.background = '#102C44'
  button.style.boxShadow = '0 0 16px rgba(22,140,255,.22)'
  toast(
    'VERTEX // AUTO ARMED',
    `${source.toUpperCase()} AUTO● · FULL EXECUTION AUTHORITY ON · TASK + VRA · ${authority.authority_id.slice(0, 8)}…`,
    'green'
  )
  ensureAutoLoop()
}

async function pollAuto(): Promise<void> {
  for (const source of Array.from(armedSources)) {
    const pane = paneFor(source)
    if (!pane) continue

    const probe = await probePane(pane)
    if (!probe.raw || probe.busy) continue

    let env: TaskEnvelope
    try {
      env = parseEnvelope(probe.raw, source)
    } catch {
      continue
    }

    if (env.delivery !== 'AUTO') continue
    if (armBaseline.get(source) === env.dispatch_id) continue

    const stable = probeStable.get(source)
    if (!stable || stable.dispatchId !== env.dispatch_id) {
      probeStable.set(source, { dispatchId: env.dispatch_id, count: 1 })
      continue
    }

    stable.count += 1
    if (stable.count < STABLE_POLLS_REQUIRED) continue

    probeStable.delete(source)
    armBaseline.set(source, env.dispatch_id)
    await dispatchEnvelope(env, source, 'AUTO')
  }
}

function ensureAutoLoop(): void {
  if (autoTimer !== null) return
  autoTimer = window.setInterval(() => {
    if (!armedSources.size) return
    void (async () => {
      await pollAuto()
      await pollVxsRequests()
      await pollAutoVraArtifacts()
    })()
  }, POLL_MS)
}

function styleButton(button: HTMLButtonElement, active = false): void {
  button.style.cssText = [
    'height:22px',
    'min-width:42px',
    'padding:0 7px',
    `border:1px solid ${active ? '#168CFF' : '#26394B'}`,
    'border-radius:4px',
    `background:${active ? '#102C44' : '#111923'}`,
    `color:${active ? '#9FD1FF' : '#718195'}`,
    'font:700 10px/20px ui-monospace,monospace',
    'letter-spacing:.45px',
    `box-shadow:${active ? '0 0 16px rgba(22,140,255,.22)' : 'none'}`,
    'cursor:pointer'
  ].join(';')
}

function decoratePane(pane: HTMLElement): void {
  const root = pane.shadowRoot
  if (!root) return

  let controls = root.querySelector<HTMLElement>('[data-vertex-task-controls]')
  if (controls) return

  controls = document.createElement('div')
  controls.dataset.vertexTaskControls = '1'
  controls.style.cssText = 'display:inline-flex;align-items:center;gap:5px;margin-left:5px'

  const taskButton = document.createElement('button')
  taskButton.type = 'button'
  taskButton.dataset.vertexTaskDispatch = '1'
  taskButton.textContent = 'TASK'
  taskButton.title = 'Vertex Task Dispatch'
  styleButton(taskButton)
  taskButton.addEventListener('click', () => void manualDispatch(pane))

  const autoButton = document.createElement('button')
  autoButton.type = 'button'
  autoButton.dataset.vertexTaskAuto = '1'
  autoButton.dataset.armed = '0'
  autoButton.textContent = 'AUTO'
  autoButton.title = 'Vertex AUTO · Task Dispatch + VRA Execution Authority'
  styleButton(autoButton)
  autoButton.addEventListener('click', () => void armAuto(pane, autoButton))

  controls.append(taskButton, autoButton)

  const relay = root.querySelector<HTMLElement>(
    '[data-action="relay"],.relayButton,button[title*="Relay"],button[title*="relay"]'
  )
  if (relay?.parentElement) {
    relay.insertAdjacentElement('afterend', controls)
    return
  }

  const header = root.querySelector<HTMLElement>('.sessionHead,.sessionHeader,header')
  if (header) {
    header.append(controls)
    return
  }

  root.querySelector<HTMLElement>('.session')?.prepend(controls)
}

function decorateAll(): void {
  for (const pane of panes()) decoratePane(pane)
}

function bootstrap(): void {
  decorateAll()
  ensureAutoLoop()
  ensureDeliveryLoop()
  ensureResultLoop()

  const frame = document.querySelector('vertex-main-frame') as HTMLElement | null
  const root = frame?.shadowRoot
  if (!root) {
    window.setTimeout(bootstrap, 400)
    return
  }

  new MutationObserver(() => decorateAll()).observe(root, {
    childList: true,
    subtree: true,
  })
}

if (document.readyState === 'loading') {
  window.addEventListener('DOMContentLoaded', bootstrap, { once: true })
} else {
  bootstrap()
}

// TARGET_READINESS_QUEUE_IS_NATIVE
// SELECTIVE_TARGET_ROUTING_IS_NATIVE
// DISTINCT_PROMPT_PER_TARGET_IS_NATIVE
// STRUCTURED_RESULT_RETURN_IS_NATIVE
// RESULT_DOM_READ_IS_MARKER_BOUNDED_ONLY
// AUTO_VRA_CAPTURE_IS_WILL_DOWNLOAD_NATIVE
// AUTO_VRA_DOM_READ_IS_MARKER_BOUNDED_ONLY
// BLOCKED_RESULT_PRESERVES_AUTO_TASK_CONTEXT
