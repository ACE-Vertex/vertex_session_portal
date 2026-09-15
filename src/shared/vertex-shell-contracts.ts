export interface VertexShellState {
  generation: '000080V4A'
  backend: string
  cwd: string
  busy: boolean
  activePid: number | null
  activeCommandId: string | null
  historyPath: string
}

export interface VertexShellCommandRequest {
  command: string
  cwd?: string | null
}

export interface VertexShellSetCwdRequest {
  cwd: string
}

export type VertexShellStreamKind = 'stdout' | 'stderr' | 'system'

export interface VertexShellStreamEvent {
  commandId: string
  kind: VertexShellStreamKind
  chunk: string
  at: string
}

export interface VertexShellCommandResult {
  commandId: string
  command: string
  cwd: string
  backend: string
  pid: number | null
  exitCode: number
  durationMs: number
  stdoutBytes: number
  stderrBytes: number
  stopped: boolean
}

export interface VertexShellBridge {
  state(): Promise<VertexShellState>
  execute(request: VertexShellCommandRequest): Promise<VertexShellCommandResult>
  stop(): Promise<VertexShellState>
  setCwd(request: VertexShellSetCwdRequest): Promise<VertexShellState>
  onOutput(listener: (event: VertexShellStreamEvent) => void): () => void
}
