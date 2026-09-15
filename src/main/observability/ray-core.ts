import { createHash } from 'node:crypto'
import { promises as fs } from 'node:fs'
import * as path from 'node:path'
import {
  OBSERVABILITY_CONTRACT,
  type DeepRayReport,
  type RayContentHit,
  type RayDependencyEdge,
  type RayNode,
  type RayNodeKind,
  type RaySourceFile,
  type RayTextRead,
  type RayTreeReport
} from './contracts'

export interface RayTreeOptions {
  maxDepth?: number
  maxNodes?: number
  skipNames?: string[]
}

export interface DeepRayOptions extends RayTreeOptions {
  maxSourceBytes?: number
  maxSourceFiles?: number
}

export interface RaySearchOptions extends RayTreeOptions {
  regex?: boolean
  caseSensitive?: boolean
  maxHits?: number
  maxTextBytes?: number
}

const HARD_MAX_DEPTH = 128
const HARD_MAX_NODES = 100_000
const HARD_MAX_SOURCE_FILES = 30_000
const HARD_MAX_SOURCE_BYTES = 4 * 1024 * 1024
const HARD_MAX_TEXT_READ_BYTES = 8 * 1024 * 1024
const DEFAULT_SKIP_NAMES = new Set(['.git', 'node_modules', 'out', 'dist', 'target', '.next', '.cache'])
const SOURCE_EXTENSIONS = new Set([
  '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.rs', '.py', '.go', '.java', '.kt', '.kts',
  '.cs', '.cpp', '.cc', '.c', '.h', '.hpp', '.json', '.toml', '.yaml', '.yml', '.md', '.sql'
])
const MANIFEST_NAMES = new Set([
  'package.json', 'pnpm-lock.yaml', 'package-lock.json', 'yarn.lock', 'cargo.toml', 'cargo.lock',
  'pyproject.toml', 'requirements.txt', 'go.mod', 'go.sum', 'tsconfig.json', 'electron.vite.config.ts'
])

function clamp(value: number | undefined, fallback: number, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return Math.max(min, Math.min(max, Math.floor(value)))
}

function kindOf(dirent: { isFile(): boolean; isDirectory(): boolean; isSymbolicLink(): boolean }): RayNodeKind {
  if (dirent.isFile()) return 'file'
  if (dirent.isDirectory()) return 'directory'
  if (dirent.isSymbolicLink()) return 'symlink'
  return 'other'
}

function normalizeCompare(input: string): string {
  const resolved = path.resolve(input)
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved
}

