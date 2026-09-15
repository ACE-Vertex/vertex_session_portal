import {
  existsSync,
  readFileSync,
  readdirSync,
  statSync
} from 'node:fs'
import type {
  Dirent
} from 'node:fs'
import {
  extname,
  join,
  relative,
  resolve,
  sep
} from 'node:path'
import type {
  RetrievalHit,
  RetrievalSource
} from '../../shared/contracts'

interface CandidateFile {
  source: RetrievalSource
  absolutePath: string
  relativePath: string
}

const PROJECT_EXTENSIONS =
  new Set([
    '.ts',
    '.tsx',
    '.js',
    '.mjs',
    '.cjs',
    '.css',
    '.html',
    '.md',
    '.json',
    '.py',
    '.txt'
  ])

const EVIDENCE_EXTENSIONS =
  new Set([
    '.json',
    '.txt',
    '.md',
    '.log'
  ])

const EXCLUDED_DIRECTORIES =
  new Set([
    '.git',
    'node_modules',
    'out',
    'dist',
    'coverage',
    'MIGRATION_BACKUPS'
  ])

export class LocalRetrievalService {
  constructor(
    private readonly projectRoot:
      string
  ) {}

  search(
    query: string,
    limit = 8
  ): RetrievalHit[] {
    const normalized =
      query.trim()

    if (!normalized) {
      return []
    }

    const tokens =
      this.tokenize(
        normalized
      )

    const candidates = [
      ...this.collectProjectFiles(),
      ...this.collectEvidenceFiles()
    ]

    const hits:
      RetrievalHit[] = []

    for (
      const candidate
      of candidates
    ) {
      const hit =
        this.searchFile(
          candidate,
          normalized,
          tokens
        )

      if (hit) {
        hits.push(hit)
      }
    }

    return hits
      .sort(
        (a, b) =>
          b.score - a.score ||
          a.relativePath.localeCompare(
            b.relativePath
          )
      )
      .slice(
        0,
        Math.max(
          1,
          Math.min(limit, 16)
        )
      )
  }

  private collectProjectFiles():
    CandidateFile[] {
    const result:
      CandidateFile[] = []

    const roots = [
      'src',
      'docs',
      'scripts'
    ]

    for (
      const name
      of roots
    ) {
      const root =
        join(
          this.projectRoot,
          name
        )

      if (existsSync(root)) {
        this.walk(
          root,
          'PROJECT',
          PROJECT_EXTENSIONS,
          result,
          1400
        )
      }
    }

    for (
      const name of [
        'package.json',
        'README.md',
        'electron.vite.config.ts'
      ]
    ) {
      const absolutePath =
        join(
          this.projectRoot,
          name
        )

      if (
        existsSync(
          absolutePath
        )
      ) {
        result.push({
          source: 'PROJECT',
          absolutePath,
          relativePath:
            this.relativePath(
              absolutePath
            )
        })
      }
    }

    return result
  }

  private collectEvidenceFiles():
    CandidateFile[] {
    const result:
      CandidateFile[] = []

    const root =
      join(
        this.projectRoot,
        'EVIDENCE'
      )

    if (existsSync(root)) {
      this.walk(
        root,
        'EVIDENCE',
        EVIDENCE_EXTENSIONS,
        result,
        500
      )
    }

    return result
  }

  private walk(
    root: string,
    source: RetrievalSource,
    extensions: Set<string>,
    output: CandidateFile[],
    maxFiles: number
  ): void {
    if (
      output.length >=
      maxFiles
    ) {
      return
    }

    let entries:
      Dirent<string>[]

    try {
      entries =
        readdirSync(
          root,
          {
            withFileTypes: true
          }
        )
    } catch {
      return
    }

    for (
      const entry of entries
    ) {
      if (
        output.length >=
        maxFiles
      ) {
        break
      }

      if (
        entry.isDirectory() &&
        EXCLUDED_DIRECTORIES
          .has(entry.name)
      ) {
        continue
      }

      const absolutePath =
        join(
          root,
          entry.name
        )

      if (
        entry.isDirectory()
      ) {
        this.walk(
          absolutePath,
          source,
          extensions,
          output,
          maxFiles
        )
        continue
      }

      if (!entry.isFile()) {
        continue
      }

      const extension =
        extname(
          entry.name
        ).toLowerCase()

      if (
        !extensions.has(
          extension
        )
      ) {
        continue
      }

      try {
        if (
          statSync(
            absolutePath
          ).size >
          512 * 1024
        ) {
          continue
        }
      } catch {
        continue
      }

      output.push({
        source,
        absolutePath,
        relativePath:
          this.relativePath(
            absolutePath
          )
      })
    }
  }

