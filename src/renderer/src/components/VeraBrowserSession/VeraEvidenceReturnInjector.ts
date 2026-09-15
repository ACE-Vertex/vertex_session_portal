export const VERA_EVIDENCE_RETURN_EVENT = 'vertex-vera-evidence-return'
export const VERA_EVIDENCE_RETURN_RESULT_EVENT = 'vertex-vera-evidence-return-result'

export type VeraEvidenceReturnMessage = {
  deliveryId: string
  jobId: string
  originVera: string
  originSession: string
  originWindow: string
  correlationId: string
  returnChannel: string
  text: string
}

export type VeraEvidenceReturnResult = {
  deliveryId: string
  jobId: string
  originSession: string
  ok: boolean
  stage: string
}

type EvidenceWebview = HTMLElement & {
  executeJavaScript: (code: string, userGesture?: boolean) => Promise<unknown>
}


// VERTEX_EVIDENCE_CONTRACT_AUTO_INJECTION_000038V2
type VertexEvidenceReadContract = {
  id?: unknown
  version?: unknown
  rules?: unknown
  stateSemantics?: unknown
  readingOrder?: unknown
}

type VertexContractCatalogBridge = {
  resolve: (id: 'vertex.vra.issue/1' | 'vertex.evidence.read/1') => Promise<unknown>
}

function evidenceContractBridge(): VertexContractCatalogBridge | null {
  return (
    window as unknown as {
      vertexContractCatalog?: VertexContractCatalogBridge
    }
  ).vertexContractCatalog ?? null
}

function renderEvidenceReadContract(raw: unknown): string {
  if (!raw || typeof raw !== 'object') return ''
  const contract = raw as VertexEvidenceReadContract
  if (contract.id !== 'vertex.evidence.read/1') return ''

  const version = typeof contract.version === 'string' ? contract.version : 'active'
  const rules = Array.isArray(contract.rules)
    ? contract.rules.filter((item): item is string => typeof item === 'string')
    : []
  const readingOrder = Array.isArray(contract.readingOrder)
    ? contract.readingOrder.filter((item): item is string => typeof item === 'string')
    : []
  const semantics =
    contract.stateSemantics &&
    typeof contract.stateSemantics === 'object' &&
    !Array.isArray(contract.stateSemantics)
      ? Object.entries(contract.stateSemantics as Record<string, unknown>)
          .filter((entry): entry is [string, string] => typeof entry[1] === 'string')
      : []

  const lines = [
    `[VERTEX EVIDENCE INTERPRETATION CONTRACT ${String(contract.id)}@${version}]`,
    'Use this active contract to interpret the Evidence below. Do not reconstruct Evidence semantics from LLM memory.'
  ]

  if (readingOrder.length > 0) {
    lines.push('READING_ORDER:')
    lines.push(...readingOrder.map(item => `- ${item}`))
  }

  const importantSemantics = semantics.filter(([key]) =>
    /AVAILABLE|RETURN_QUEUED|RETURNED|verified|final_state|rollback|write_lock/i.test(key)
  )
  if (importantSemantics.length > 0) {
    lines.push('STATE_SEMANTICS:')
    lines.push(...importantSemantics.map(([key, value]) => `- ${key} => ${value}`))
  }

  const importantRules = rules.filter(rule =>
    /identity|return|visibility|rollback|boundary|AVAILABLE|Workstation/i.test(rule)
  )
  if (importantRules.length > 0) {
    lines.push('RULES:')
    lines.push(...importantRules.map(rule => `- ${rule}`))
  }

  lines.push('[/VERTEX EVIDENCE INTERPRETATION CONTRACT]')
  return lines.join('\n')
}


// VERTEX_ROUNDTRIP_CONTRACT_PACKET_000039V2
type VertexVraIssueContract = {
  id?: unknown
  version?: unknown
  rules?: unknown
  example?: unknown
}