function inside(root: string, candidate: string): boolean {
  const rootCmp = normalizeCompare(root)
  const candidateCmp = normalizeCompare(candidate)
  const relative = path.relative(rootCmp, candidateCmp)
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export class RayCore {
  private readonly roots: string[]

  constructor(allowedRoots: string[]) {
    const normalized = [...new Set(allowedRoots.filter(Boolean).map(root => path.resolve(root)))]
    if (normalized.length === 0) throw new Error('RAY_ALLOWED_ROOT_REQUIRED')
    this.roots = normalized
  }

  allowedRoots(): string[] {
    return [...this.roots]
  }

  resolveScoped(inputPath: string): string {
    const candidate = path.resolve(inputPath)
    if (!this.roots.some(root => inside(root, candidate))) {
      throw new Error(`RAY_SCOPE_DENIED:${candidate}`)
    }
    return candidate
  }

  async readText(inputPath: string, maxBytes = 64 * 1024, tail = false): Promise<RayTextRead> {
    const target = this.resolveScoped(inputPath)
    const stat = await fs.stat(target)
    if (!stat.isFile()) throw new Error(`RAY_NOT_FILE:${target}`)

    const bounded = clamp(maxBytes, 64 * 1024, 1, HARD_MAX_TEXT_READ_BYTES)
    const bytesRead = Math.min(stat.size, bounded)
    const start = tail ? Math.max(0, stat.size - bytesRead) : 0
    const handle = await fs.open(target, 'r')
    try {
      const buffer = Buffer.alloc(bytesRead)
      if (bytesRead > 0) await handle.read(buffer, 0, bytesRead, start)
      return {
        path: target,
        bytesRead,
        truncated: stat.size > bytesRead,
        tail,
        text: buffer.toString('utf8')
      }
    } finally {
      await handle.close()
    }
  }

  async sha256(inputPath: string, maxBytes = 16 * 1024 * 1024): Promise<string | null> {
    const target = this.resolveScoped(inputPath)
    const stat = await fs.stat(target)
    if (!stat.isFile()) return null
    const bounded = clamp(maxBytes, 16 * 1024 * 1024, 1, 64 * 1024 * 1024)
    if (stat.size > bounded) return null
    const data = await fs.readFile(target)
    return createHash('sha256').update(data).digest('hex')
  }

  async scanTree(inputRoot: string, options: RayTreeOptions = {}): Promise<RayTreeReport> {
    const root = this.resolveScoped(inputRoot)
    const maxDepth = clamp(options.maxDepth, 64, 0, HARD_MAX_DEPTH)
    const maxNodes = clamp(options.maxNodes, 50_000, 1, HARD_MAX_NODES)
    const skipNames = new Set(options.skipNames ?? [...DEFAULT_SKIP_NAMES])
    const nodes: RayNode[] = []
    const warnings: string[] = []
    const queue: Array<{ absolute: string; depth: number }> = [{ absolute: root, depth: 0 }]
    let truncated = false

    while (queue.length > 0) {
      const current = queue.shift()
      if (!current) break
      if (current.depth > maxDepth) {
        truncated = true
        continue
      }

      let entries
      try {
        entries = await fs.readdir(current.absolute, { withFileTypes: true })
      } catch (error) {
        warnings.push(`READ_DIR_FAILED:${current.absolute}:${error instanceof Error ? error.message : String(error)}`)
        continue
      }

      for (const entry of entries) {
        if (nodes.length >= maxNodes) {
          truncated = true
          queue.length = 0
          break
        }
        if (skipNames.has(entry.name)) continue

        const absolute = path.join(current.absolute, entry.name)
        const kind = kindOf(entry)
        let sizeBytes: number | null = null
        let modifiedMs: number | null = null
        try {
          const stat = await fs.lstat(absolute)
          sizeBytes = stat.isFile() ? stat.size : null
          modifiedMs = stat.mtimeMs
        } catch (error) {
          warnings.push(`LSTAT_FAILED:${absolute}:${error instanceof Error ? error.message : String(error)}`)
        }

        nodes.push({
          path: absolute,
          relativePath: path.relative(root, absolute),
          kind,
          depth: current.depth + 1,
          sizeBytes,
          modifiedMs
        })

        if (kind === 'directory' && current.depth < maxDepth) {
          queue.push({ absolute, depth: current.depth + 1 })
        }
      }
    }

    return {
      schema: OBSERVABILITY_CONTRACT,
      root,
      nodes,
      truncated,
      warnings,
      scannedAt: new Date().toISOString()
    }
  }

  async searchContent(inputRoot: string, query: string, options: RaySearchOptions = {}): Promise<RayContentHit[]> {
    if (!query) return []
    const tree = await this.scanTree(inputRoot, options)
    const caseSensitive = options.caseSensitive === true
    const source = options.regex === true ? query : escapeRegex(query)
    const expression = new RegExp(source, caseSensitive ? '' : 'i')
    const maxHits = clamp(options.maxHits, 1000, 1, 5000)
    const maxTextBytes = clamp(options.maxTextBytes, 512 * 1024, 1024, HARD_MAX_SOURCE_BYTES)
    const hits: RayContentHit[] = []

    for (const node of tree.nodes) {
      if (hits.length >= maxHits) break
      if (node.kind !== 'file') continue
      const extension = path.extname(node.path).toLowerCase()
      if (!SOURCE_EXTENSIONS.has(extension) && !MANIFEST_NAMES.has(path.basename(node.path).toLowerCase())) continue
      if ((node.sizeBytes ?? 0) > maxTextBytes) continue

      let read: RayTextRead
      try {
        read = await this.readText(node.path, maxTextBytes)
      } catch {
        continue
      }
      const lines = read.text.split(/\r?\n/)
      for (let index = 0; index < lines.length; index += 1) {
        const line = lines[index] ?? ''
        if (!expression.test(line)) continue
        hits.push({ path: node.path, line: index + 1, text: line.slice(0, 500) })
        if (hits.length >= maxHits) break
      }
    }
    return hits
  }

  async deepScan(inputRoot: string, options: DeepRayOptions = {}): Promise<DeepRayReport> {
    const tree = await this.scanTree(inputRoot, options)
    const maxSourceBytes = clamp(options.maxSourceBytes, 1024 * 1024, 1024, HARD_MAX_SOURCE_BYTES)
    const maxSourceFiles = clamp(options.maxSourceFiles, 12_000, 1, HARD_MAX_SOURCE_FILES)
    const sourceFiles: RaySourceFile[] = []
    const manifests: string[] = []

    for (const node of tree.nodes) {
      if (node.kind !== 'file') continue
      const base = path.basename(node.path).toLowerCase()
      if (MANIFEST_NAMES.has(base)) manifests.push(node.path)
      const extension = path.extname(node.path).toLowerCase()
      if (!SOURCE_EXTENSIONS.has(extension)) continue
      if ((node.sizeBytes ?? 0) > maxSourceBytes) continue
      if (sourceFiles.length >= maxSourceFiles) break

      let read: RayTextRead
      try {
        read = await this.readText(node.path, maxSourceBytes)
      } catch {
        continue
      }

      sourceFiles.push({
        path: node.path,
        relativePath: node.relativePath,
        extension,
        imports: this.extractImports(read.text),
        symbols: this.extractSymbols(read.text),
        sizeBytes: node.sizeBytes ?? read.bytesRead
      })
    }

    const fileSet = new Set(sourceFiles.map(file => normalizeCompare(file.path)))
    const edges: RayDependencyEdge[] = []
    for (const file of sourceFiles) {
      for (const specifier of file.imports) {
        edges.push({
          from: file.path,
          specifier,
          to: this.resolveImportAgainstSet(file.path, specifier, fileSet)
        })
      }
    }

    const truncated = tree.truncated || sourceFiles.length >= maxSourceFiles
    return {
      schema: OBSERVABILITY_CONTRACT,
      root: tree.root,
      tree,
      sourceFiles,
      edges,
      manifests,
      truncated,
      scannedAt: new Date().toISOString()
    }
  }

  private extractImports(text: string): string[] {
    const results = new Set<string>()
    const patterns = [
      /\bfrom\s+['"]([^'"]+)['"]/g,
      /\brequire\(\s*['"]([^'"]+)['"]\s*\)/g,
      /\bimport\(\s*['"]([^'"]+)['"]\s*\)/g,
      /^\s*import\s+['"]([^'"]+)['"]/gm
    ]
    for (const pattern of patterns) {
      for (const match of text.matchAll(pattern)) {
        const specifier = match[1]
        if (specifier) results.add(specifier)
      }
    }
    return [...results]
  }

  private extractSymbols(text: string): string[] {
    const results = new Set<string>()
    const patterns = [
      /\b(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)/g,
      /\b(?:export\s+)?class\s+([A-Za-z_$][\w$]*)/g,
      /\b(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)/g,
      /\b(?:export\s+)?type\s+([A-Za-z_$][\w$]*)/g,
      /\b(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)/g,
      /\b(?:pub\s+)?(?:struct|enum|trait|fn)\s+([A-Za-z_][\w]*)/g,
      /^\s*(?:def|class)\s+([A-Za-z_][\w]*)/gm
    ]
    for (const pattern of patterns) {
      for (const match of text.matchAll(pattern)) {
        const symbol = match[1]
        if (symbol) results.add(symbol)
      }
    }
    return [...results].slice(0, 5000)
  }

  private resolveImportAgainstSet(fromFile: string, specifier: string, fileSet: Set<string>): string | null {
    if (!specifier.startsWith('.')) return null
    const base = path.resolve(path.dirname(fromFile), specifier)
    const candidates = [
      base,
      `${base}.ts`, `${base}.tsx`, `${base}.js`, `${base}.jsx`, `${base}.mjs`, `${base}.cjs`, `${base}.json`,
      path.join(base, 'index.ts'), path.join(base, 'index.tsx'), path.join(base, 'index.js'), path.join(base, 'index.jsx')
    ]
    for (const candidate of candidates) {
      if (fileSet.has(normalizeCompare(candidate))) return path.resolve(candidate)
    }
    return null
  }
}
