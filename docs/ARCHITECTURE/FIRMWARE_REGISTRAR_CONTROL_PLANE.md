# Firmware Registrar Control Plane

This implementation keeps Firmware Change Gate as a Human-facing approval surface.

Flow:

1. `vertex:firmware-change-decision` DOM event
2. Renderer `FirmwareDecisionBridge`
3. trusted preload `submitFirmwareChangeDecision`
4. Main IPC `firmware:submit-change-decision`
5. `FirmwareRegistrar`
6. HMAC-SHA256 Signed Approval Record
7. deterministic validation + optimistic version check
8. atomic Firmware Registry commit
9. hash-chained Journal append

Durable local paths are below Electron `userData/vra-registry/firmware/`.

The Gate does not write Registry state directly.
APPROVE requires at least one validator row and every validator status must be PASS.
RED approvals additionally require the Gate's second Human confirmation.
REJECT is recorded and journaled without mutating Firmware Registry state.
