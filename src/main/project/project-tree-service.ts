import {
  clipboard,
  shell
} from 'electron'
import {
  readdirSync
} from 'node:fs'
import {
  basename,
  dirname,
  isAbsolute,
  relative,
  resolve
} from 'node:path'
import type {
  ProjectTreeBreadcrumb,
  ProjectTreeListing,
  ProjectTreeNode,
  ProjectTreeNodeKind
} from '../../shared/contracts'

function nodeKind(entry: import('node:fs').Dirent): ProjectTreeNodeKind {
  if (entry.isSymbolicLink()) return 'SYMLINK'
  if (entry.isDirectory()) return 'DIRECTORY'
  if (entry.isFile()) return 'FILE'
  return 'OTHER'
}

export class ProjectTreeService {
  private readonly projectRootPath: string
  private readonly workspaceRootPath: string

  constructor(projectRoot: string) {
    this.projectRootPath = resolve(projectRoot)

    const parent = dirname(this.projectRootPath)
    this.workspaceRootPath = basename(parent).toLowerCase() === 'development'
      ? dirname(parent)
      : parent
  }

  resolve(path: string): string {
    return this.resolveInsideWorkspace(path)
  }

  list(path?: string): ProjectTreeListing {
    const directoryPath = this.resolveInsideWorkspace(path)
    const relativeDirectory = relative(this.workspaceRootPath, directoryPath)
    const children = readdirSync(directoryPath, { withFileTypes: true })
      .map(entry => {
        const kind = nodeKind(entry)
        const absolutePath = resolve(directoryPath, entry.name)
        const relativePath = relative(this.workspaceRootPath, absolutePath)
        return {
          name: entry.name,
          path: absolutePath,
          relativePath,
          kind,
          expandable: kind === 'DIRECTORY'
        } satisfies ProjectTreeNode
      })
      .sort((left, right) => {
        const leftRank = left.kind === 'DIRECTORY' ? 0 : 1
        const rightRank = right.kind === 'DIRECTORY' ? 0 : 1
        if (leftRank !== rightRank) return leftRank - rightRank
        return left.name.localeCompare(right.name, undefined, { sensitivity: 'base', numeric: true })
      })

    return {
      rootPath: this.projectRootPath,
      workspaceRootPath: this.workspaceRootPath,
      parentPath: directoryPath === this.workspaceRootPath ? null : dirname(directoryPath),
      breadcrumbs: this.breadcrumbs(directoryPath),
      directory: {
        name: basename(directoryPath) || directoryPath,
        path: directoryPath,
        relativePath: relativeDirectory,
        kind: 'DIRECTORY',
        expandable: true
      },
      children
    }
  }

  async open(path: string): Promise<void> {
    const candidate = this.resolveInsideWorkspace(path)
    const error = await shell.openPath(candidate)
    if (error) throw new Error(`PROJECT_TREE_OPEN_FAILED: ${error}`)
  }

  reveal(path: string): void {
    const candidate = this.resolveInsideWorkspace(path)
    shell.showItemInFolder(candidate)
  }

  copy(path: string): void {
    const candidate = this.resolveInsideWorkspace(path)
    clipboard.writeText(candidate)
  }

  private breadcrumbs(directoryPath: string): ProjectTreeBreadcrumb[] {
    const relativeDirectory = relative(this.workspaceRootPath, directoryPath)
    const segments = relativeDirectory
      ? relativeDirectory.split(/[\\/]+/).filter(Boolean)
      : []

    const breadcrumbs: ProjectTreeBreadcrumb[] = [
      {
        name: basename(this.workspaceRootPath) || this.workspaceRootPath,
        path: this.workspaceRootPath
      }
    ]

    let current = this.workspaceRootPath
    for (const segment of segments) {
      current = resolve(current, segment)
      breadcrumbs.push({ name: segment, path: current })
    }
    return breadcrumbs
  }

  private resolveInsideWorkspace(input?: string): string {
    const candidate = !input?.trim()
      ? this.projectRootPath
      : resolve(this.projectRootPath, isAbsolute(input) ? input : input.trim())

    const rel = relative(this.workspaceRootPath, candidate)
    if (rel === '') return candidate
    if (rel.startsWith('..') || isAbsolute(rel)) {
      throw new Error('PROJECT_TREE_OUTSIDE_WORKSPACE')
    }
    return candidate
  }
}
