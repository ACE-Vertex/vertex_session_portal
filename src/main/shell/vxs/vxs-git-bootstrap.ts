// VXS_GIT_BOOTSTRAP_000068V3
import { spawnSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { app } from 'electron'
import type {
  VxsCommandContext,
  VxsCommandDispatchResult,
  VxsExecutionCommandResult
} from './vxs-command-registry'

type AutoAuthorityLease = {
  schema?: unknown
  authority_id?: unknown
  controller_session?: unknown
  allowed_sessions?: unknown
  granted_utc?: unknown
  expires_utc?: unknown
  status?: unknown
}

type AutoAuthorityLedger = {
  schema?: unknown
  authorities?: unknown
}

type ReadResult = {
  ok: boolean
  stdout: string
  stderr: string
  status: number | null
}

const AUTO_AUTHORITY_LEDGER_SCHEMA = 'vertex-session-portal/auto-authority-ledger-1'
const AUTO_AUTHORITY_SCHEMA = 'vertex-session-portal/auto-authority-1'
const BOOTSTRAP_REQUEST_SCHEMA = 'vertex-session-portal/vxs-git-bootstrap-request-1'
const ORIGIN_SESSION_PATTERN = /^vera-0[1-5]$/
const GITHUB_HTTPS = /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+(?:\.git)?$/i

function errorResult(message: string, hints: string[] = []): VxsCommandDispatchResult {
  return {
    kind: 'immediate',
    output: [
      `ERROR: ${message}`,
      ...hints,
      ''
    ].map(value => `${value}\n`).join(''),
    exitCode: 2,
    stream: 'stderr'
  }
}

function run(program: string, args: string[], cwd: string, timeoutMs = 15_000): ReadResult {
  try {
    const result = spawnSync(program, args, {
      cwd,
      encoding: 'utf8',
      windowsHide: true,
      shell: false,
      timeout: timeoutMs,
      maxBuffer: 4 * 1024 * 1024
    })
    return {
      ok: result.status === 0 && !result.error,
      stdout: String(result.stdout ?? '').trimEnd(),
      stderr: String(result.stderr ?? '').trimEnd(),
      status: result.status
    }
  } catch (error) {
    return {
      ok: false,
      stdout: '',
      stderr: error instanceof Error ? error.message : String(error),
      status: null
    }
  }
}

function readActiveAuthority(originSession: string): {
  authorityId: string
  expiresUtc: string
  ledgerPath: string
  auditPath: string
} | null {
  if (!ORIGIN_SESSION_PATTERN.test(originSession)) return null

  const stagingRoot = path.join(app.getPath('userData'), 'vra-dispatch')
  const ledgerPath = path.join(stagingRoot, 'auto-authorities.json')
  const auditPath = path.join(stagingRoot, 'vxs-git-bootstrap-audit.jsonl')
  if (!fs.existsSync(ledgerPath)) return null

  let parsed: AutoAuthorityLedger
  try {
    parsed = JSON.parse(fs.readFileSync(ledgerPath, 'utf8')) as AutoAuthorityLedger
  } catch {
    return null
  }
  if (parsed.schema !== AUTO_AUTHORITY_LEDGER_SCHEMA || !Array.isArray(parsed.authorities)) return null

  const now = Date.now()
  const candidates = (parsed.authorities as AutoAuthorityLease[])
    .filter(row => row && row.schema === AUTO_AUTHORITY_SCHEMA)
    .filter(row => row.status === 'ACTIVE')
    .filter(row => typeof row.authority_id === 'string' && row.authority_id.length > 0)
    .filter(row => typeof row.expires_utc === 'string')
    .filter(row => {
      const expires = Date.parse(String(row.expires_utc))
      return Number.isFinite(expires) && expires > now
    })
    .filter(row => Array.isArray(row.allowed_sessions) && row.allowed_sessions.includes(originSession))
    .sort((a, b) => Date.parse(String(b.granted_utc ?? '')) - Date.parse(String(a.granted_utc ?? '')))

  const lease = candidates[0]
  if (!lease) return null
  fs.mkdirSync(stagingRoot, { recursive: true })
  return {
    authorityId: String(lease.authority_id),
    expiresUtc: String(lease.expires_utc),
    ledgerPath,
    auditPath
  }
}

function psSingleQuote(value: string): string {
  return `'${value.replace(/'/g, "''")}'`
}

const BOOTSTRAP_POWERSHELL = String.raw`# VXS_GIT_BOOTSTRAP_000068V3
param(
  [Parameter(Mandatory=$true)]
  [string]$RequestBase64
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Emit([string]$Key, [object]$Value) {
  if ($null -eq $Value) { Write-Output ($Key + '=') }
  else { Write-Output ($Key + '=' + [string]$Value) }
}

function Read-Request([string]$Encoded) {
  $bytes = [Convert]::FromBase64String($Encoded)
  $json = [Text.Encoding]::UTF8.GetString($bytes)
  return $json | ConvertFrom-Json -Depth 40
}

function Invoke-Git {
  param(
    [Parameter(Mandatory=$true)]
    [string[]]$GitArgs,
    [switch]$AllowFailure
  )
  $lines = @(& git -C $script:ProjectRoot @GitArgs 2>&1)
  $code = $LASTEXITCODE
  $text = ($lines | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
  if ($code -ne 0 -and -not $AllowFailure) {
    throw ('GIT_FAILED:' + ($GitArgs -join ' ') + ':' + $text)
  }
  return [pscustomobject]@{ ExitCode = $code; Text = $text }
}

function Invoke-GitRemoteProbe {
  param([Parameter(Mandatory=$true)][string]$RemoteUrl)
  $lines = @(& git ls-remote $RemoteUrl 2>&1)
  $code = $LASTEXITCODE
  $text = ($lines | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
  if ($code -ne 0) { throw ('GIT_REMOTE_PROBE_FAILED:' + $text) }
  return $text.Trim()
}

function Assert-AutoAuthority {
  $ledgerPath = [string]$script:Request.ledger_path
  if (-not (Test-Path -LiteralPath $ledgerPath -PathType Leaf)) {
    throw 'AUTO_AUTHORITY_LEDGER_MISSING'
  }
  $ledger = Get-Content -LiteralPath $ledgerPath -Raw -Encoding UTF8 | ConvertFrom-Json -Depth 40
  if ([string]$ledger.schema -ne 'vertex-session-portal/auto-authority-ledger-1') {
    throw 'AUTO_AUTHORITY_LEDGER_SCHEMA_MISMATCH'
  }
  $lease = @($ledger.authorities | Where-Object {
    ([string]$_.authority_id -eq [string]$script:Request.authority_id) -and
    ([string]$_.schema -eq 'vertex-session-portal/auto-authority-1')
  } | Select-Object -Last 1)
  if ($lease.Count -ne 1) { throw 'AUTO_AUTHORITY_NOT_FOUND' }

  $row = $lease[0]
  if ([string]$row.status -ne 'ACTIVE') { throw 'AUTO_AUTHORITY_NOT_ACTIVE' }

  $expires = [DateTime]::Parse([string]$row.expires_utc).ToUniversalTime()
  if ($expires -le [DateTime]::UtcNow) { throw 'AUTO_AUTHORITY_EXPIRED' }

  $allowed = @($row.allowed_sessions | ForEach-Object { [string]$_ })
  if ($allowed -notcontains [string]$script:Request.origin_session) {
    throw 'AUTO_AUTHORITY_SESSION_OUT_OF_SCOPE'
  }
  if ([string]$row.expires_utc -ne [string]$script:Request.authority_expires_utc) {
    throw 'AUTO_AUTHORITY_EPOCH_CHANGED'
  }
  Emit 'AUTO_AUTHORITY' 'ACTIVE'
}

function Append-Audit([string]$Result, [string]$ErrorText) {
  try {
    $audit = [ordered]@{
      schema = 'vertex-session-portal/vxs-git-bootstrap-audit-1'
      request_id = [string]$script:Request.request_id
      at_utc = [DateTime]::UtcNow.ToString('o')
      origin_session = [string]$script:Request.origin_session
      authority_id = [string]$script:Request.authority_id
      project_root = [string]$script:Request.project_root
      remote_url = [string]$script:Request.remote_url
      result = $Result
      error = $ErrorText
    }
    [IO.File]::AppendAllText(
      [string]$script:Request.audit_path,
      ($audit | ConvertTo-Json -Compress -Depth 20) + [Environment]::NewLine,
      [Text.UTF8Encoding]::new($false)
    )
  } catch {
    Emit 'AUDIT_WRITE' 'FAILED'
  }
}

$script:Request = $null
$script:ProjectRoot = ''
$createdGit = $false
$lockStream = $null

try {
  $script:Request = Read-Request $RequestBase64
  if ([string]$script:Request.schema -ne 'vertex-session-portal/vxs-git-bootstrap-request-1') {
    throw 'REQUEST_SCHEMA_MISMATCH'
  }
  if ([string]$script:Request.origin_session -notmatch '^vera-0[1-5]$') {
    throw 'ORIGIN_SESSION_INVALID'
  }
  if ([string]$script:Request.remote_url -notmatch '^https://github\.com/[^/\s]+/[^/\s]+(?:\.git)?$') {
    throw 'REMOTE_URL_INVALID'
  }

  Assert-AutoAuthority

  $script:ProjectRoot = [IO.Path]::GetFullPath([string]$script:Request.project_root)
  if (-not (Test-Path -LiteralPath $script:ProjectRoot -PathType Container)) {
    throw 'PROJECT_ROOT_NOT_FOUND'
  }

  $lockPath = Join-Path (Split-Path -Parent ([string]$script:Request.ledger_path)) 'vxs-git-publish.lock'
  $lockStream = [IO.File]::Open(
    $lockPath,
    [IO.FileMode]::OpenOrCreate,
    [IO.FileAccess]::ReadWrite,
    [IO.FileShare]::None
  )

  $remoteRefs = Invoke-GitRemoteProbe -RemoteUrl ([string]$script:Request.remote_url)
  if (-not [string]::IsNullOrWhiteSpace($remoteRefs)) {
    throw 'REMOTE_NOT_EMPTY'
  }
  Emit 'REMOTE_EMPTY' 'YES'

  $existing = Invoke-Git -GitArgs @('rev-parse', '--show-toplevel') -AllowFailure
  if ($existing.ExitCode -eq 0) {
    $actual = [IO.Path]::GetFullPath($existing.Text.Trim())
    if (-not [string]::Equals(
      $actual.TrimEnd('\'),
      $script:ProjectRoot.TrimEnd('\'),
      [StringComparison]::OrdinalIgnoreCase
    )) {
      throw ('EXISTING_REPOSITORY_ROOT_MISMATCH:' + $actual)
    }
    $branch = (Invoke-Git -GitArgs @('symbolic-ref', '--short', 'HEAD')).Text.Trim()
    $remote = (Invoke-Git -GitArgs @('remote', 'get-url', 'origin')).Text.Trim()
    if ($branch -ne 'main') { throw ('EXISTING_BRANCH_MISMATCH:' + $branch) }
    if ($remote -ne [string]$script:Request.remote_url) { throw ('EXISTING_ORIGIN_MISMATCH:' + $remote) }

    Assert-AutoAuthority
    Append-Audit -Result 'ALREADY_CONFIGURED' -ErrorText ''
    Emit 'BOOTSTRAP' 'ALREADY_CONFIGURED'
    Emit 'BRANCH' $branch
    Emit 'ORIGIN' $remote
    exit 0
  }

  $gitPath = Join-Path $script:ProjectRoot '.git'
  if (Test-Path -LiteralPath $gitPath) {
    throw 'GIT_METADATA_PRESENT_BUT_INVALID'
  }

  Assert-AutoAuthority
  Invoke-Git -GitArgs @('init', '-b', 'main') | Out-Null
  $createdGit = $true
  Invoke-Git -GitArgs @('remote', 'add', 'origin', [string]$script:Request.remote_url) | Out-Null

  Assert-AutoAuthority

  $root = [IO.Path]::GetFullPath((Invoke-Git -GitArgs @('rev-parse', '--show-toplevel')).Text.Trim())
  if (-not [string]::Equals(
    $root.TrimEnd('\'),
    $script:ProjectRoot.TrimEnd('\'),
    [StringComparison]::OrdinalIgnoreCase
  )) {
    throw ('BOOTSTRAP_ROOT_VERIFY_FAILED:' + $root)
  }

  $branch = (Invoke-Git -GitArgs @('symbolic-ref', '--short', 'HEAD')).Text.Trim()
  if ($branch -ne 'main') { throw ('BOOTSTRAP_BRANCH_VERIFY_FAILED:' + $branch) }

  $remote = (Invoke-Git -GitArgs @('remote', 'get-url', 'origin')).Text.Trim()
  if ($remote -ne [string]$script:Request.remote_url) {
    throw ('BOOTSTRAP_ORIGIN_VERIFY_FAILED:' + $remote)
  }

  Append-Audit -Result 'BOOTSTRAPPED' -ErrorText ''
  Emit 'BOOTSTRAP' 'PASS'
  Emit 'BRANCH' $branch
  Emit 'ORIGIN' $remote
  exit 0
} catch {
  $message = $_.Exception.Message
  Emit 'BOOTSTRAP' 'FAILED'
  Emit 'ERROR' $message

  if ($createdGit -and -not [string]::IsNullOrWhiteSpace($script:ProjectRoot)) {
    try {
      $gitPath = Join-Path $script:ProjectRoot '.git'
      if (Test-Path -LiteralPath $gitPath) {
        Remove-Item -LiteralPath $gitPath -Recurse -Force
      }
      Emit 'ROLLBACK' 'REMOVED_CREATED_GIT_METADATA'
    } catch {
      Emit 'ROLLBACK' 'FAILED'
    }
  }

  if ($null -ne $script:Request) {
    Append-Audit -Result 'FAILED' -ErrorText $message
  }
  exit 1
} finally {
  if ($null -ne $lockStream) {
    $lockStream.Dispose()
  }
}
`

export function planVxsGitBootstrap(
  context: VxsCommandContext,
  projectRootCandidate: string,
  args: string[]
): VxsCommandDispatchResult {
  const originSession = String(args[0] ?? '').trim().toLowerCase()
  if (!ORIGIN_SESSION_PATTERN.test(originSession)) {
    return errorResult(
      'AUTO-gated Git bootstrap requires immutable VERA origin session.',
      ['Usage: vxs git bootstrap <vera-01..vera-05> <github-origin-url>']
    )
  }

  const remoteUrl = String(args[1] ?? '').trim()
  if (!GITHUB_HTTPS.test(remoteUrl)) {
    return errorResult(
      'Git bootstrap requires an HTTPS GitHub origin URL.',
      ['Example: https://github.com/OWNER/REPOSITORY.git']
    )
  }

  const root = path.resolve(projectRootCandidate)
  if (!fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
    return errorResult('Project root does not exist.', [`Candidate: ${root}`])
  }

  const authority = readActiveAuthority(originSession)
  if (!authority) {
    return errorResult(
      'ACTIVE Human AUTO authority was not found for this VERA session.',
      ['AUTO is the Human Gate. Turn AUTO ON before requesting Git bootstrap.']
    )
  }

  const probe = run('git', ['ls-remote', remoteUrl], root, 20_000)
  if (!probe.ok) {
    return errorResult(
      'Unable to read the requested GitHub origin.',
      [probe.stderr || probe.stdout || remoteUrl]
    )
  }
  if (probe.stdout.trim()) {
    return errorResult(
      'Git bootstrap is restricted to an empty remote repository.',
      ['Remote already contains refs; reconcile manually before bootstrap.']
    )
  }

  const stagingRoot = path.dirname(authority.ledgerPath)
  const toolRoot = path.join(stagingRoot, 'tools')
  fs.mkdirSync(toolRoot, { recursive: true })
  const toolPath = path.join(toolRoot, 'vxs-git-bootstrap.ps1')
  fs.writeFileSync(toolPath, BOOTSTRAP_POWERSHELL, { encoding: 'utf8' })

  const request = {
    schema: BOOTSTRAP_REQUEST_SCHEMA,
    request_id: randomUUID(),
    origin_session: originSession,
    authority_id: authority.authorityId,
    authority_expires_utc: authority.expiresUtc,
    project_root: root,
    remote_url: remoteUrl,
    ledger_path: authority.ledgerPath,
    audit_path: authority.auditPath,
  }

  const requestBase64 = Buffer.from(JSON.stringify(request), 'utf8').toString('base64')
  const executionCommand = `& ${psSingleQuote(toolPath)} -RequestBase64 ${psSingleQuote(requestBase64)}`

  const result: VxsExecutionCommandResult = {
    kind: 'execute',
    executionCommand,
    executionCwd: root,
    capability: 'GIT',
    routeSummary: `${context.canonicalName} Git bootstrap under ACTIVE Human AUTO authority (${originSession})`
  }
  return result
}