  private searchFile(
    candidate:
      CandidateFile,
    phrase: string,
    tokens: string[]
  ): RetrievalHit | null {
    let text: string

    try {
      text =
        readFileSync(
          candidate.absolutePath,
          'utf-8'
        )
    } catch {
      return null
    }

    const lower =
      text.toLowerCase()

    const phraseLower =
      phrase.toLowerCase()

    let score = 0

    if (
      lower.includes(
        phraseLower
      )
    ) {
      score += 120
    }

    for (
      const token
      of tokens
    ) {
      const tokenLower =
        token.toLowerCase()

      const weight =
        this.tokenWeight(
          token
        )

      const count =
        lower.split(
          tokenLower
        ).length - 1

      if (count > 0) {
        score +=
          Math.min(
            count,
            4
          ) * weight
      }

      if (
        candidate.relativePath
          .toLowerCase()
          .includes(
            tokenLower
          )
      ) {
        score +=
          weight * 2
      }
    }

    if (score <= 0) {
      return null
    }

    const lines =
      text.split(
        /\r?\n/
      )

    let bestIndex = 0
    let bestLineScore = -1

    for (
      let index = 0;
      index < lines.length;
      index += 1
    ) {
      const line =
        lines[index]
          .toLowerCase()

      let lineScore =
        line.includes(
          phraseLower
        )
          ? 120
          : 0

      for (
        const token
        of tokens
      ) {
        if (
          line.includes(
            token.toLowerCase()
          )
        ) {
          lineScore +=
            this.tokenWeight(
              token
            )
        }
      }

      if (
        lineScore >
        bestLineScore
      ) {
        bestLineScore =
          lineScore
        bestIndex =
          index
      }
    }

    const start =
      Math.max(
        0,
        bestIndex - 2
      )

    const end =
      Math.min(
        lines.length,
        bestIndex + 3
      )

    const snippet =
      lines
        .slice(
          start,
          end
        )
        .join('\n')
        .trim()
        .slice(
          0,
          1800
        )

    return {
      source:
        candidate.source,
      relativePath:
        candidate.relativePath,
      lineStart:
        start + 1,
      lineEnd:
        end,
      snippet,
      score
    }
  }

  private tokenize(
    query: string
  ): string[] {
    const normalized =
      query.trim()

    const strongTerms:
      string[] = []

    const phraseMatch =
      normalized.match(
        /\bphrase\s+(.+?)(?:[.!?。！？]|$)/iu
      )

    if (
      phraseMatch?.[1]
    ) {
      strongTerms.push(
        phraseMatch[1].trim()
      )
    }

    for (
      const match
      of normalized.matchAll(
        /["'「『](.+?)["'」』]/gu
      )
    ) {
      if (
        match[1]
      ) {
        strongTerms.push(
          match[1].trim()
        )
      }
    }

    const stopWords =
      new Set([
        'the',
        'a',
        'an',
        'and',
        'or',
        'for',
        'to',
        'of',
        'in',
        'on',
        'with',
        'search',
        'find',
        'local',
        'project',
        'phrase',
        'state',
        'which',
        'document',
        'contains',
        'include',
        'token',
        'your',
        'answer',
        'it'
      ])

    const parts =
      normalized
        .split(
          /[\s,.!?;、。，．！？；:：/\\()[\]{}'"`]+/
        )
        .map(
          (item) =>
            item.trim()
        )
        .filter(
          (item) =>
            item.length >= 2
        )
        .filter(
          (item) =>
            !stopWords.has(
              item.toLowerCase()
            )
        )

    return [
      ...new Set(
        [
          ...strongTerms,
          ...parts
        ]
        .filter(Boolean)
      )
    ]
  }

  private tokenWeight(
    token: string
  ): number {
    if (
      /[^\x00-\x7F]/u.test(
        token
      )
    ) {
      return 400
    }

    if (
      token.length >= 16
    ) {
      return 90
    }

    if (
      token.length >= 10
    ) {
      return 55
    }

    if (
      token.length >= 7
    ) {
      return 28
    }

    return 8
  }

  private relativePath(
    absolutePath: string
  ): string {
    const root =
      resolve(
        this.projectRoot
      )

    const target =
      resolve(
        absolutePath
      )

    const value =
      relative(
        root,
        target
      )

    if (
      value.startsWith(
        '..'
      ) ||
      value.includes(
        `..${sep}`
      )
    ) {
      throw new Error(
        'RETRIEVAL_PATH_ESCAPED_PROJECT_ROOT'
      )
    }

    return value
      .split(sep)
      .join('/')
  }
}
