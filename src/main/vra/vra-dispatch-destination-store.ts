import { app, BrowserWindow, dialog, type OpenDialogOptions } from 'electron'
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { dirname, isAbsolute, join, normalize } from 'node:path'

export const DEFAULT_VRA_DISPATCH_DESTINATION =
  'G:\\Vertex_Project\\Development\\_incoming'

type DestinationRecord = {
  path: string
  updatedAt: string
}

export type VraDispatchDestinationState = {
  path: string
  isDefault: boolean
}

function configPath(): string {
  return join(app.getPath('userData'), 'vra-dispatch-destination.json')
}

function validateCandidate(value: unknown): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim()
  if (!trimmed || !isAbsolute(trimmed)) return null
  return normalize(trimmed)
}

function readConfigured(): string | null {
  try {
    const file = configPath()
    if (!existsSync(file)) return null
    const record = JSON.parse(readFileSync(file, 'utf8')) as Partial<DestinationRecord>
    return validateCandidate(record.path)
  } catch {
    return null
  }
}

function persist(path: string): void {
  const file = configPath()
  mkdirSync(dirname(file), { recursive: true })
  const temporary = `${file}.tmp`
  const record: DestinationRecord = {
    path,
    updatedAt: new Date().toISOString()
  }
  writeFileSync(temporary, JSON.stringify(record, null, 2), 'utf8')
  renameSync(temporary, file)
}

export function getVraDispatchDestination(): string {
  return readConfigured() ?? DEFAULT_VRA_DISPATCH_DESTINATION
}

export function getVraDispatchDestinationState(): VraDispatchDestinationState {
  const path = getVraDispatchDestination()
  return {
    path,
    isDefault: path === DEFAULT_VRA_DISPATCH_DESTINATION
  }
}

export async function chooseVraDispatchDestination(): Promise<
  VraDispatchDestinationState & { canceled: boolean }
> {
  const current = getVraDispatchDestination()
  const options: OpenDialogOptions = {
    title: 'Select VRA Dispatch Destination',
    defaultPath: current,
    buttonLabel: 'Use this folder',
    properties: ['openDirectory', 'createDirectory']
  }

  const owner = BrowserWindow.getFocusedWindow()
  const result = owner
    ? await dialog.showOpenDialog(owner, options)
    : await dialog.showOpenDialog(options)

  if (result.canceled || result.filePaths.length === 0) {
    return { ...getVraDispatchDestinationState(), canceled: true }
  }

  const selected = validateCandidate(result.filePaths[0])
  if (!selected) {
    throw new Error('VRA_DISPATCH_DESTINATION_INVALID')
  }

  mkdirSync(selected, { recursive: true })
  persist(selected)

  return {
    path: selected,
    isDefault: selected === DEFAULT_VRA_DISPATCH_DESTINATION,
    canceled: false
  }
}
