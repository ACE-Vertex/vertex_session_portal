const DECISION_EVENT = 'vertex:firmware-change-decision'
const RESULT_EVENT = 'vertex:firmware-change-registrar-result'
const INSTALL_FLAG = '__vertexFirmwareDecisionBridgeInstalled'

type FirmwareRegistrarResult = {
  accepted: boolean
  committed: boolean
  idempotent: boolean
  decisionId: string
  requestId: string
  target: string
  proposedVersion: string
  registryState: 'APPROVED' | 'REJECTED' | 'UNCHANGED'
  approvalRecordHash: string
  journalEntryHash: string
}

type FirmwarePortalBridge = {
  submitFirmwareChangeDecision?: (detail: unknown) => Promise<FirmwareRegistrarResult>
}

type FirmwareWindow = Window & {
  vertexPortal?: FirmwarePortalBridge
  [INSTALL_FLAG]?: boolean
}

const firmwareWindow = window as FirmwareWindow

if (!firmwareWindow[INSTALL_FLAG]) {
  firmwareWindow[INSTALL_FLAG] = true

  window.addEventListener(DECISION_EVENT, (event: Event) => {
    const detail = (event as CustomEvent<unknown>).detail
    const submit = firmwareWindow.vertexPortal?.submitFirmwareChangeDecision

    if (!submit) {
      window.dispatchEvent(new CustomEvent(RESULT_EVENT, {
        detail: {
          ok: false,
          error: 'Firmware Registrar preload bridge is unavailable.'
        }
      }))
      return
    }

    void submit(detail)
      .then(result => {
        window.dispatchEvent(new CustomEvent(RESULT_EVENT, {
          detail: { ok: true, result }
        }))
      })
      .catch(error => {
        window.dispatchEvent(new CustomEvent(RESULT_EVENT, {
          detail: {
            ok: false,
            error: error instanceof Error ? error.message : String(error)
          }
        }))
      })
  })
}
