export type VeraRelayMessage = {
  relayId: string
  from: string
  to: string
  text: string
  sentAt: number
}

type RelayWebview = HTMLElement & {
  executeJavaScript: (code: string, userGesture?: boolean) => Promise<unknown>
}

export type VeraRelayInjectionResult = {
  ok: boolean
  sent: false
  stage: string
}

// FINAL_WIRING_B_000054V1: Prompt Relay is clipboard PASTE ONLY.
// It writes to the target composer and never clicks Send or reads response content.
export async function injectRelayMessage(
  browser: HTMLElement,
  message: VeraRelayMessage
): Promise<VeraRelayInjectionResult> {
  const webview = browser as RelayWebview
  const text = message.text
  const script = "(() => {\n  const text = __TEXT__;\n  const composer =\n    document.querySelector('#prompt-textarea') ||\n    document.querySelector('[data-testid=\"prompt-textarea\"]') ||\n    document.querySelector('textarea');\n\n  if (!composer) return { ok: false, sent: false, stage: 'composer-not-found' };\n  composer.focus();\n\n  if (composer instanceof HTMLTextAreaElement) {\n    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;\n    if (setter) setter.call(composer, text);\n    else composer.value = text;\n    composer.dispatchEvent(new Event('input', { bubbles: true }));\n    composer.dispatchEvent(new Event('change', { bubbles: true }));\n  } else {\n    const selection = window.getSelection();\n    const range = document.createRange();\n    range.selectNodeContents(composer);\n    selection?.removeAllRanges();\n    selection?.addRange(range);\n    const inserted = document.execCommand('insertText', false, text);\n    if (!inserted) {\n      composer.textContent = text;\n      composer.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));\n    }\n  }\n\n  return { ok: true, sent: false, stage: 'clipboard-pasted' };\n})()".replace('__TEXT__', JSON.stringify(text))
  const raw = await webview.executeJavaScript(script, true)
  const result = raw as Partial<VeraRelayInjectionResult> | null
  if (!result?.ok) return { ok: false, sent: false, stage: String(result?.stage ?? 'write-only-injection-failed') }
  return { ok: true, sent: false, stage: 'clipboard-pasted' }
}
