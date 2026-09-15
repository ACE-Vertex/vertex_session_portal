import {
  dialog,
  ipcMain
} from 'electron'
import { readFile, stat } from 'node:fs/promises'
import { basename } from 'node:path'
import type {
  AiLaneId,
  ListAiLaneModelsRequest,
  SaveAiLaneSettingsRequest,
  SaveProviderSettingsRequest,
  SessionAgentRequest
} from '../../shared/contracts'
import {
  SessionAgentService
} from '../agents/session-agent-service'

export function registerSessionAgentIpc(
  service: SessionAgentService
): void {
  ipcMain.handle(
    'session-agent:provider-status',
    () => service.providerStatus()
  )

  ipcMain.handle(
    'session-agent:provider-settings',
    () => service.getProviderSettings()
  )

  ipcMain.handle(
    'session-agent:save-provider-settings',
    (_event, request: SaveProviderSettingsRequest) =>
      service.saveProviderSettings(request)
  )

  ipcMain.handle(
    'session-agent:clear-provider-api-key',
    () => service.clearProviderApiKey()
  )

  ipcMain.handle(
    'session-agent:ai-lane-settings',
    () => service.getAiLaneSettings()
  )

  ipcMain.handle(
    'session-agent:save-ai-lane-settings',
    (_event, request: SaveAiLaneSettingsRequest) =>
      service.saveAiLaneSettings(request)
  )

  ipcMain.handle(
    'session-agent:clear-ai-lane-api-key',
    (_event, laneId: AiLaneId) =>
      service.clearAiLaneApiKey(laneId)
  )

  ipcMain.handle(
    'session-agent:list-ai-lane-models',
    (_event, request: ListAiLaneModelsRequest) =>
      service.listAiLaneModels(request)
  )

  ipcMain.handle(
    'session-agent:browse-local-llm',
    async () => {
      const result = await dialog.showOpenDialog({
        title: 'Select local raw LLM',
        properties: ['openFile'],
        filters: [
          { name: 'LLM model files', extensions: ['gguf', 'bin', 'safetensors'] },
          { name: 'All files', extensions: ['*'] }
        ]
      })
      if (result.canceled || result.filePaths.length === 0) return null
      return result.filePaths[0]
    }
  )

  ipcMain.handle(
    'session-agent:browse-session-context-file',
    async () => {
      const result = await dialog.showOpenDialog({
        title: 'Attach local text context',
        properties: ['openFile'],
        filters: [
          {
            name: 'Text / code / log files',
            extensions: [
              'txt', 'md', 'json', 'jsonl', 'log', 'ts', 'tsx', 'js', 'jsx',
              'vue', 'rs', 'py', 'ps1', 'cmd', 'bat', 'sql', 'yaml', 'yml',
              'toml', 'xml', 'html', 'css', 'scss', 'ini', 'cfg', 'csv'
            ]
          },
          { name: 'All files', extensions: ['*'] }
        ]
      })

      if (result.canceled || result.filePaths.length === 0) return null

      const path = result.filePaths[0]
      const info = await stat(path)
      if (!info.isFile()) throw new Error('SESSION_CONTEXT_NOT_FILE')
      if (info.size > 262144) throw new Error('SESSION_CONTEXT_FILE_TOO_LARGE_256KB_MAX')

      const buffer = await readFile(path)
      if (buffer.subarray(0, Math.min(buffer.length, 8192)).includes(0)) {
        throw new Error('SESSION_CONTEXT_BINARY_NOT_SUPPORTED')
      }

      return {
        name: basename(path),
        path,
        content: buffer.toString('utf8')
      }
    }
  )

  ipcMain.handle(
    'session-agent:conversation',
    (_event, sessionId: string) =>
      service.conversation(sessionId)
  )

  ipcMain.handle(
    'session-agent:retrieval',
    (_event, sessionId: string) =>
      service.retrievalHits(sessionId)
  )

  ipcMain.handle(
    'session-agent:send',
    (_event, request: SessionAgentRequest) =>
      service.send(request)
  )
}