function renderVraIssueContract(raw: unknown): string {
  // VERTEX_VRA_CONTRACT_NEWLINE_REPAIR_000041V2: render real line breaks, not literal backslash-n text.
  if (!raw || typeof raw !== 'object') return ''
  const contract = raw as VertexVraIssueContract
  if (contract.id !== 'vertex.vra.issue/1') return ''

  const version = typeof contract.version === 'string' ? contract.version : 'active'
  const rules = Array.isArray(contract.rules)
    ? contract.rules.filter((item): item is string => typeof item === 'string')
    : []

  const importantRules = rules.filter(rule =>
    /schema_version|HUMAN_APPLY|vra-routing|fresh|origin_|return_channel|lane_policy|copy|payload\/|sha256|verification|TEST|forbidden/i.test(rule)
  )

  const lines = [
    `[VERTEX VRA ISSUANCE CONTRACT ${String(contract.id)}@${version}]`,
    'Use this active contract for the next VRA issuance. Never reconstruct VRA format from LLM memory.'
  ]

  if (importantRules.length > 0) {
    lines.push('RULES:')
    lines.push(...importantRules.map(rule => `- ${rule}`))
  }

  if (contract.example && typeof contract.example === 'object') {
    try {
      lines.push('CANONICAL_EXAMPLE:')
      lines.push(JSON.stringify(contract.example, null, 2))
    } catch {
      // Example rendering is advisory only.
    }
  }

  lines.push('[/VERTEX VRA ISSUANCE CONTRACT]')
  return lines.join('\n')
}

async function evidencePayloadWithActiveContract(payload: string): Promise<string> {
  try {
    const bridge = evidenceContractBridge()
    if (!bridge) return payload

    const [evidenceContract, vraContract] = await Promise.all([
      bridge.resolve('vertex.evidence.read/1'),
      bridge.resolve('vertex.vra.issue/1')
    ])

    const evidenceGuide = renderEvidenceReadContract(evidenceContract)
    const vraGuide = renderVraIssueContract(vraContract)
    const contractPacket = [evidenceGuide, vraGuide].filter(Boolean).join('\n\n')

    return contractPacket ? `${contractPacket}\n\n${payload}` : payload
  } catch {
    // Fail open for return delivery: contract assistance must never block Evidence.
    return payload
  }
}

export async function injectWorkstationEvidence(
  browser: HTMLElement,
  message: VeraEvidenceReturnMessage
): Promise<VeraEvidenceReturnResult> {
  // VERTEX_ROUNDTRIP_CONTRACT_PACKET_000039V2: resolve active Evidence-read + next-VRA issuance contracts before injection.
  const __vertexEvidencePayload = await evidencePayloadWithActiveContract(message.text)

  const webview = browser as EvidenceWebview
  const script = `(() => {
    const text = __TEXT__;
    const composer =
      document.querySelector('#prompt-textarea') ||
      document.querySelector('[data-testid="prompt-textarea"]') ||
      document.querySelector('textarea');
    if (!composer) return Promise.resolve({ ok: false, stage: 'composer-not-found' });
    composer.focus();
    if (composer instanceof HTMLTextAreaElement) {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
      if (setter) setter.call(composer, text); else composer.value = text;
      composer.dispatchEvent(new Event('input', { bubbles: true }));
      composer.dispatchEvent(new Event('change', { bubbles: true }));
    } else {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(composer);
      selection?.removeAllRanges();
      selection?.addRange(range);
      const inserted = document.execCommand('insertText', false, text);
      if (!inserted) {
        composer.textContent = text;
        composer.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
      }
    }
    const findSend = () =>
      document.querySelector('button[data-testid="send-button"]') ||
      document.querySelector('button[aria-label="Send prompt"]') ||
      document.querySelector('button[aria-label="Send"]') ||
      document.querySelector('button[aria-label="送信"]');
    return new Promise(resolve => {
      let attempts = 0;
      const attempt = () => {
        const button = findSend();
        if (button instanceof HTMLButtonElement && !button.disabled) {
          button.click();
          resolve({ ok: true, stage: 'sent' });
          return;
        }
        attempts += 1;
        if (attempts >= 40) {
          resolve({ ok: false, stage: 'send-button-not-ready' });
          return;
        }
        window.setTimeout(attempt, 75);
      };
      attempt();
    });
  })()`.replace('__TEXT__', JSON.stringify(__vertexEvidencePayload))

  const raw = await webview.executeJavaScript(script, true)
  const result = raw as { ok?: boolean; stage?: string } | null
  return {
    deliveryId: message.deliveryId,
    jobId: message.jobId,
    originSession: message.originSession,
    ok: result?.ok === true,
    stage: typeof result?.stage === 'string' ? result.stage : 'unknown'
  }
}
