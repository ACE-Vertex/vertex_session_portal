// VXS_AUTO_GIT_PUBLISH_000065V3
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
import type { VxsWorkspaceInfo } from './vxs-workspace-detector'

type GitMutationMode = 'commit' | 'push' | 'publish'

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

type ReadOnlyGitResult = {
  ok: boolean
  stdout: string
  stderr: string
  status: number | null
}

const AUTO_AUTHORITY_LEDGER_SCHEMA = 'vertex-session-portal/auto-authority-ledger-1'
const AUTO_AUTHORITY_SCHEMA = 'vertex-session-portal/auto-authority-1'
const GIT_REQUEST_SCHEMA = 'vertex-session-portal/vxs-git-auto-request-1'
const ORIGIN_SESSION_PATTERN = /^vera-0[1-5]$/
const GITHUB_HTTPS = /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+(?:\.git)?$/i
const GITHUB_SSH = /^(?:git@github\.com:|ssh:\/\/git@github\.com\/)[^/\s]+\/[^/\s]+(?:\.git)?$/i

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

function normalizeStatusSnapshot(value: string): string {
  return value
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map(line => line.trimEnd())
    .filter(line => line.length > 0)
    .join('\n')
}

function runGitReadOnly(root: string, args: string[], timeoutMs = 15_000): ReadOnlyGitResult {
  try {
    const result = spawnSync(
      'git',
      ['-C', root, ...args],
      {
        encoding: 'utf8',
        windowsHide: true,
        shell: false,
        timeout: timeoutMs,
        maxBuffer: 4 * 1024 * 1024
      }
    )

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
  const auditPath = path.join(stagingRoot, 'vxs-git-publish-audit.jsonl')

  if (!fs.existsSync(ledgerPath)) return null

  let parsed: AutoAuthorityLedger
  try {
    parsed = JSON.parse(fs.readFileSync(ledgerPath, 'utf8')) as AutoAuthorityLedger
  } catch {
    return null
  }

  if (parsed.schema !== AUTO_AUTHORITY_LEDGER_SCHEMA || !Array.isArray(parsed.authorities)) {
    return null
  }

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

function isGithubRemote(remote: string): boolean {
  return GITHUB_HTTPS.test(remote) || GITHUB_SSH.test(remote)
}

const AUTO_GIT_POWERSHELL = String.raw`# VXS_AUTO_GIT_PUBLISH_000065V3
param(
  [Parameter(Mandatory=$true)]
  [string]$RequestBase64
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Emit([string]$Key, [object]$Value) {
  if ($null -eq $Value) {
    Write-Output ($Key + '=')
  } else {
    Write-Output ($Key + '=' + [string]$Value)
  }
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

  $lines = @(& git -C $script:RepoRoot @GitArgs 2>&1)
  $code = $LASTEXITCODE
  $text = ($lines | ForEach-Object { [string]$_ }) -join [Environment]::NewLine

  if ($code -ne 0 -and -not $AllowFailure) {
    throw ('GIT_FAILED:' + ($GitArgs -join ' ') + ':' + $text)
  }

  return [pscustomobject]@{
    ExitCode = $code
    Text = $text
  }
}

function Invoke-External {
  param(
    [Parameter(Mandatory=$true)]
    [string]$Program,
    [Parameter(Mandatory=$true)]
    [string[]]$Arguments
  )

  $lines = @(& $Program @Arguments 2>&1)
  $code = $LASTEXITCODE
  foreach ($line in $lines) {
    Write-Output ([string]$line)
  }
  if ($code -ne 0) {
    throw ('VERIFY_COMMAND_FAILED:' + $Program + ' ' + ($Arguments -join ' '))
  }
}

function Normalize-Status([string]$Text) {
  $rows = @($Text -split '\r?\n' | ForEach-Object { $_.TrimEnd() } | Where-Object { $_.Length -gt 0 })
  return ($rows -join [char]10)
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

  if ($lease.Count -ne 1) {
    throw 'AUTO_AUTHORITY_NOT_FOUND'
  }

  $row = $lease[0]
  if ([string]$row.status -ne 'ACTIVE') {
    throw 'AUTO_AUTHORITY_NOT_ACTIVE'
  }

  $expires = [DateTime]::Parse([string]$row.expires_utc).ToUniversalTime()
  if ($expires -le [DateTime]::UtcNow) {
    throw 'AUTO_AUTHORITY_EXPIRED'
  }

  $allowed = @($row.allowed_sessions | ForEach-Object { [string]$_ })
  if ($allowed -notcontains [string]$script:Request.origin_session) {
    throw 'AUTO_AUTHORITY_SESSION_OUT_OF_SCOPE'
  }

  if ([string]$row.expires_utc -ne [string]$script:Request.authority_expires_utc) {
    throw 'AUTO_AUTHORITY_EPOCH_CHANGED'
  }

  Emit 'AUTO_AUTHORITY' 'ACTIVE'
  Emit 'AUTHORITY_ID' ([string]$row.authority_id)
}

function Resolve-Repository {
  $resolved = Invoke-Git -GitArgs @('rev-parse', '--show-toplevel')
  $actual = [IO.Path]::GetFullPath($resolved.Text.Trim())
  $expected = [IO.Path]::GetFullPath([string]$script:Request.repo_root)

  if (-not [string]::Equals($actual.TrimEnd('\'), $expected.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
    throw ('REPOSITORY_ROOT_DRIFT:' + $actual)
  }

  $script:RepoRoot = $actual

  $branch = (Invoke-Git -GitArgs @('branch', '--show-current')).Text.Trim()
  if ([string]::IsNullOrWhiteSpace($branch)) {
    throw 'DETACHED_HEAD_FORBIDDEN'
  }
  if ($branch -ne [string]$script:Request.expected_branch) {
    throw ('BRANCH_DRIFT:' + $branch)
  }

  $remote = (Invoke-Git -GitArgs @('remote', 'get-url', 'origin')).Text.Trim()
  if ($remote -ne [string]$script:Request.expected_remote_url) {
    throw 'REMOTE_DRIFT'
  }

  if (
    $remote -notmatch '^https://github\.com/[^/\s]+/[^/\s]+(?:\.git)?$' -and
    $remote -notmatch '^(?:git@github\.com:|ssh://git@github\.com/)[^/\s]+/[^/\s]+(?:\.git)?$'
  ) {
    throw 'NON_GITHUB_REMOTE_FORBIDDEN'
  }

  $headRead = Invoke-Git -GitArgs @('rev-parse', '--verify', 'HEAD') -AllowFailure
  $head = if ($headRead.ExitCode -eq 0) { $headRead.Text.Trim() } else { '' }

  if ($head -ne [string]$script:Request.expected_head) {
    throw 'HEAD_DRIFT'
  }

  $status = Normalize-Status ((Invoke-Git -GitArgs @('status', '--porcelain=v1', '--untracked-files=all')).Text)
  if ($status -ne [string]$script:Request.expected_status) {
    throw 'WORKTREE_DRIFT'
  }

  $conflicts = (Invoke-Git -GitArgs @('diff', '--name-only', '--diff-filter=U')).Text.Trim()
  if (-not [string]::IsNullOrWhiteSpace($conflicts)) {
    throw 'MERGE_CONFLICT_PRESENT'
  }

  $stagedBefore = (Invoke-Git -GitArgs @('diff', '--cached', '--name-only')).Text.Trim()
  if (-not [string]::IsNullOrWhiteSpace($stagedBefore)) {
    throw 'PREEXISTING_STAGED_CHANGES_FORBIDDEN'
  }

  Emit 'REPOSITORY' $actual
  Emit 'BRANCH' $branch
  Emit 'REMOTE' $remote
  Emit 'EXPECTED_HEAD' $head
}

function Get-RemoteHead {
  $branch = [string]$script:Request.expected_branch
  $ref = 'refs/heads/' + $branch
  $probe = Invoke-Git -GitArgs @('ls-remote', '--heads', 'origin', $ref)
  $line = $probe.Text.Trim()
  if ([string]::IsNullOrWhiteSpace($line)) {
    return ''
  }
  return ($line -split '\s+')[0]
}

function Assert-RemoteAncestor([string]$RemoteHead, [string]$LocalHead) {
  if ([string]::IsNullOrWhiteSpace($RemoteHead)) {
    return
  }
  if ([string]::IsNullOrWhiteSpace($LocalHead)) {
    throw 'REMOTE_EXISTS_BUT_LOCAL_HEAD_MISSING'
  }

  Invoke-Git -GitArgs @('fetch', '--no-tags', 'origin', [string]$script:Request.expected_branch) | Out-Null
  $ancestor = Invoke-Git -GitArgs @('merge-base', '--is-ancestor', $RemoteHead, $LocalHead) -AllowFailure
  if ($ancestor.ExitCode -ne 0) {
    throw 'REMOTE_NOT_ANCESTOR_OF_LOCAL_HEAD'
  }
}

function Invoke-Verification {
  $count = 0
  $verification = $script:Request.verification
  $scripts = @($verification.scripts | ForEach-Object { [string]$_ })
  $markers = @($verification.markers | ForEach-Object { [string]$_ })
  $pm = [string]$verification.package_manager

  if (-not [string]::IsNullOrWhiteSpace($pm)) {
    $program = if ($IsWindows) { $pm + '.cmd' } else { $pm }
    foreach ($name in @('typecheck', 'check', 'test', 'build')) {
      if ($scripts -contains $name) {
        Emit 'VERIFY_STEP' ($program + ' run ' + $name)
        Invoke-External -Program $program -Arguments @('run', $name)
        $count += 1
      }
    }
  }

  if ($markers -contains 'Cargo.toml') {
    Emit 'VERIFY_STEP' 'cargo check'
    Invoke-External -Program 'cargo' -Arguments @('check')
    $count += 1
    Emit 'VERIFY_STEP' 'cargo test'
    Invoke-External -Program 'cargo' -Arguments @('test')
    $count += 1
  }

  if (
    $count -eq 0 -and
    (
      $markers -contains 'pyproject.toml' -or
      $markers -contains 'requirements.txt' -or
      $markers -contains 'setup.py'
    )
  ) {
    Emit 'VERIFY_STEP' 'python -m pytest'
    Invoke-External -Program 'python' -Arguments @('-m', 'pytest')
    $count += 1
  }

  if ($count -eq 0) {
    throw 'NO_SUPPORTED_VERIFICATION_PIPELINE'
  }

  Emit 'VERIFY' 'PASS'
  Emit 'VERIFY_COMMAND_COUNT' $count
}

function Assert-StagedPathsSafe {
  $staged = @((Invoke-Git -GitArgs @('diff', '--cached', '--name-only', '--diff-filter=ACMRDT')).Text -split '\r?\n' | Where-Object { $_.Length -gt 0 })
  $blocked = @()

  foreach ($item in $staged) {
    $normalized = ([string]$item).Replace('\', '/')
    if (
      $normalized -match '(^|/)\.env($|\.)' -or
      $normalized -match '\.(pem|key|pfx|p12)$' -or
      $normalized -match '(^|/)(id_rsa|id_ed25519)$' -or
      $normalized -match '(^|/)(credentials|service-account)[^/]*\.json$'
    ) {
      $blocked += $normalized
    }
  }

  if ($blocked.Count -gt 0) {
    foreach ($item in $blocked) {
      Emit 'BLOCKED_PATH' $item
    }
    throw 'SENSITIVE_PATH_STAGED'
  }

  Emit 'STAGED_FILES' $staged.Count
}

function Append-Audit([string]$Result, [string]$ErrorText) {
  try {
    $audit = [ordered]@{
      schema = 'vertex-session-portal/vxs-git-publish-audit-1'
      timestamp = [DateTime]::UtcNow.ToString('o')
      request_id = [string]$script:Request.request_id
      authority_id = [string]$script:Request.authority_id
      origin_session = [string]$script:Request.origin_session
      mode = [string]$script:Request.mode
      repo_root = [string]$script:Request.repo_root
      branch = [string]$script:Request.expected_branch
      remote = [string]$script:Request.expected_remote_url
      before_remote_head = $script:RemoteBefore
      local_head = $script:LocalHead
      after_remote_head = $script:RemoteAfter
      commit_created = $script:CommitCreated
      result = $Result
      error = $ErrorText
    }
    $json = $audit | ConvertTo-Json -Compress -Depth 20
    [IO.File]::AppendAllText(
      [string]$script:Request.audit_path,
      $json + [Environment]::NewLine,
      [Text.UTF8Encoding]::new($false)
    )
  } catch {
    Emit 'AUDIT_WRITE' 'FAILED'
  }
}

$script:Request = $null
$script:RepoRoot = ''
$script:RemoteBefore = ''
$script:RemoteAfter = ''
$script:LocalHead = ''
$script:CommitCreated = $false
$script:IndexMutated = $false
$lockStream = $null
$locationPushed = $false

try {
  $script:Request = Read-Request $RequestBase64

  if ([string]$script:Request.schema -ne 'vertex-session-portal/vxs-git-auto-request-1') {
    throw 'REQUEST_SCHEMA_MISMATCH'
  }
  if ([string]$script:Request.mode -notin @('commit', 'push', 'publish')) {
    throw 'REQUEST_MODE_INVALID'
  }
  if ([string]$script:Request.origin_session -notmatch '^vera-0[1-5]$') {
    throw 'ORIGIN_SESSION_INVALID'
  }

  Assert-AutoAuthority

  $lockPath = Join-Path (Split-Path -Parent ([string]$script:Request.ledger_path)) 'vxs-git-publish.lock'
  $lockStream = [IO.File]::Open(
    $lockPath,
    [IO.FileMode]::OpenOrCreate,
    [IO.FileAccess]::ReadWrite,
    [IO.FileShare]::None
  )

  $script:RepoRoot = [string]$script:Request.repo_root
  Resolve-Repository

  Push-Location -LiteralPath $script:RepoRoot
  $locationPushed = $true

  $script:RemoteBefore = Get-RemoteHead
  Emit 'REMOTE_HEAD_BEFORE' $script:RemoteBefore

  $initialHead = [string]$script:Request.expected_head
  Assert-RemoteAncestor -RemoteHead $script:RemoteBefore -LocalHead $initialHead

  if ([string]$script:Request.mode -eq 'push') {
    if (-not [string]::IsNullOrWhiteSpace([string]$script:Request.expected_status)) {
      throw 'PUSH_ONLY_REQUIRES_CLEAN_WORKTREE'
    }
    if ([string]::IsNullOrWhiteSpace($initialHead)) {
      throw 'PUSH_ONLY_REQUIRES_LOCAL_HEAD'
    }
    $script:LocalHead = $initialHead
  } else {
    Invoke-Verification

    $statusAfterVerify = Normalize-Status ((Invoke-Git -GitArgs @('status', '--porcelain=v1', '--untracked-files=all')).Text)
    if ($statusAfterVerify -ne [string]$script:Request.expected_status) {
      throw 'WORKTREE_CHANGED_DURING_VERIFY'
    }

    Assert-AutoAuthority

    $script:IndexMutated = $true
    Invoke-Git -GitArgs @('add', '-A') | Out-Null
    Assert-StagedPathsSafe

    $staged = (Invoke-Git -GitArgs @('diff', '--cached', '--name-only')).Text.Trim()
    if (-not [string]::IsNullOrWhiteSpace($staged)) {
      $message = [string]$script:Request.commit_message
      if ([string]::IsNullOrWhiteSpace($message)) {
        throw 'COMMIT_MESSAGE_REQUIRED'
      }
      if ($message.Length -gt 240 -or $message.Contains([char]10) -or $message.Contains([char]13)) {
        throw 'COMMIT_MESSAGE_INVALID'
      }
      Invoke-Git -GitArgs @('commit', '-m', $message) | Out-Null
      $script:CommitCreated = $true
      $script:IndexMutated = $false
      Emit 'COMMIT' 'CREATED'
    } else {
      $script:IndexMutated = $false
      Emit 'COMMIT' 'NO_CHANGES'
    }

    $headRead = Invoke-Git -GitArgs @('rev-parse', '--verify', 'HEAD') -AllowFailure
    if ($headRead.ExitCode -ne 0) {
      throw 'LOCAL_HEAD_MISSING_AFTER_COMMIT'
    }
    $script:LocalHead = $headRead.Text.Trim()
    Emit 'LOCAL_HEAD' $script:LocalHead
  }

  if ([string]$script:Request.mode -eq 'commit') {
    Append-Audit -Result 'COMMITTED' -ErrorText ''
    Emit 'RESULT' 'COMMITTED'
    exit 0
  }

  Assert-AutoAuthority

  $remoteNow = Get-RemoteHead
  if ($remoteNow -ne $script:RemoteBefore) {
    throw 'REMOTE_HEAD_CHANGED_DURING_OPERATION'
  }

  Assert-RemoteAncestor -RemoteHead $remoteNow -LocalHead $script:LocalHead

  $refspec = ('{0}:{0}' -f [string]$script:Request.expected_branch)
  Invoke-Git -GitArgs @('push', '--dry-run', 'origin', $refspec) | Out-Null
  Emit 'PUSH_DRY_RUN' 'PASS'

  Assert-AutoAuthority
  Invoke-Git -GitArgs @('push', 'origin', $refspec) | Out-Null
  Emit 'PUSH' 'PASS'

  $script:RemoteAfter = Get-RemoteHead
  Emit 'REMOTE_HEAD_AFTER' $script:RemoteAfter

  if ($script:RemoteAfter -ne $script:LocalHead) {
    throw 'REMOTE_HEAD_VERIFY_FAILED'
  }

  Append-Audit -Result 'PUBLISHED' -ErrorText ''
  Emit 'REMOTE_VERIFY' 'PASS'
  Emit 'RESULT' 'PUBLISHED'
  exit 0
} catch {
  $message = $_.Exception.Message
  Emit 'RESULT' 'FAILED'
  Emit 'ERROR' $message

  if ($script:IndexMutated -and -not $script:CommitCreated -and -not [string]::IsNullOrWhiteSpace($script:RepoRoot)) {
    try {
      Invoke-Git -GitArgs @('reset', '--mixed') -AllowFailure | Out-Null
      Emit 'INDEX_RECOVERY' 'ATTEMPTED'
    } catch {
      Emit 'INDEX_RECOVERY' 'FAILED'
    }
  }

  if ($null -ne $script:Request) {
    Append-Audit -Result 'FAILED' -ErrorText $message
  }
  exit 1
} finally {
  if ($locationPushed) {
    Pop-Location
  }
  if ($null -ne $lockStream) {
    $lockStream.Dispose()
  }
}
`

function resolveRepositoryRoot(candidate: string): {
  root: string
  branch: string
  remote: string
  head: string
  statusSnapshot: string
  stagedPaths: string
} | null {
  const rootProbe = runGitReadOnly(candidate, ['rev-parse', '--show-toplevel'])
  if (!rootProbe.ok || !rootProbe.stdout.trim()) return null

  const root = path.resolve(rootProbe.stdout.trim())
  const branchProbe = runGitReadOnly(root, ['branch', '--show-current'])
  const remoteProbe = runGitReadOnly(root, ['remote', 'get-url', 'origin'])
  const headProbe = runGitReadOnly(root, ['rev-parse', '--verify', 'HEAD'])
  const statusProbe = runGitReadOnly(root, ['status', '--porcelain=v1', '--untracked-files=all'])
  const stagedProbe = runGitReadOnly(root, ['diff', '--cached', '--name-only'])

  if (!branchProbe.ok || !branchProbe.stdout.trim()) return null
  if (!remoteProbe.ok || !remoteProbe.stdout.trim()) return null
  if (!statusProbe.ok || !stagedProbe.ok) return null

  return {
    root,
    branch: branchProbe.stdout.trim(),
    remote: remoteProbe.stdout.trim(),
    head: headProbe.ok ? headProbe.stdout.trim() : '',
    statusSnapshot: normalizeStatusSnapshot(statusProbe.stdout),
    stagedPaths: stagedProbe.stdout.trim()
  }
}

export function planVxsAutoGitMutation(
  context: VxsCommandContext,
  gitRootCandidate: string,
  mode: GitMutationMode,
  args: string[],
  workspace: VxsWorkspaceInfo
): VxsCommandDispatchResult {
  const originSession = String(args[0] ?? '').trim().toLowerCase()
  if (!ORIGIN_SESSION_PATTERN.test(originSession)) {
    return errorResult(
      'AUTO-gated Git mutation requires immutable VERA origin session.',
      [`Usage: vxs git ${mode} <vera-01..vera-05>${mode === 'push' ? '' : ' <commit message>'}`]
    )
  }

  const commitMessage = args.slice(1).join(' ').trim()
  if ((mode === 'commit' || mode === 'publish') && !commitMessage) {
    return errorResult(
      'Commit message is required.',
      [`Usage: vxs git ${mode} ${originSession} <commit message>`]
    )
  }

  if (commitMessage.length > 240 || /[\r\n]/.test(commitMessage)) {
    return errorResult('Commit message must be one line and at most 240 characters.')
  }

  const authority = readActiveAuthority(originSession)
  if (!authority) {
    return errorResult(
      'ACTIVE Human AUTO authority was not found for this VERA session.',
      ['AUTO is the Human Gate. Turn AUTO ON before requesting Git mutation.']
    )
  }

  const repository = resolveRepositoryRoot(gitRootCandidate)
  if (!repository) {
    return errorResult(
      'Unable to resolve a branch-attached Git repository with origin.',
      [`Candidate: ${gitRootCandidate}`]
    )
  }

  if (repository.stagedPaths) {
    return errorResult(
      'Pre-existing staged changes are forbidden for AUTO Git mutation.',
      ['Commit or unstage the existing index before retrying.']
    )
  }

  if (!isGithubRemote(repository.remote)) {
    return errorResult(
      'Git mutation is restricted to an existing GitHub origin remote.',
      [`Origin: ${repository.remote}`]
    )
  }

  if (mode === 'push' && repository.statusSnapshot) {
    return errorResult(
      'vxs git push requires a clean worktree.',
      ['Use vxs git publish <session> <message> to verify, commit, and push current changes.']
    )
  }

  const stagingRoot = path.dirname(authority.ledgerPath)
  const toolRoot = path.join(stagingRoot, 'tools')
  fs.mkdirSync(toolRoot, { recursive: true })

  const toolPath = path.join(toolRoot, 'vxs-git-auto-publish.ps1')
  fs.writeFileSync(toolPath, AUTO_GIT_POWERSHELL, { encoding: 'utf8' })

  const request = {
    schema: GIT_REQUEST_SCHEMA,
    request_id: randomUUID(),
    mode,
    origin_session: originSession,
    authority_id: authority.authorityId,
    authority_expires_utc: authority.expiresUtc,
    repo_root: repository.root,
    expected_branch: repository.branch,
    expected_remote_url: repository.remote,
    expected_head: repository.head,
    expected_status: repository.statusSnapshot,
    commit_message: commitMessage,
    ledger_path: authority.ledgerPath,
    audit_path: authority.auditPath,
    verification: {
      package_manager: workspace.packageManager,
      scripts: [...workspace.scripts],
      markers: [...workspace.markers]
    }
  }

  const requestBase64 = Buffer.from(JSON.stringify(request), 'utf8').toString('base64')
  const executionCommand = `& ${psSingleQuote(toolPath)} -RequestBase64 ${psSingleQuote(requestBase64)}`

  const result: VxsExecutionCommandResult = {
    kind: 'execute',
    executionCommand,
    executionCwd: repository.root,
    capability: 'GIT',
    routeSummary: `${context.canonicalName} Git ${mode} under ACTIVE Human AUTO authority (${originSession})`
  }

  return result
}
