import { createHash } from 'node:crypto'
import type { BlackBoxEntry } from './contracts'

const MAX_ENTRIES = 512
const MAX_PAYLOAD_CHARS = 32_768

function serializeBounded(value: unknown): string {
  let serialized: string
  try {
    serialized = JSON.stringify(value)
  } catch {
    serialized = String(value)
  }
  if (serialized.length <= MAX_PAYLOAD_CHARS) return serialized
  return `${serialized.slice(0, MAX_PAYLOAD_CHARS)}…<TRUNCATED>`
}

export class BlackBox {
  private sequence = 0
  private readonly entries: BlackBoxEntry[] = []

  append(channel: string, payload: unknown): BlackBoxEntry {
    const bounded = serializeBounded(payload)
    const entry: BlackBoxEntry = {
      sequence: ++this.sequence,
      timestamp: new Date().toISOString(),
      channel,
      payload: bounded,
      sha256: createHash('sha256').update(bounded).digest('hex')
    }
    this.entries.push(entry)
    if (this.entries.length > MAX_ENTRIES) this.entries.splice(0, this.entries.length - MAX_ENTRIES)
    return { ...entry }
  }

  snapshot(): BlackBoxEntry[] {
    return this.entries.map(entry => ({ ...entry }))
  }

  clear(): void {
    this.entries.length = 0
  }
}
