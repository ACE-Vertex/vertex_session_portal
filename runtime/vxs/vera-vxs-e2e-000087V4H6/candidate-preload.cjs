// src/preload/index.h6candidate.ts
var import_electron = require("electron");
var api = {
  submitFirmwareChangeDecision: (detail) => import_electron.ipcRenderer.invoke("firmware:submit-change-decision", detail),
  bootstrap: () => import_electron.ipcRenderer.invoke(
    "workstation:bootstrap"
  ),
  setPrioritySession: (sessionId) => import_electron.ipcRenderer.invoke(
    "workstation:set-priority-session",
    sessionId
  ),
  activateNextMainLane: () => import_electron.ipcRenderer.invoke(
    "workstation:activate-next-main-lane"
  ),
  setSidebarTab: (tab) => import_electron.ipcRenderer.invoke(
    "workstation:set-sidebar-tab",
    tab
  ),
  fitMainWindow: (request) => import_electron.ipcRenderer.invoke(
    "portal:main-window-fit",
    request
  ),
  listProjectTree: (path) => import_electron.ipcRenderer.invoke("project-tree:list", path),
  resolveProjectTreePath: (path) => import_electron.ipcRenderer.invoke("project-tree:resolve", path),
  openProjectTreePath: (path) => import_electron.ipcRenderer.invoke("project-tree:open", path),
  revealProjectTreePath: (path) => import_electron.ipcRenderer.invoke("project-tree:reveal", path),
  copyProjectTreePath: (path) => import_electron.ipcRenderer.invoke("project-tree:copy-path", path),
  projectVirtualArd: (request) => import_electron.ipcRenderer.invoke(
    "workstation:project-virtual-ard",
    request
  ),
  appendSessionMessage: (request) => import_electron.ipcRenderer.invoke(
    "workstation:append-session-message",
    request
  ),
  createVirtualArdHandoff: (request) => import_electron.ipcRenderer.invoke(
    "workstation:create-virtual-ard-handoff",
    request
  ),
  getVirtualArdState: (missionId) => import_electron.ipcRenderer.invoke(
    "workstation:get-virtual-ard-state",
    missionId
  ),
  sessionProviderStatus: () => import_electron.ipcRenderer.invoke(
    "session-agent:provider-status"
  ),
  getSessionConversation: (sessionId) => import_electron.ipcRenderer.invoke(
    "session-agent:conversation",
    sessionId
  ),
  getSessionRetrieval: (sessionId) => import_electron.ipcRenderer.invoke(
    "session-agent:retrieval",
    sessionId
  ),
  sendSessionMessage: (request) => import_electron.ipcRenderer.invoke(
    "session-agent:send",
    request
  ),
  getProviderSettings: () => import_electron.ipcRenderer.invoke("session-agent:provider-settings"),
  saveProviderSettings: (request) => import_electron.ipcRenderer.invoke("session-agent:save-provider-settings", request),
  clearProviderApiKey: () => import_electron.ipcRenderer.invoke("session-agent:clear-provider-api-key"),
  getAiLaneSettings: () => import_electron.ipcRenderer.invoke("session-agent:ai-lane-settings"),
  saveAiLaneSettings: (request) => import_electron.ipcRenderer.invoke("session-agent:save-ai-lane-settings", request),
  clearAiLaneApiKey: (laneId) => import_electron.ipcRenderer.invoke("session-agent:clear-ai-lane-api-key", laneId),
  browseLocalLlm: () => import_electron.ipcRenderer.invoke("session-agent:browse-local-llm"),
  browseSessionContextFile: () => import_electron.ipcRenderer.invoke("session-agent:browse-session-context-file"),
  listAiLaneModels: (request) => import_electron.ipcRenderer.invoke("session-agent:list-ai-lane-models", request),
  storageStatus: () => import_electron.ipcRenderer.invoke("workstation:storage-status"),
  searchVcr: (query) => import_electron.ipcRenderer.invoke("workstation:vcr-search", query),
  upsertVcrEntry: (request) => import_electron.ipcRenderer.invoke("workstation:vcr-upsert", request),
  searchVca: (query) => import_electron.ipcRenderer.invoke("workstation:vca-search", query),
  appendVcaMemoryEvent: (request) => import_electron.ipcRenderer.invoke("workstation:vca-memory-append", request),
  appendVcaWeightRevision: (request) => import_electron.ipcRenderer.invoke("workstation:vca-weight-append", request),
  getVcaMemoryClockState: () => import_electron.ipcRenderer.invoke("workstation:vca-memory-clock"),
  getVcaCompensation: (sessionId, limit) => import_electron.ipcRenderer.invoke("workstation:vca-compensation", sessionId, limit),
  acknowledgeVcaCompensation: (sessionId, throughRevision) => import_electron.ipcRenderer.invoke("workstation:vca-compensation-ack", sessionId, throughRevision),
  getVcaCuratorState: () => import_electron.ipcRenderer.invoke("workstation:vca-curator-state"),
  saveVcaCuratorSettings: (request) => import_electron.ipcRenderer.invoke("workstation:vca-curator-save-settings", request),
  runVcaCurator: (request) => import_electron.ipcRenderer.invoke("workstation:vca-curator-run", request),
  getVeraSessionThreadBindings: () => import_electron.ipcRenderer.invoke("workstation:vera-thread-bindings"),
  updateVeraSessionThread: (request) => import_electron.ipcRenderer.invoke("workstation:vera-thread-update", request),
  getVcaInbox: () => import_electron.ipcRenderer.invoke("workstation:vca-inbox"),
  enqueueVcaInbox: (request) => import_electron.ipcRenderer.invoke("workstation:vca-inbox-enqueue", request),
  getVraDispatchState: () => import_electron.ipcRenderer.invoke("workstation:vra-dispatch-state"),
  registerVraWebviewSource: (request) => import_electron.ipcRenderer.invoke("workstation:vra-register-webview-source", request),
  exportVraCard: (cardId) => import_electron.ipcRenderer.invoke("workstation:vra-export-card", cardId),
  dispatchVraCard: (cardId) => import_electron.ipcRenderer.invoke("workstation:vra-dispatch-card", cardId),
  removeVraCard: (cardId) => import_electron.ipcRenderer.invoke("workstation:vra-remove-card", cardId),
  acknowledgeVraEvidenceDelivery: (request) => import_electron.ipcRenderer.invoke("workstation:vra-evidence-ack", request),
  getWorkstationSafety: () => import_electron.ipcRenderer.invoke("workstation:safety-state"),
  performWorkstationSafetyAction: (request) => import_electron.ipcRenderer.invoke("workstation:safety-action", request),
  getWorkstationServerProcessState: () => import_electron.ipcRenderer.invoke("workstation:server-process-state"),
  startWorkstationServer: () => import_electron.ipcRenderer.invoke("workstation:server-start"),
  readClipboardText: () => import_electron.ipcRenderer.invoke("portal:clipboard-read-text"),
  onVraDispatchChanged: (listener) => {
    const wrapped = () => listener();
    import_electron.ipcRenderer.on("vra-dispatch:changed", wrapped);
    return () => import_electron.ipcRenderer.removeListener("vra-dispatch:changed", wrapped);
  },
  onControlCommand: (listener) => {
    import_electron.ipcRenderer.on(
      "portal:control",
      (_event, serializedCommand) => {
        listener(
          serializedCommand
        );
      }
    );
  }
};
import_electron.contextBridge.exposeInMainWorld(
  "vertexPortal",
  {
    ...api,
    submitSystemPolicyDecision: (decision) => import_electron.ipcRenderer.invoke("vertex:system-policy-decision", decision),
    readActiveSystemPolicy: (target) => import_electron.ipcRenderer.invoke("vertex:system-policy-read-active", target)
  }
);
import_electron.contextBridge.exposeInMainWorld("vertexContractCatalog", Object.freeze({
  resolve: (id) => import_electron.ipcRenderer.invoke("vertex:contract-resolve", id),
  list: () => import_electron.ipcRenderer.invoke("vertex:contract-list")
}));
import_electron.contextBridge.exposeInMainWorld("vertexSystemPolicy", {
  resolve: (policyId) => import_electron.ipcRenderer.invoke("vertex:system-policy-resolve", policyId),
  list: () => import_electron.ipcRenderer.invoke("vertex:system-policy-list")
});
import_electron.contextBridge.exposeInMainWorld("veraVxs", {
  execute: (request) => import_electron.ipcRenderer.invoke("vera-vxs:execute", request)
});
