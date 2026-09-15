import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

import { VraRegistryCore } from './vra-registry-core'
import { SqliteVraRegistryStore } from './sqlite-vra-registry-store'

export interface VraRegistryRuntime {
  core: VraRegistryCore
  store: SqliteVraRegistryStore
  databasePath: string
  close(): void
}

/**
 * Registry department composition root.
 *
 * Responsibility:
 * - choose the durable Registry backend
 * - bind the same durable store to Registry state and VLog
 * - expose one Core instance
 *
 * Non-responsibility:
 * - VRA manifest parsing
 * - Human approval
 * - Dispatch Bay presentation
 * - Workstation lane allocation
 * - job execution
 * - Evidence return delivery
 */
export function createVraRegistryRuntime(userDataRoot: string): VraRegistryRuntime {
  const directory = join(userDataRoot, 'vra-registry')
  mkdirSync(directory, { recursive: true })

  const databasePath = join(directory, 'registry.sqlite3')
  const store = new SqliteVraRegistryStore(databasePath)
  const core = new VraRegistryCore(store, store)

  return {
    core,
    store,
    databasePath,
    close: () => store.close(),
  }
}
