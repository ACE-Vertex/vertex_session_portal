var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __esm = (fn, res) => function __init() {
  return fn && (res = (0, fn[__getOwnPropNames(fn)[0]])(fn = 0)), res;
};
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// src/main/shell/vxs/vera-vxs-human-authority.ts
function snapshot() {
  return { ...state };
}
function isVeraVxsHumanFullAccessGranted() {
  return state.granted && state.mode === "FULL" && state.grantedBy === "HUMAN";
}
function grantVeraVxsHumanFullAccess() {
  state = {
    ...state,
    mode: "FULL",
    granted: true,
    generation: state.generation + 1,
    grantedAt: (/* @__PURE__ */ new Date()).toISOString(),
    grantedBy: "HUMAN"
  };
  return snapshot();
}
function revokeVeraVxsHumanFullAccess() {
  state = {
    ...state,
    mode: "LOCKED",
    granted: false,
    generation: state.generation + 1,
    grantedAt: null,
    grantedBy: null
  };
  return snapshot();
}
var VERA_VXS_HUMAN_AUTHORITY_SCHEMA, state;
var init_vera_vxs_human_authority = __esm({
  "src/main/shell/vxs/vera-vxs-human-authority.ts"() {
    VERA_VXS_HUMAN_AUTHORITY_SCHEMA = "vertex-vxs/human-authority-1";
    state = {
      schema: VERA_VXS_HUMAN_AUTHORITY_SCHEMA,
      mode: "LOCKED",
      granted: false,
      generation: 0,
      grantedAt: null,
      grantedBy: null,
      scope: "VERA_FULL_ACCESS",
      persistence: "PROCESS"
    };
  }
});

// src/shared/vera-vxs-contracts.ts
var VERA_VXS_REQUEST_SCHEMA, VERA_VXS_RESULT_SCHEMA;
var init_vera_vxs_contracts = __esm({
  "src/shared/vera-vxs-contracts.ts"() {
    VERA_VXS_REQUEST_SCHEMA = "vertex-vxs/vera-request-1";
    VERA_VXS_RESULT_SCHEMA = "vertex-vxs/vera-result-1";
  }
});

// src/main/shell/vxs/vera-vxs-interface.ts
var vera_vxs_interface_exports = {};
__export(vera_vxs_interface_exports, {
  executeVeraVxsRequest: () => executeVeraVxsRequest
});
function requiredText(value, field, max = 512) {
  if (typeof value !== "string") {
    throw new Error(`VERA_VXS_INVALID_${field.toUpperCase()}`);
  }
  const trimmed = value.trim();
  if (!trimmed || trimmed.length > max) {
    throw new Error(`VERA_VXS_INVALID_${field.toUpperCase()}`);
  }
  return trimmed;
}
function validateOrigin(origin) {
  if (!origin || typeof origin !== "object") {
    throw new Error("VERA_VXS_INVALID_ORIGIN");
  }
  const vera = requiredText(origin.vera, "origin_vera", 32).toUpperCase();
  const session = requiredText(origin.session, "origin_session", 32).toLowerCase();
  const window = requiredText(origin.window, "origin_window", 32).toLowerCase();
  const veraMatch = /^VERA(\d{2})$/.exec(vera);
  const sessionMatch = /^vera-(\d{2})$/.exec(session);
  const windowMatch = /^vera-(\d{2})$/.exec(window);
  if (!veraMatch || !sessionMatch || !windowMatch) {
    throw new Error("VERA_VXS_INVALID_ORIGIN");
  }
  if (veraMatch[1] !== sessionMatch[1] || veraMatch[1] !== windowMatch[1]) {
    throw new Error("VERA_VXS_ORIGIN_MISMATCH");
  }
  return { vera, session, window };
}
function normalizeRequest(input) {
  if (!input || typeof input !== "object") {
    throw new Error("VERA_VXS_REQUEST_REQUIRED");
  }
  if (input.schema !== VERA_VXS_REQUEST_SCHEMA) {
    throw new Error("VERA_VXS_SCHEMA_UNSUPPORTED");
  }
  const requestId = requiredText(input.requestId, "request_id", 256);
  const correlationId = requiredText(input.correlationId, "correlation_id", 256);
  const origin = validateOrigin(input.origin);
  if (input.authority !== "AUTO_SAFE" && input.authority !== "HUMAN_APPLY") {
    throw new Error("VERA_VXS_INVALID_AUTHORITY");
  }
  const command = requiredText(input.command, "command", MAX_COMMAND_CHARS2);
  if (!isVeraVxsHumanFullAccessGranted() && !/^vxs(?:\s|$)/i.test(command)) {
    throw new Error("VERA_VXS_CANONICAL_VXS_COMMAND_REQUIRED");
  }
  const cwd = input.cwd === void 0 ? void 0 : requiredText(input.cwd, "cwd", 4096);
  return {
    schema: VERA_VXS_REQUEST_SCHEMA,
    requestId,
    correlationId,
    origin,
    authority: input.authority,
    command,
    ...cwd ? { cwd } : {}
  };
}
async function executeVeraVxsRequest(executor, input) {
  if (!isVeraVxsHumanFullAccessGranted()) {
    throw new Error("VERA_VXS_HUMAN_GATE_REQUIRED");
  }
  const request2 = normalizeRequest(input);
  const acceptedAt = (/* @__PURE__ */ new Date()).toISOString();
  const streamEvents = [];
  let streamBytes = 0;
  let streamTruncated = false;
  const sink = (event) => {
    if (streamTruncated) return;
    const eventBytes = Buffer.byteLength(event.chunk ?? "", "utf8");
    if (streamBytes + eventBytes > MAX_RETURN_STREAM_BYTES) {
      streamTruncated = true;
      return;
    }
    streamBytes += eventBytes;
    streamEvents.push(event);
  };
  const shellRequest = {
    command: request2.command,
    ...request2.cwd ? { cwd: request2.cwd } : {}
  };
  const shellResult = await executor.execute(shellRequest, sink);
  return {
    schema: VERA_VXS_RESULT_SCHEMA,
    requestId: request2.requestId,
    correlationId: request2.correlationId,
    origin: request2.origin,
    requestedAuthority: request2.authority,
    authorityEnforcement: "VXS_EXISTING_POLICY",
    transport: "VERTEX_SHELL_SERVICE",
    acceptedAt,
    completedAt: (/* @__PURE__ */ new Date()).toISOString(),
    streamBytes,
    streamTruncated,
    streamEvents,
    shellResult
  };
}
var MAX_COMMAND_CHARS2, MAX_RETURN_STREAM_BYTES;
var init_vera_vxs_interface = __esm({
  "src/main/shell/vxs/vera-vxs-interface.ts"() {
    init_vera_vxs_human_authority();
    init_vera_vxs_contracts();
    MAX_COMMAND_CHARS2 = 32e3;
    MAX_RETURN_STREAM_BYTES = 512 * 1024;
  }
});

// scripts/vera_vxs_human_full_access_e2e_000088V4.ts
var import_electron5 = require("electron");
var fs15 = __toESM(require("node:fs"), 1);
var path16 = __toESM(require("node:path"), 1);

// src/main/shell/vertex-shell-service.ts
var import_electron3 = require("electron");
var import_node_child_process9 = require("node:child_process");
var import_node_crypto4 = require("node:crypto");

// src/main/shell/vxs/vxs-command-registry.ts
var import_node_child_process8 = require("node:child_process");
var fs13 = __toESM(require("node:fs"), 1);

// src/main/shell/vxs/vxs-workspace-detector.ts
var fs = __toESM(require("node:fs"), 1);
var path = __toESM(require("node:path"), 1);
var WORKSPACE_MARKERS = [
  "package.json",
  "Cargo.toml",
  "pyproject.toml",
  "requirements.txt",
  "setup.py",
  ".git"
];
function exists(candidate) {
  try {
    return fs.existsSync(candidate);
  } catch {
    return false;
  }
}
function readJsonObject(candidate) {
  try {
    const parsed = JSON.parse(fs.readFileSync(candidate, "utf8"));
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
function stringProperty(record, key) {
  const value = record?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
function objectProperty(record, key) {
  const value = record?.[key];
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
function nearestWorkspaceRoot(start) {
  let current = path.resolve(start);
  while (true) {
    if (WORKSPACE_MARKERS.some((marker) => exists(path.join(current, marker)))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) return path.resolve(start);
    current = parent;
  }
}
function detectPackageManager(root) {
  if (exists(path.join(root, "pnpm-lock.yaml"))) return "pnpm";
  if (exists(path.join(root, "yarn.lock"))) return "yarn";
  if (exists(path.join(root, "package-lock.json"))) return "npm";
  if (exists(path.join(root, "package.json"))) return "npm";
  return null;
}
function detectFrameworks(packageJson) {
  if (!packageJson) return [];
  const deps = {
    ...objectProperty(packageJson, "dependencies"),
    ...objectProperty(packageJson, "devDependencies")
  };
  const known = [
    ["electron", "Electron"],
    ["vue", "Vue"],
    ["react", "React"],
    ["typescript", "TypeScript"],
    ["vite", "Vite"],
    ["@electron-vite/cli", "electron-vite"],
    ["electron-vite", "electron-vite"],
    ["quasar", "Quasar"],
    ["@quasar/extras", "Quasar"]
  ];
  const found = [];
  for (const [dependency, label] of known) {
    if (dependency in deps && !found.includes(label)) found.push(label);
  }
  return found;
}
function detectScripts(packageJson) {
  const scripts = objectProperty(packageJson, "scripts");
  return Object.keys(scripts).sort();
}
function detectVxsWorkspace(cwd) {
  const resolvedCwd = path.resolve(cwd);
  const root = nearestWorkspaceRoot(resolvedCwd);
  const markers = WORKSPACE_MARKERS.filter(
    (marker) => exists(path.join(root, marker))
  );
  const hasNode = markers.includes("package.json");
  const hasRust = markers.includes("Cargo.toml");
  const hasPython = markers.includes("pyproject.toml") || markers.includes("requirements.txt") || markers.includes("setup.py");
  const kinds = [hasNode, hasRust, hasPython].filter(Boolean).length;
  const kind = kinds > 1 ? "mixed" : hasNode ? "node" : hasRust ? "rust" : hasPython ? "python" : "directory";
  const packageJson = hasNode ? readJsonObject(path.join(root, "package.json")) : null;
  return {
    cwd: resolvedCwd,
    root,
    kind,
    markers,
    packageManager: detectPackageManager(root),
    packageName: stringProperty(packageJson, "name"),
    packageVersion: stringProperty(packageJson, "version"),
    frameworks: detectFrameworks(packageJson),
    scripts: detectScripts(packageJson),
    git: exists(path.join(root, ".git"))
  };
}

// src/main/shell/vxs/vxs-dev-capabilities.ts
var path4 = __toESM(require("node:path"), 1);

// src/main/shell/vxs/vxs-git-auto-publish.ts
var import_node_child_process = require("node:child_process");
var import_node_crypto = require("node:crypto");
var fs2 = __toESM(require("node:fs"), 1);
var path2 = __toESM(require("node:path"), 1);
var import_electron = require("electron");
var AUTO_AUTHORITY_LEDGER_SCHEMA = "vertex-session-portal/auto-authority-ledger-1";
var AUTO_AUTHORITY_SCHEMA = "vertex-session-portal/auto-authority-1";
var GIT_REQUEST_SCHEMA = "vertex-session-portal/vxs-git-auto-request-1";
var ORIGIN_SESSION_PATTERN = /^vera-0[1-5]$/;
var GITHUB_HTTPS = /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+(?:\.git)?$/i;
var GITHUB_SSH = /^(?:git@github\.com:|ssh:\/\/git@github\.com\/)[^/\s]+\/[^/\s]+(?:\.git)?$/i;
function errorResult(message, hints = []) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      ...hints,
      ""
    ].map((value) => `${value}
`).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function normalizeStatusSnapshot(value) {
  return value.replace(/\r\n/g, "\n").split("\n").map((line20) => line20.trimEnd()).filter((line20) => line20.length > 0).join("\n");
}
function runGitReadOnly(root, args, timeoutMs = 15e3) {
  try {
    const result = (0, import_node_child_process.spawnSync)(
      "git",
      ["-C", root, ...args],
      {
        encoding: "utf8",
        windowsHide: true,
        shell: false,
        timeout: timeoutMs,
        maxBuffer: 4 * 1024 * 1024
      }
    );
    return {
      ok: result.status === 0 && !result.error,
      stdout: String(result.stdout ?? "").trimEnd(),
      stderr: String(result.stderr ?? "").trimEnd(),
      status: result.status
    };
  } catch (error2) {
    return {
      ok: false,
      stdout: "",
      stderr: error2 instanceof Error ? error2.message : String(error2),
      status: null
    };
  }
}
function readActiveAuthority(originSession) {
  if (!ORIGIN_SESSION_PATTERN.test(originSession)) return null;
  const stagingRoot = path2.join(import_electron.app.getPath("userData"), "vra-dispatch");
  const ledgerPath = path2.join(stagingRoot, "auto-authorities.json");
  const auditPath = path2.join(stagingRoot, "vxs-git-publish-audit.jsonl");
  if (!fs2.existsSync(ledgerPath)) return null;
  let parsed;
  try {
    parsed = JSON.parse(fs2.readFileSync(ledgerPath, "utf8"));
  } catch {
    return null;
  }
  if (parsed.schema !== AUTO_AUTHORITY_LEDGER_SCHEMA || !Array.isArray(parsed.authorities)) {
    return null;
  }
  const now = Date.now();
  const candidates = parsed.authorities.filter((row) => row && row.schema === AUTO_AUTHORITY_SCHEMA).filter((row) => row.status === "ACTIVE").filter((row) => typeof row.authority_id === "string" && row.authority_id.length > 0).filter((row) => typeof row.expires_utc === "string").filter((row) => {
    const expires = Date.parse(String(row.expires_utc));
    return Number.isFinite(expires) && expires > now;
  }).filter((row) => Array.isArray(row.allowed_sessions) && row.allowed_sessions.includes(originSession)).sort((a, b) => Date.parse(String(b.granted_utc ?? "")) - Date.parse(String(a.granted_utc ?? "")));
  const lease = candidates[0];
  if (!lease) return null;
  fs2.mkdirSync(stagingRoot, { recursive: true });
  return {
    authorityId: String(lease.authority_id),
    expiresUtc: String(lease.expires_utc),
    ledgerPath,
    auditPath
  };
}
function psSingleQuote(value) {
  return `'${value.replace(/'/g, "''")}'`;
}
function isGithubRemote(remote) {
  return GITHUB_HTTPS.test(remote) || GITHUB_SSH.test(remote);
}
var AUTO_GIT_POWERSHELL = String.raw`# VXS_AUTO_GIT_PUBLISH_000065V3
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
`;
function resolveRepositoryRoot(candidate) {
  const rootProbe = runGitReadOnly(candidate, ["rev-parse", "--show-toplevel"]);
  if (!rootProbe.ok || !rootProbe.stdout.trim()) return null;
  const root = path2.resolve(rootProbe.stdout.trim());
  const branchProbe = runGitReadOnly(root, ["branch", "--show-current"]);
  const remoteProbe = runGitReadOnly(root, ["remote", "get-url", "origin"]);
  const headProbe = runGitReadOnly(root, ["rev-parse", "--verify", "HEAD"]);
  const statusProbe = runGitReadOnly(root, ["status", "--porcelain=v1", "--untracked-files=all"]);
  const stagedProbe = runGitReadOnly(root, ["diff", "--cached", "--name-only"]);
  if (!branchProbe.ok || !branchProbe.stdout.trim()) return null;
  if (!remoteProbe.ok || !remoteProbe.stdout.trim()) return null;
  if (!statusProbe.ok || !stagedProbe.ok) return null;
  return {
    root,
    branch: branchProbe.stdout.trim(),
    remote: remoteProbe.stdout.trim(),
    head: headProbe.ok ? headProbe.stdout.trim() : "",
    statusSnapshot: normalizeStatusSnapshot(statusProbe.stdout),
    stagedPaths: stagedProbe.stdout.trim()
  };
}
function planVxsAutoGitMutation(context, gitRootCandidate, mode, args, workspace) {
  const originSession = String(args[0] ?? "").trim().toLowerCase();
  if (!ORIGIN_SESSION_PATTERN.test(originSession)) {
    return errorResult(
      "AUTO-gated Git mutation requires immutable VERA origin session.",
      [`Usage: vxs git ${mode} <vera-01..vera-05>${mode === "push" ? "" : " <commit message>"}`]
    );
  }
  const commitMessage = args.slice(1).join(" ").trim();
  if ((mode === "commit" || mode === "publish") && !commitMessage) {
    return errorResult(
      "Commit message is required.",
      [`Usage: vxs git ${mode} ${originSession} <commit message>`]
    );
  }
  if (commitMessage.length > 240 || /[\r\n]/.test(commitMessage)) {
    return errorResult("Commit message must be one line and at most 240 characters.");
  }
  const authority = readActiveAuthority(originSession);
  if (!authority) {
    return errorResult(
      "ACTIVE Human AUTO authority was not found for this VERA session.",
      ["AUTO is the Human Gate. Turn AUTO ON before requesting Git mutation."]
    );
  }
  const repository = resolveRepositoryRoot(gitRootCandidate);
  if (!repository) {
    return errorResult(
      "Unable to resolve a branch-attached Git repository with origin.",
      [`Candidate: ${gitRootCandidate}`]
    );
  }
  if (repository.stagedPaths) {
    return errorResult(
      "Pre-existing staged changes are forbidden for AUTO Git mutation.",
      ["Commit or unstage the existing index before retrying."]
    );
  }
  if (!isGithubRemote(repository.remote)) {
    return errorResult(
      "Git mutation is restricted to an existing GitHub origin remote.",
      [`Origin: ${repository.remote}`]
    );
  }
  if (mode === "push" && repository.statusSnapshot) {
    return errorResult(
      "vxs git push requires a clean worktree.",
      ["Use vxs git publish <session> <message> to verify, commit, and push current changes."]
    );
  }
  const stagingRoot = path2.dirname(authority.ledgerPath);
  const toolRoot = path2.join(stagingRoot, "tools");
  fs2.mkdirSync(toolRoot, { recursive: true });
  const toolPath = path2.join(toolRoot, "vxs-git-auto-publish.ps1");
  fs2.writeFileSync(toolPath, AUTO_GIT_POWERSHELL, { encoding: "utf8" });
  const request2 = {
    schema: GIT_REQUEST_SCHEMA,
    request_id: (0, import_node_crypto.randomUUID)(),
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
  };
  const requestBase64 = Buffer.from(JSON.stringify(request2), "utf8").toString("base64");
  const executionCommand = `& ${psSingleQuote(toolPath)} -RequestBase64 ${psSingleQuote(requestBase64)}`;
  const result = {
    kind: "execute",
    executionCommand,
    executionCwd: repository.root,
    capability: "GIT",
    routeSummary: `${context.canonicalName} Git ${mode} under ACTIVE Human AUTO authority (${originSession})`
  };
  return result;
}

// src/main/shell/vxs/vxs-git-bootstrap.ts
var import_node_child_process2 = require("node:child_process");
var import_node_crypto2 = require("node:crypto");
var fs3 = __toESM(require("node:fs"), 1);
var path3 = __toESM(require("node:path"), 1);
var import_electron2 = require("electron");
var AUTO_AUTHORITY_LEDGER_SCHEMA2 = "vertex-session-portal/auto-authority-ledger-1";
var AUTO_AUTHORITY_SCHEMA2 = "vertex-session-portal/auto-authority-1";
var BOOTSTRAP_REQUEST_SCHEMA = "vertex-session-portal/vxs-git-bootstrap-request-1";
var ORIGIN_SESSION_PATTERN2 = /^vera-0[1-5]$/;
var GITHUB_HTTPS2 = /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+(?:\.git)?$/i;
function errorResult2(message, hints = []) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      ...hints,
      ""
    ].map((value) => `${value}
`).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function run(program, args, cwd, timeoutMs = 15e3) {
  try {
    const result = (0, import_node_child_process2.spawnSync)(program, args, {
      cwd,
      encoding: "utf8",
      windowsHide: true,
      shell: false,
      timeout: timeoutMs,
      maxBuffer: 4 * 1024 * 1024
    });
    return {
      ok: result.status === 0 && !result.error,
      stdout: String(result.stdout ?? "").trimEnd(),
      stderr: String(result.stderr ?? "").trimEnd(),
      status: result.status
    };
  } catch (error2) {
    return {
      ok: false,
      stdout: "",
      stderr: error2 instanceof Error ? error2.message : String(error2),
      status: null
    };
  }
}
function readActiveAuthority2(originSession) {
  if (!ORIGIN_SESSION_PATTERN2.test(originSession)) return null;
  const stagingRoot = path3.join(import_electron2.app.getPath("userData"), "vra-dispatch");
  const ledgerPath = path3.join(stagingRoot, "auto-authorities.json");
  const auditPath = path3.join(stagingRoot, "vxs-git-bootstrap-audit.jsonl");
  if (!fs3.existsSync(ledgerPath)) return null;
  let parsed;
  try {
    parsed = JSON.parse(fs3.readFileSync(ledgerPath, "utf8"));
  } catch {
    return null;
  }
  if (parsed.schema !== AUTO_AUTHORITY_LEDGER_SCHEMA2 || !Array.isArray(parsed.authorities)) return null;
  const now = Date.now();
  const candidates = parsed.authorities.filter((row) => row && row.schema === AUTO_AUTHORITY_SCHEMA2).filter((row) => row.status === "ACTIVE").filter((row) => typeof row.authority_id === "string" && row.authority_id.length > 0).filter((row) => typeof row.expires_utc === "string").filter((row) => {
    const expires = Date.parse(String(row.expires_utc));
    return Number.isFinite(expires) && expires > now;
  }).filter((row) => Array.isArray(row.allowed_sessions) && row.allowed_sessions.includes(originSession)).sort((a, b) => Date.parse(String(b.granted_utc ?? "")) - Date.parse(String(a.granted_utc ?? "")));
  const lease = candidates[0];
  if (!lease) return null;
  fs3.mkdirSync(stagingRoot, { recursive: true });
  return {
    authorityId: String(lease.authority_id),
    expiresUtc: String(lease.expires_utc),
    ledgerPath,
    auditPath
  };
}
function psSingleQuote2(value) {
  return `'${value.replace(/'/g, "''")}'`;
}
var BOOTSTRAP_POWERSHELL = String.raw`# VXS_GIT_BOOTSTRAP_000068V3
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
`;
function planVxsGitBootstrap(context, projectRootCandidate, args) {
  const originSession = String(args[0] ?? "").trim().toLowerCase();
  if (!ORIGIN_SESSION_PATTERN2.test(originSession)) {
    return errorResult2(
      "AUTO-gated Git bootstrap requires immutable VERA origin session.",
      ["Usage: vxs git bootstrap <vera-01..vera-05> <github-origin-url>"]
    );
  }
  const remoteUrl = String(args[1] ?? "").trim();
  if (!GITHUB_HTTPS2.test(remoteUrl)) {
    return errorResult2(
      "Git bootstrap requires an HTTPS GitHub origin URL.",
      ["Example: https://github.com/OWNER/REPOSITORY.git"]
    );
  }
  const root = path3.resolve(projectRootCandidate);
  if (!fs3.existsSync(root) || !fs3.statSync(root).isDirectory()) {
    return errorResult2("Project root does not exist.", [`Candidate: ${root}`]);
  }
  const authority = readActiveAuthority2(originSession);
  if (!authority) {
    return errorResult2(
      "ACTIVE Human AUTO authority was not found for this VERA session.",
      ["AUTO is the Human Gate. Turn AUTO ON before requesting Git bootstrap."]
    );
  }
  const probe = run("git", ["ls-remote", remoteUrl], root, 2e4);
  if (!probe.ok) {
    return errorResult2(
      "Unable to read the requested GitHub origin.",
      [probe.stderr || probe.stdout || remoteUrl]
    );
  }
  if (probe.stdout.trim()) {
    return errorResult2(
      "Git bootstrap is restricted to an empty remote repository.",
      ["Remote already contains refs; reconcile manually before bootstrap."]
    );
  }
  const stagingRoot = path3.dirname(authority.ledgerPath);
  const toolRoot = path3.join(stagingRoot, "tools");
  fs3.mkdirSync(toolRoot, { recursive: true });
  const toolPath = path3.join(toolRoot, "vxs-git-bootstrap.ps1");
  fs3.writeFileSync(toolPath, BOOTSTRAP_POWERSHELL, { encoding: "utf8" });
  const request2 = {
    schema: BOOTSTRAP_REQUEST_SCHEMA,
    request_id: (0, import_node_crypto2.randomUUID)(),
    origin_session: originSession,
    authority_id: authority.authorityId,
    authority_expires_utc: authority.expiresUtc,
    project_root: root,
    remote_url: remoteUrl,
    ledger_path: authority.ledgerPath,
    audit_path: authority.auditPath
  };
  const requestBase64 = Buffer.from(JSON.stringify(request2), "utf8").toString("base64");
  const executionCommand = `& ${psSingleQuote2(toolPath)} -RequestBase64 ${psSingleQuote2(requestBase64)}`;
  const result = {
    kind: "execute",
    executionCommand,
    executionCwd: root,
    capability: "GIT",
    routeSummary: `${context.canonicalName} Git bootstrap under ACTIVE Human AUTO authority (${originSession})`
  };
  return result;
}

// src/main/shell/vxs/vxs-dev-capabilities.ts
function line(value = "") {
  return `${value}
`;
}
function immediateError(message, hints = []) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      ...hints,
      ""
    ].map(line).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function packageExecutable(packageManager) {
  if (process.platform !== "win32") return packageManager;
  return `${packageManager}.cmd`;
}
function nodeScriptPlan(workspace, script, capability) {
  if (!workspace.packageManager) return null;
  if (!workspace.scripts.includes(script)) return null;
  const executable = packageExecutable(workspace.packageManager);
  return {
    kind: "execute",
    executionCommand: `${executable} run ${script}`,
    executionCwd: workspace.root,
    capability,
    routeSummary: `${workspace.packageManager} script '${script}'`
  };
}
function workspaceHas(workspace, marker) {
  return workspace.markers.includes(marker);
}
function buildPlan(workspace) {
  const node = nodeScriptPlan(workspace, "build", "BUILD");
  if (node) return node;
  if (workspaceHas(workspace, "Cargo.toml")) {
    return {
      kind: "execute",
      executionCommand: "cargo build",
      executionCwd: workspace.root,
      capability: "BUILD",
      routeSummary: "Cargo build"
    };
  }
  if (workspaceHas(workspace, "pyproject.toml")) {
    return {
      kind: "execute",
      executionCommand: "python -m build",
      executionCwd: workspace.root,
      capability: "BUILD",
      routeSummary: "Python package build"
    };
  }
  return immediateError(
    "No supported build capability detected for this workspace.",
    [
      `Workspace Root: ${workspace.root}`,
      "Expected: package.json build script, Cargo.toml, or pyproject.toml"
    ]
  );
}
function testPlan(workspace) {
  const node = nodeScriptPlan(workspace, "test", "TEST");
  if (node) return node;
  if (workspaceHas(workspace, "Cargo.toml")) {
    return {
      kind: "execute",
      executionCommand: "cargo test",
      executionCwd: workspace.root,
      capability: "TEST",
      routeSummary: "Cargo test"
    };
  }
  if (workspaceHas(workspace, "pyproject.toml") || workspaceHas(workspace, "requirements.txt") || workspaceHas(workspace, "setup.py")) {
    return {
      kind: "execute",
      executionCommand: "python -m pytest",
      executionCwd: workspace.root,
      capability: "TEST",
      routeSummary: "Python pytest"
    };
  }
  return immediateError(
    "No supported test capability detected for this workspace.",
    [`Workspace Root: ${workspace.root}`]
  );
}
function lintPlan(workspace) {
  const node = nodeScriptPlan(workspace, "lint", "LINT");
  if (node) return node;
  if (workspaceHas(workspace, "Cargo.toml")) {
    return {
      kind: "execute",
      executionCommand: "cargo clippy --all-targets",
      executionCwd: workspace.root,
      capability: "LINT",
      routeSummary: "Cargo clippy"
    };
  }
  if (workspaceHas(workspace, "pyproject.toml") || workspaceHas(workspace, "requirements.txt") || workspaceHas(workspace, "setup.py")) {
    return {
      kind: "execute",
      executionCommand: "python -m ruff check .",
      executionCwd: workspace.root,
      capability: "LINT",
      routeSummary: "Python Ruff"
    };
  }
  return immediateError(
    "No supported lint capability detected for this workspace.",
    [`Workspace Root: ${workspace.root}`]
  );
}
function runScriptPlan(workspace, args) {
  if (!workspace.packageManager) {
    return immediateError(
      "vxs run currently requires a Node workspace with a package manager."
    );
  }
  const script = args[0]?.trim() ?? "";
  if (!script) {
    return {
      kind: "immediate",
      output: [
        "VXS RUN",
        `Workspace Root: ${workspace.root}`,
        `Package Manager: ${workspace.packageManager}`,
        `Scripts: ${workspace.scripts.length ? workspace.scripts.join(", ") : "none"}`,
        "",
        "Usage: vxs run <script>",
        ""
      ].map(line).join(""),
      exitCode: 0,
      stream: "system"
    };
  }
  if (!/^[A-Za-z0-9:_-]+$/.test(script)) {
    return immediateError(
      `Invalid package script name '${script}'.`
    );
  }
  if (!workspace.scripts.includes(script)) {
    return immediateError(
      `Package script '${script}' was not found.`,
      [
        `Available: ${workspace.scripts.length ? workspace.scripts.join(", ") : "none"}`
      ]
    );
  }
  const plan = nodeScriptPlan(workspace, script, "RUN");
  return plan ?? immediateError(`Unable to route package script '${script}'.`);
}
function gitPlan(context, args) {
  const subcommand = (args[0] ?? "status").toLowerCase();
  const workspace = detectVxsWorkspace(context.cwd);
  const gitRoot = workspace.git ? workspace.root : context.cwd;
  if (subcommand === "bootstrap") {
    return planVxsGitBootstrap(
      context,
      path4.resolve(gitRoot),
      args.slice(1)
    );
  }
  if (subcommand === "commit" || subcommand === "push" || subcommand === "publish") {
    return planVxsAutoGitMutation(
      context,
      path4.resolve(gitRoot),
      subcommand,
      args.slice(1),
      workspace
    );
  }
  const fixed = {
    status: {
      command: "git status --short --branch",
      summary: "Git status"
    },
    diff: {
      command: "git diff",
      summary: "Git working-tree diff"
    },
    staged: {
      command: "git diff --staged",
      summary: "Git staged diff"
    },
    branch: {
      command: "git branch --show-current",
      summary: "Git current branch"
    },
    log: {
      command: "git log --oneline -10",
      summary: "Git recent log"
    }
  };
  if (subcommand === "help" || subcommand === "--help") {
    return {
      kind: "immediate",
      output: [
        "VXS GIT \xB7 OBSERVE + AUTO-GATED MUTATION",
        "",
        "  vxs git status                         Short status + branch",
        "  vxs git diff                           Working-tree diff",
        "  vxs git staged                         Staged diff",
        "  vxs git branch                         Current branch",
        "  vxs git log                            Last 10 commits",
        "",
        "AUTO Human Gate mutation:",
        "  vxs git bootstrap <vera-01..vera-05> <github-origin-url>",
        "  vxs git commit <vera-01..vera-05> <message>",
        "  vxs git push <vera-01..vera-05>",
        "  vxs git publish <vera-01..vera-05> <message>",
        "",
        "bootstrap = AUTO-authorized git init(main) + GitHub origin registration only",
        "publish = verify -> stage -> commit -> dry-run push -> push -> remote HEAD verify",
        "AUTO OFF / expired / out-of-scope = fail closed.",
        "Force push and remote mutation are not supported.",
        ""
      ].map(line).join(""),
      exitCode: 0,
      stream: "system"
    };
  }
  const selected = fixed[subcommand];
  if (!selected) {
    return immediateError(
      `Unsupported vxs git command '${subcommand}'.`,
      ["Run: vxs git help"]
    );
  }
  return {
    kind: "execute",
    executionCommand: selected.command,
    executionCwd: path4.resolve(gitRoot),
    capability: "GIT",
    routeSummary: selected.summary
  };
}
function buildCommand(_args, context) {
  return buildPlan(detectVxsWorkspace(context.cwd));
}
function testCommand(_args, context) {
  return testPlan(detectVxsWorkspace(context.cwd));
}
function lintCommand(_args, context) {
  return lintPlan(detectVxsWorkspace(context.cwd));
}
function runCommand(args, context) {
  return runScriptPlan(detectVxsWorkspace(context.cwd), args);
}
function gitCommand(args, context) {
  return gitPlan(context, args);
}
function workspaceCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  return {
    kind: "immediate",
    output: [
      "VXS WORKSPACE",
      `CWD: ${workspace.cwd}`,
      `Root: ${workspace.root}`,
      `Type: ${workspace.kind}`,
      `Markers: ${workspace.markers.length ? workspace.markers.join(", ") : "none"}`,
      `Package Manager: ${workspace.packageManager ?? "not detected"}`,
      `Package: ${workspace.packageName ?? "not detected"}`,
      `Version: ${workspace.packageVersion ?? "not detected"}`,
      `Frameworks: ${workspace.frameworks.length ? workspace.frameworks.join(", ") : "none detected"}`,
      `Git: ${workspace.git ? "detected" : "not detected"}`,
      `Scripts: ${workspace.scripts.length ? workspace.scripts.join(", ") : "none detected"}`,
      ""
    ].map(line).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function scriptsCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  if (!workspace.packageManager) {
    return immediateError(
      "No Node package manager was detected for this workspace.",
      [`Workspace Root: ${workspace.root}`]
    );
  }
  return {
    kind: "immediate",
    output: [
      "VXS SCRIPTS",
      `Workspace Root: ${workspace.root}`,
      `Package Manager: ${workspace.packageManager}`,
      "",
      ...workspace.scripts.length ? workspace.scripts.map((script) => `  ${script}`) : ["  (no package scripts detected)"],
      ""
    ].map(line).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function checkCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  for (const script of ["typecheck", "check"]) {
    const plan = nodeScriptPlan(workspace, script, "CHECK");
    if (plan) return plan;
  }
  if (workspaceHas(workspace, "Cargo.toml")) {
    return {
      kind: "execute",
      executionCommand: "cargo check",
      executionCwd: workspace.root,
      capability: "CHECK",
      routeSummary: "Cargo check"
    };
  }
  if (workspaceHas(workspace, "pyproject.toml") || workspaceHas(workspace, "requirements.txt") || workspaceHas(workspace, "setup.py")) {
    return {
      kind: "execute",
      executionCommand: "python -m ruff check .",
      executionCwd: workspace.root,
      capability: "CHECK",
      routeSummary: "Python Ruff check"
    };
  }
  return immediateError(
    "No supported non-mutating code check was detected.",
    [
      `Workspace Root: ${workspace.root}`,
      "Expected: Node typecheck/check script, Cargo.toml, or Python workspace"
    ]
  );
}
function formatCheckCommand(args, context) {
  const requested = (args[0] ?? "").toLowerCase();
  if (requested !== "--check") {
    return immediateError(
      "Formatting mutation is not enabled in this pack.",
      ["Usage: vxs format --check"]
    );
  }
  const workspace = detectVxsWorkspace(context.cwd);
  for (const script of ["format:check", "format-check", "prettier:check"]) {
    const plan = nodeScriptPlan(workspace, script, "FORMAT_CHECK");
    if (plan) return plan;
  }
  if (workspaceHas(workspace, "Cargo.toml")) {
    return {
      kind: "execute",
      executionCommand: "cargo fmt --all -- --check",
      executionCwd: workspace.root,
      capability: "FORMAT_CHECK",
      routeSummary: "Cargo fmt check"
    };
  }
  if (workspaceHas(workspace, "pyproject.toml") || workspaceHas(workspace, "requirements.txt") || workspaceHas(workspace, "setup.py")) {
    return {
      kind: "execute",
      executionCommand: "python -m ruff format --check .",
      executionCwd: workspace.root,
      capability: "FORMAT_CHECK",
      routeSummary: "Python Ruff format check"
    };
  }
  return immediateError(
    "No supported formatting check was detected.",
    [
      `Workspace Root: ${workspace.root}`,
      "Expected: Node format-check script, Cargo.toml, or Python workspace"
    ]
  );
}
function createVxsDevelopmentCommands() {
  return [
    {
      name: "workspace",
      aliases: ["ws-info"],
      usage: "vxs workspace",
      summary: "Show detected workspace details",
      execute: workspaceCommand
    },
    {
      name: "scripts",
      aliases: [],
      usage: "vxs scripts",
      summary: "List detected Node package scripts",
      execute: scriptsCommand
    },
    {
      name: "check",
      aliases: [],
      usage: "vxs check",
      summary: "Auto-route non-mutating code checks",
      execute: checkCommand
    },
    {
      name: "format",
      aliases: [],
      usage: "vxs format --check",
      summary: "Verify formatting without rewriting files",
      execute: formatCheckCommand
    },
    {
      name: "build",
      aliases: [],
      usage: "vxs build",
      summary: "Auto-route the workspace build",
      execute: buildCommand
    },
    {
      name: "test",
      aliases: [],
      usage: "vxs test",
      summary: "Auto-route the workspace test suite",
      execute: testCommand
    },
    {
      name: "lint",
      aliases: [],
      usage: "vxs lint",
      summary: "Auto-route the workspace linter",
      execute: lintCommand
    },
    {
      name: "run",
      aliases: [],
      usage: "vxs run <script>",
      summary: "Run a detected Node package script",
      execute: runCommand
    },
    {
      name: "git",
      aliases: [],
      usage: "vxs git <status|diff|staged|branch|log|bootstrap|commit|push|publish>",
      summary: "Git observation plus AUTO Human Gate bootstrap/commit/push/publish",
      execute: gitCommand
    }
  ];
}

// src/main/shell/vxs/vxs-native-capabilities.ts
function psQuote(value) {
  return `'${value.replace(/'/g, "''")}'`;
}
function cleanTarget(args) {
  const joined = args.join(" ").trim();
  return joined.replace(/^(['"])(.*)\1$/, "$2");
}
function systemCommand(args, context) {
  const subcommand = (args[0] ?? "observe").toLowerCase();
  if (subcommand !== "observe") {
    return {
      kind: "immediate",
      output: [
        `Unsupported vxs system command '${subcommand}'.`,
        "Usage: vxs system observe"
      ].join("\n"),
      exitCode: 2,
      stream: "stderr"
    };
  }
  const result = {
    kind: "execute",
    executionCommand: "$PSVersionTable | Select-Object PSEdition,PSVersion,Platform,OS | ConvertTo-Json -Compress",
    executionCwd: context.cwd,
    capability: "NATIVE_SYSTEM_OBSERVE",
    routeSummary: "Native-first Rust SYSTEM observer with PowerShell fallback",
    providerRequest: {
      resource: "SYSTEM",
      action: "OBSERVE",
      authority: "AUTO_SAFE"
    }
  };
  return result;
}
function filesystemCommand(args, context) {
  const subcommand = (args[0] ?? "").toLowerCase();
  const target = cleanTarget(args.slice(1));
  if (!["exists", "meta", "list"].includes(subcommand) || !target) {
    return {
      kind: "immediate",
      output: [
        "Usage:",
        "  vxs fs exists <path>",
        "  vxs fs meta <path>",
        "  vxs fs list <path>"
      ].join("\n"),
      exitCode: 2,
      stream: "stderr"
    };
  }
  const quoted = psQuote(target);
  if (subcommand === "exists") {
    return {
      kind: "execute",
      executionCommand: `Test-Path -LiteralPath ${quoted}`,
      executionCwd: context.cwd,
      capability: "NATIVE_FILESYSTEM_EXISTS",
      routeSummary: "Native-first Rust FILESYSTEM exists with PowerShell fallback",
      providerRequest: {
        resource: "FILESYSTEM",
        action: "TEST",
        target,
        authority: "AUTO_SAFE"
      }
    };
  }
  if (subcommand === "meta") {
    return {
      kind: "execute",
      executionCommand: `Get-Item -LiteralPath ${quoted} | Select-Object FullName,Name,Length,Attributes,LastWriteTime | ConvertTo-Json -Compress`,
      executionCwd: context.cwd,
      capability: "NATIVE_FILESYSTEM_METADATA",
      routeSummary: "Native-first Rust FILESYSTEM metadata with PowerShell fallback",
      providerRequest: {
        resource: "FILESYSTEM",
        action: "OBSERVE",
        target,
        authority: "AUTO_SAFE"
      }
    };
  }
  return {
    kind: "execute",
    executionCommand: `Get-ChildItem -LiteralPath ${quoted} | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress`,
    executionCwd: context.cwd,
    capability: "NATIVE_FILESYSTEM_LIST",
    routeSummary: "Native-first Rust FILESYSTEM list with PowerShell fallback",
    providerRequest: {
      resource: "FILESYSTEM",
      action: "FIND",
      target,
      authority: "AUTO_SAFE"
    }
  };
}
function createVxsNativeCommands() {
  return [
    {
      name: "system",
      aliases: ["sys"],
      usage: "vxs system observe",
      summary: "Observe the local system through the Native-first provider route",
      execute: systemCommand
    },
    {
      name: "fs",
      aliases: ["filesystem"],
      usage: "vxs fs <exists|meta|list> <path>",
      summary: "Observe filesystem state through the Native-first provider route",
      execute: filesystemCommand
    }
  ];
}

// src/main/shell/vxs/vxs-vertex-capabilities.ts
var path5 = __toESM(require("node:path"), 1);

// src/main/shell/vxs/vxs-workstation-read-adapter.ts
var VXS_WORKSTATION_READ_CONTRACT = "vertex-vxs/workstation-read-adapter-1";
var VXS_WORKSTATION_BASE_URL = "http://127.0.0.1:47832";
var VXS_WORKSTATION_AUTHORITY_CLASS = "OBSERVE";
var VXS_WORKSTATION_DURABLE_ROOTS = Object.freeze({
  jobRegistry: "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry",
  evidence: "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\evidence",
  lanes: "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\lanes",
  portalDispatch: "G:\\Vertex_Project\\Development\\vertex_session_portal"
});
var DEFAULT_PORTAL_ROOT = "G:\\Vertex_Project\\Development\\vertex_session_portal";
var JOB_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$/;
function psSingleQuote3(value) {
  return `'${value.replaceAll("'", "''")}'`;
}
function isValidVxsWorkstationJobId(value) {
  return JOB_ID_PATTERN.test(value);
}
function describeVxsWorkstationHttpRead(urlPath) {
  return {
    contract: VXS_WORKSTATION_READ_CONTRACT,
    authorityClass: VXS_WORKSTATION_AUTHORITY_CLASS,
    channel: "HTTP_CONTROL_PLANE",
    operation: "GET",
    target: `${VXS_WORKSTATION_BASE_URL}${urlPath}`,
    mutation: false
  };
}
function describeVxsWorkstationDurableRead(operation, target) {
  return {
    contract: VXS_WORKSTATION_READ_CONTRACT,
    authorityClass: VXS_WORKSTATION_AUTHORITY_CLASS,
    channel: "DURABLE_FILESYSTEM_OBSERVATION",
    operation,
    target,
    mutation: false
  };
}
var VxsWorkstationReadAdapter = class {
  constructor(portalRoot = DEFAULT_PORTAL_ROOT) {
    this.portalRoot = portalRoot;
  }
  contract = VXS_WORKSTATION_READ_CONTRACT;
  authorityClass = VXS_WORKSTATION_AUTHORITY_CLASS;
  baseUrl = VXS_WORKSTATION_BASE_URL;
  health() {
    return this.getJson("/v1/health", "WORKSTATION", "GET /v1/health");
  }
  safety() {
    return this.getJson("/v1/safety", "WORKSTATION", "GET /v1/safety");
  }
  job(jobId) {
    if (!isValidVxsWorkstationJobId(jobId)) {
      return this.invalidJobId("vxs workstation job <job-id>");
    }
    return this.getJson(
      `/v1/jobs/${encodeURIComponent(jobId)}`,
      "WORKSTATION",
      `GET /v1/jobs/${jobId}`
    );
  }
  evidence(jobId) {
    if (!isValidVxsWorkstationJobId(jobId)) {
      return this.invalidJobId("vxs evidence <job-id>");
    }
    return this.getJson(
      `/v1/jobs/${encodeURIComponent(jobId)}/evidence`,
      "EVIDENCE",
      `GET /v1/jobs/${jobId}/evidence`
    );
  }
  durableJobRegistry() {
    return describeVxsWorkstationDurableRead(
      "READ_JOB_REGISTRY",
      VXS_WORKSTATION_DURABLE_ROOTS.jobRegistry
    );
  }
  durableEvidenceStore() {
    return describeVxsWorkstationDurableRead(
      "READ_EVIDENCE_STORE",
      VXS_WORKSTATION_DURABLE_ROOTS.evidence
    );
  }
  durableLaneObservation() {
    return describeVxsWorkstationDurableRead(
      "READ_LANE_OBSERVATION",
      VXS_WORKSTATION_DURABLE_ROOTS.lanes
    );
  }
  getJson(urlPath, capability, summary) {
    const descriptor = describeVxsWorkstationHttpRead(urlPath);
    const command = [
      "$ErrorActionPreference='Stop'",
      `$r=Invoke-RestMethod -Method Get -Uri ${psSingleQuote3(descriptor.target)} -TimeoutSec 4`,
      "$r | ConvertTo-Json -Depth 16"
    ].join("; ");
    return {
      kind: "execute",
      executionCommand: command,
      executionCwd: this.portalRoot,
      capability,
      routeSummary: summary
    };
  }
  invalidJobId(usage) {
    return {
      kind: "immediate",
      output: [
        "ERROR: A valid job-id is required.",
        `Usage: ${usage}`,
        ""
      ].join("\n"),
      exitCode: 2,
      stream: "stderr"
    };
  }
};
var vxsWorkstationReadAdapter = new VxsWorkstationReadAdapter();

// src/main/shell/vxs/vxs-vertex-capabilities.ts
var PORTAL_ROOT = "G:\\Vertex_Project\\Development\\vertex_session_portal";
function line2(value = "") {
  return `${value}
`;
}
function immediate(output, exitCode = 0, stream = "system") {
  return {
    kind: "immediate",
    output: output.map(line2).join(""),
    exitCode,
    stream
  };
}
function error(message, hints = []) {
  return immediate(
    [`ERROR: ${message}`, ...hints, ""],
    2,
    "stderr"
  );
}
function psSingleQuote4(value) {
  return `'${value.replaceAll("'", "''")}'`;
}
function rayCommand(args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const pattern = args.join(" ").trim();
  const script = path5.join(PORTAL_ROOT, "scripts", "vxs", "vxs_ray.py");
  const pieces = [
    "python",
    psSingleQuote4(script),
    "--root",
    psSingleQuote4(workspace.root)
  ];
  if (pattern) {
    pieces.push("--pattern", psSingleQuote4(pattern));
  }
  return {
    kind: "execute",
    executionCommand: pieces.join(" "),
    executionCwd: workspace.root,
    capability: "RAY",
    routeSummary: pattern ? `Read-only workspace Ray \xB7 pattern=${pattern}` : "Read-only workspace Ray \xB7 structural summary"
  };
}
function vraCommand(args, _context) {
  const body = args.join(" ").trim();
  if (!body || /^help$/i.test(body)) {
    return immediate([
      "VXS VRA",
      "",
      "  vxs vra list",
      "  vxs vra dispatch <artifact-id|card-id|filename>",
      "",
      "These commands alias the existing Portal Native VRA path.",
      "Dispatch remains an explicit Human command through the existing Human Gate.",
      ""
    ]);
  }
  return error(
    "Native VRA alias bridge did not intercept this command.",
    [
      "Expected renderer route: vxs vra ... -> existing vra ...",
      "No fallback dispatch is attempted."
    ]
  );
}
function workstationCommand(args, _context) {
  const sub = (args[0] ?? "status").toLowerCase();
  if (sub === "help" || sub === "--help") {
    return immediate([
      "VXS WORKSTATION \xB7 READ-ONLY CONTROL PLANE",
      "",
      "  vxs workstation status",
      "  vxs workstation safety",
      "  vxs workstation job <job-id>",
      "",
      `Endpoint: ${vxsWorkstationReadAdapter.baseUrl}`,
      "Mutation endpoints are not exposed by this VXS pack.",
      ""
    ]);
  }
  if (sub === "status" || sub === "health") {
    return vxsWorkstationReadAdapter.health();
  }
  if (sub === "safety") {
    return vxsWorkstationReadAdapter.safety();
  }
  if (sub === "job") {
    return vxsWorkstationReadAdapter.job(args[1] ?? "");
  }
  return error(
    `Unknown workstation command '${sub}'.`,
    ["Run: vxs workstation help"]
  );
}
function evidenceCommand(args, _context) {
  return vxsWorkstationReadAdapter.evidence(args[0] ?? "");
}
function createVxsVertexCommands() {
  return [
    {
      name: "ray",
      aliases: [],
      usage: "vxs ray [pattern]",
      summary: "Read-only workspace observation",
      execute: rayCommand
    },
    {
      name: "vra",
      aliases: [],
      usage: "vxs vra <list|dispatch ...>",
      summary: "Alias to existing Native VRA commands",
      execute: vraCommand
    },
    {
      name: "workstation",
      aliases: ["ws"],
      usage: "vxs workstation <status|safety|job>",
      summary: "Read Workstation control-plane state",
      execute: workstationCommand
    },
    {
      name: "evidence",
      aliases: [],
      usage: "vxs evidence <job-id>",
      summary: "Read Workstation Evidence for a job",
      execute: evidenceCommand
    }
  ];
}

// src/main/shell/vxs/vxs-inspection-capabilities.ts
var import_node_child_process3 = require("node:child_process");
var fs4 = __toESM(require("node:fs"), 1);
var path6 = __toESM(require("node:path"), 1);
function line3(value = "") {
  return `${value}
`;
}
function immediateError2(message, hints = []) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      ...hints,
      ""
    ].map(line3).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function envCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const pathEntries = (process.env.PATH ?? "").split(path6.delimiter).filter(Boolean);
  const rows = [
    "VXS ENV \xB7 SAFE SUMMARY",
    `Platform: ${process.platform}`,
    `Architecture: ${process.arch}`,
    `Node: ${process.versions.node}`,
    `PID: ${process.pid}`,
    `CWD: ${workspace.cwd}`,
    `Workspace Root: ${workspace.root}`,
    `Workspace Type: ${workspace.kind}`,
    `Package Manager: ${workspace.packageManager ?? "not detected"}`,
    `Compatibility Backend: ${context.compatibilityBackend}`,
    `PATH Entries: ${pathEntries.length}`,
    "",
    "Sensitive environment variable values are intentionally not displayed.",
    ""
  ];
  return {
    kind: "immediate",
    output: rows.map(line3).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function whichCommand(args, _context) {
  const tool = (args[0] ?? "").trim();
  if (!tool) {
    return immediateError2(
      "Tool name is required.",
      ["Usage: vxs which <tool>"]
    );
  }
  if (!/^[A-Za-z0-9._+-]+$/.test(tool)) {
    return immediateError2(
      `Invalid tool name '${tool}'.`
    );
  }
  const resolver = process.platform === "win32" ? "where.exe" : "which";
  try {
    const result = (0, import_node_child_process3.spawnSync)(
      resolver,
      [tool],
      {
        windowsHide: true,
        shell: false,
        encoding: "utf-8",
        timeout: 3e3
      }
    );
    const stdout = (result.stdout ?? "").trim();
    const stderr = (result.stderr ?? "").trim();
    if (result.status !== 0 || !stdout) {
      return immediateError2(
        `Tool '${tool}' was not found.`,
        stderr ? [stderr] : []
      );
    }
    return {
      kind: "immediate",
      output: [
        "VXS WHICH",
        `Tool: ${tool}`,
        ...stdout.split(/\r?\n/).map((value) => `Path: ${value}`),
        ""
      ].map(line3).join(""),
      exitCode: 0,
      stream: "system"
    };
  } catch (error2) {
    return immediateError2(
      `Unable to resolve '${tool}'.`,
      [error2 instanceof Error ? error2.message : String(error2)]
    );
  }
}
var TREE_SKIP = /* @__PURE__ */ new Set([
  ".git",
  "node_modules",
  "target",
  "dist",
  "out",
  "coverage",
  ".vite",
  "__pycache__",
  ".venv",
  "venv",
  "runtime"
]);
function treeCommand(args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const rawDepth = (args[0] ?? "2").trim();
  const depth = Number.parseInt(rawDepth, 10);
  if (!Number.isFinite(depth) || depth < 1 || depth > 4) {
    return immediateError2(
      `Invalid tree depth '${rawDepth}'.`,
      ["Usage: vxs tree [1-4]"]
    );
  }
  const rows = [
    "VXS TREE",
    `Root: ${workspace.root}`,
    `Depth: ${depth}`,
    ""
  ];
  let emitted = 0;
  const maxEntries = 300;
  function walk(dir, level) {
    if (level > depth || emitted >= maxEntries) return;
    let entries;
    try {
      entries = fs4.readdirSync(dir, { withFileTypes: true }).filter((entry) => !TREE_SKIP.has(entry.name)).sort((a, b) => {
        if (a.isDirectory() !== b.isDirectory()) {
          return a.isDirectory() ? -1 : 1;
        }
        return a.name.localeCompare(b.name);
      });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (emitted >= maxEntries) return;
      const prefix = "  ".repeat(level - 1);
      rows.push(
        `${prefix}${entry.isDirectory() ? "[D]" : "[F]"} ${entry.name}`
      );
      emitted += 1;
      if (entry.isDirectory() && level < depth) {
        walk(path6.join(dir, entry.name), level + 1);
      }
    }
  }
  walk(workspace.root, 1);
  if (emitted >= maxEntries) {
    rows.push("");
    rows.push(`TRUNCATED at ${maxEntries} entries.`);
  }
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line3).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function keysOfRecord(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return [];
  }
  return Object.keys(value).sort();
}
function depsCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const packageJson = path6.join(workspace.root, "package.json");
  if (!fs4.existsSync(packageJson)) {
    return immediateError2(
      "package.json was not found in the detected workspace.",
      [`Workspace Root: ${workspace.root}`]
    );
  }
  let data;
  try {
    data = JSON.parse(fs4.readFileSync(packageJson, "utf-8"));
  } catch (error2) {
    return immediateError2(
      "package.json could not be parsed.",
      [error2 instanceof Error ? error2.message : String(error2)]
    );
  }
  const groups = [
    ["dependencies", keysOfRecord(data.dependencies)],
    ["devDependencies", keysOfRecord(data.devDependencies)],
    ["optionalDependencies", keysOfRecord(data.optionalDependencies)],
    ["peerDependencies", keysOfRecord(data.peerDependencies)]
  ];
  const rows = [
    "VXS DEPS",
    `Package: ${typeof data.name === "string" ? data.name : "(unnamed)"}`,
    `Version: ${typeof data.version === "string" ? data.version : "(unknown)"}`,
    `Workspace Root: ${workspace.root}`,
    ""
  ];
  for (const [name, values] of groups) {
    rows.push(`${name}: ${values.length}`);
    for (const value of values.slice(0, 80)) {
      rows.push(`  ${value}`);
    }
    if (values.length > 80) {
      rows.push(`  ... ${values.length - 80} more`);
    }
    rows.push("");
  }
  return {
    kind: "immediate",
    output: rows.map(line3).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsInspectionCommands() {
  return [
    {
      name: "env",
      aliases: [],
      usage: "vxs env",
      summary: "Show a safe development environment summary",
      execute: envCommand
    },
    {
      name: "which",
      aliases: [],
      usage: "vxs which <tool>",
      summary: "Resolve a development tool path",
      execute: whichCommand
    },
    {
      name: "tree",
      aliases: [],
      usage: "vxs tree [1-4]",
      summary: "Show a bounded workspace tree",
      execute: treeCommand
    },
    {
      name: "deps",
      aliases: [],
      usage: "vxs deps",
      summary: "Inspect local package dependencies",
      execute: depsCommand
    }
  ];
}

// src/main/shell/vxs/vxs-observability-capabilities.ts
var fs5 = __toESM(require("node:fs"), 1);
var path7 = __toESM(require("node:path"), 1);
function line4(value = "") {
  return `${value}
`;
}
function immediateError3(message, hints = []) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      ...hints,
      ""
    ].map(line4).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function safeReadText(filePath, maxBytes = 512 * 1024) {
  try {
    const stat = fs5.statSync(filePath);
    if (!stat.isFile()) return null;
    const fd = fs5.openSync(filePath, "r");
    try {
      const size = Math.min(stat.size, maxBytes);
      const start = Math.max(0, stat.size - size);
      const buffer = Buffer.alloc(size);
      fs5.readSync(fd, buffer, 0, size, start);
      return buffer.toString("utf-8");
    } finally {
      fs5.closeSync(fd);
    }
  } catch {
    return null;
  }
}
function lastLines(text, count) {
  return text.split(/\r?\n/).filter((value, index, values) => value.length > 0 || index < values.length - 1).slice(-count);
}
function portalLogRoots() {
  const appData = process.env.APPDATA;
  const localAppData = process.env.LOCALAPPDATA;
  const roots = [];
  if (appData) {
    roots.push(
      path7.join(appData, "vertex-session-portal"),
      path7.join(appData, "Vertex Session Portal")
    );
  }
  if (localAppData) {
    roots.push(
      path7.join(localAppData, "vertex-session-portal"),
      path7.join(localAppData, "VertexSessionPortal")
    );
  }
  return roots;
}
function collectRecentLogFiles(roots, limit = 30) {
  const rows = [];
  const allowed = /* @__PURE__ */ new Set([".log", ".txt", ".jsonl", ".ndjson"]);
  function walk(dir, depth) {
    if (depth > 3 || rows.length > 500) return;
    let entries;
    try {
      entries = fs5.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const full = path7.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (["node_modules", ".git", "target"].includes(entry.name)) continue;
        walk(full, depth + 1);
        continue;
      }
      if (!entry.isFile()) continue;
      if (!allowed.has(path7.extname(entry.name).toLowerCase())) continue;
      try {
        const stat = fs5.statSync(full);
        rows.push({ path: full, mtimeMs: stat.mtimeMs, size: stat.size });
      } catch {
      }
    }
  }
  for (const root of roots) {
    if (fs5.existsSync(root)) walk(root, 0);
  }
  return rows.sort((a, b) => b.mtimeMs - a.mtimeMs).slice(0, limit);
}
function logsCommand(args, _context) {
  const scope = (args[0] ?? "portal").toLowerCase();
  const rawCount = args[1] ?? "80";
  const count = Number.parseInt(rawCount, 10);
  if (!Number.isFinite(count) || count < 10 || count > 300) {
    return immediateError3(
      `Invalid line count '${rawCount}'.`,
      ["Usage: vxs logs [portal|workstation] [10-300]"]
    );
  }
  let roots;
  if (scope === "portal") {
    roots = portalLogRoots();
  } else if (scope === "workstation") {
    roots = [
      "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime"
    ];
  } else {
    return immediateError3(
      `Unknown log scope '${scope}'.`,
      ["Usage: vxs logs [portal|workstation] [10-300]"]
    );
  }
  const files = collectRecentLogFiles(roots, 12);
  if (!files.length) {
    return immediateError3(
      `No readable ${scope} log files were found.`
    );
  }
  const rows = [
    "VXS LOGS",
    `Scope: ${scope}`,
    `Tail Lines: ${count}`,
    ""
  ];
  for (const item of files.slice(0, 5)) {
    rows.push(`FILE: ${item.path}`);
    rows.push(`SIZE: ${item.size}`);
    const text = safeReadText(item.path);
    if (text === null) {
      rows.push("(unreadable)");
    } else {
      rows.push(...lastLines(text, count));
    }
    rows.push("");
  }
  return {
    kind: "immediate",
    output: rows.map(line4).join(""),
    exitCode: 0,
    stream: "system"
  };
}
var JOB_ID_PATTERN2 = /^[A-Za-z0-9._:-]+$/;
function traceCommand(args, _context) {
  const jobId = (args[0] ?? "").trim();
  if (!jobId) {
    return immediateError3(
      "Job ID is required.",
      ["Usage: vxs trace <job-id>"]
    );
  }
  if (!JOB_ID_PATTERN2.test(jobId)) {
    return immediateError3("Job ID contains unsupported characters.");
  }
  const portalRoots = portalLogRoots();
  const workstationRoot = "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime";
  const searchRoots = [
    ...portalRoots,
    workstationRoot
  ];
  const files = collectRecentLogFiles(searchRoots, 80);
  const hits = [];
  for (const item of files) {
    const text = safeReadText(item.path, 2 * 1024 * 1024);
    if (!text || !text.includes(jobId)) continue;
    const matched = text.split(/\r?\n/).filter((value) => value.includes(jobId)).slice(-20);
    hits.push({ path: item.path, lines: matched });
    if (hits.length >= 12) break;
  }
  const registryRoot = "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry";
  if (fs5.existsSync(registryRoot)) {
    let registryFiles = [];
    try {
      registryFiles = fs5.readdirSync(registryRoot).filter((name) => name.endsWith(".json")).map((name) => path7.join(registryRoot, name)).slice(-200);
    } catch {
      registryFiles = [];
    }
    for (const filePath of registryFiles) {
      const text = safeReadText(filePath, 2 * 1024 * 1024);
      if (!text || !text.includes(jobId)) continue;
      const matched = text.split(/\r?\n/).filter((value) => value.includes(jobId)).slice(-20);
      hits.push({ path: filePath, lines: matched });
      if (hits.length >= 16) break;
    }
  }
  const rows = [
    "VXS TRACE",
    `Job ID: ${jobId}`,
    `Matches: ${hits.length}`,
    ""
  ];
  if (!hits.length) {
    rows.push("No local trace matches were found.");
    rows.push("");
  } else {
    for (const hit of hits) {
      rows.push(`FILE: ${hit.path}`);
      rows.push(...hit.lines);
      rows.push("");
    }
  }
  return {
    kind: "immediate",
    output: rows.map(line4).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsObservabilityCommands() {
  return [
    {
      name: "logs",
      aliases: [],
      usage: "vxs logs [portal|workstation] [10-300]",
      summary: "Tail bounded local Vertex logs",
      execute: logsCommand
    },
    {
      name: "trace",
      aliases: ["job-trace"],
      usage: "vxs trace <job-id>",
      summary: "Find local Portal/Workstation traces for a Job",
      execute: traceCommand
    }
  ];
}

// src/main/shell/vxs/vxs-source-inspection-capabilities.ts
var import_node_crypto3 = require("node:crypto");
var fs6 = __toESM(require("node:fs"), 1);
var path8 = __toESM(require("node:path"), 1);
function line5(value = "") {
  return `${value}
`;
}
function immediateError4(message, hints = []) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      ...hints,
      ""
    ].map(line5).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function resolveInsideWorkspace(workspaceRoot, requested) {
  const value = requested.trim();
  if (!value) return workspaceRoot;
  const resolved = path8.resolve(workspaceRoot, value);
  const relative4 = path8.relative(workspaceRoot, resolved);
  if (relative4 === "" || !relative4.startsWith("..") && !path8.isAbsolute(relative4)) {
    return resolved;
  }
  return null;
}
var SEARCH_SKIP = /* @__PURE__ */ new Set([
  ".git",
  "node_modules",
  "target",
  "dist",
  "out",
  "coverage",
  ".vite",
  "__pycache__",
  ".venv",
  "venv",
  "runtime"
]);
function findCommand(args, context) {
  const pattern = (args[0] ?? "").trim();
  const relativeRoot = (args[1] ?? ".").trim();
  if (!pattern) {
    return immediateError4(
      "Search pattern is required.",
      ["Usage: vxs find <text> [path]"]
    );
  }
  if (pattern.length > 200) {
    return immediateError4("Search pattern is too long.");
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const searchRoot = resolveInsideWorkspace(workspace.root, relativeRoot);
  if (!searchRoot) {
    return immediateError4("Search path escapes the detected workspace.");
  }
  if (!fs6.existsSync(searchRoot)) {
    return immediateError4(`Search path does not exist: ${relativeRoot}`);
  }
  const hits = [];
  let scannedFiles = 0;
  const maxFiles = 4e3;
  const maxHits = 120;
  const maxFileBytes = 2 * 1024 * 1024;
  const needle = pattern.toLowerCase();
  function scanFile(filePath) {
    if (scannedFiles >= maxFiles || hits.length >= maxHits) return;
    let stat;
    try {
      stat = fs6.statSync(filePath);
    } catch {
      return;
    }
    if (!stat.isFile() || stat.size > maxFileBytes) return;
    scannedFiles += 1;
    let text;
    try {
      text = fs6.readFileSync(filePath, "utf-8");
    } catch {
      return;
    }
    const rows2 = text.split(/\r?\n/);
    for (let index = 0; index < rows2.length; index += 1) {
      if (!rows2[index].toLowerCase().includes(needle)) continue;
      const rel = path8.relative(workspace.root, filePath);
      hits.push(`${rel}:${index + 1}: ${rows2[index].slice(0, 500)}`);
      if (hits.length >= maxHits) return;
    }
  }
  function walk(current) {
    if (scannedFiles >= maxFiles || hits.length >= maxHits) return;
    let stat;
    try {
      stat = fs6.statSync(current);
    } catch {
      return;
    }
    if (stat.isFile()) {
      scanFile(current);
      return;
    }
    if (!stat.isDirectory()) return;
    let entries;
    try {
      entries = fs6.readdirSync(current, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      if (hits.length >= maxHits || scannedFiles >= maxFiles) return;
      if (entry.isDirectory() && SEARCH_SKIP.has(entry.name)) continue;
      walk(path8.join(current, entry.name));
    }
  }
  walk(searchRoot);
  const rows = [
    "VXS FIND",
    `Pattern: ${pattern}`,
    `Root: ${searchRoot}`,
    `Files Scanned: ${scannedFiles}`,
    `Matches: ${hits.length}`,
    "",
    ...hits
  ];
  if (hits.length >= maxHits) {
    rows.push("");
    rows.push(`TRUNCATED at ${maxHits} matches.`);
  }
  if (scannedFiles >= maxFiles) {
    rows.push("");
    rows.push(`FILE SCAN LIMIT reached at ${maxFiles}.`);
  }
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line5).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function inspectCommand(args, context) {
  const requested = (args[0] ?? "").trim();
  const rawStart = args[1] ?? "1";
  const rawCount = args[2] ?? "120";
  if (!requested) {
    return immediateError4(
      "File path is required.",
      ["Usage: vxs inspect <path> [start-line] [count]"]
    );
  }
  const start = Number.parseInt(rawStart, 10);
  const count = Number.parseInt(rawCount, 10);
  if (!Number.isFinite(start) || start < 1) {
    return immediateError4(`Invalid start line '${rawStart}'.`);
  }
  if (!Number.isFinite(count) || count < 1 || count > 400) {
    return immediateError4(
      `Invalid line count '${rawCount}'.`,
      ["Allowed range: 1-400"]
    );
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const filePath = resolveInsideWorkspace(workspace.root, requested);
  if (!filePath) {
    return immediateError4("Requested file escapes the detected workspace.");
  }
  let stat;
  try {
    stat = fs6.statSync(filePath);
  } catch {
    return immediateError4(`File not found: ${requested}`);
  }
  if (!stat.isFile()) {
    return immediateError4(`Path is not a file: ${requested}`);
  }
  if (stat.size > 4 * 1024 * 1024) {
    return immediateError4(
      "File is larger than the 4 MiB inspection limit.",
      ["Use vxs find for bounded search instead."]
    );
  }
  let text;
  try {
    text = fs6.readFileSync(filePath, "utf-8");
  } catch {
    return immediateError4(`File could not be read as UTF-8 text: ${requested}`);
  }
  const fileLines = text.split(/\r?\n/);
  const from = Math.min(start - 1, fileLines.length);
  const to = Math.min(from + count, fileLines.length);
  const rows = [
    "VXS INSPECT",
    `File: ${path8.relative(workspace.root, filePath)}`,
    `Lines: ${from + 1}-${to} / ${fileLines.length}`,
    ""
  ];
  for (let index = from; index < to; index += 1) {
    rows.push(`${String(index + 1).padStart(6, "0")}| ${fileLines[index]}`);
  }
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line5).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function hashCommand(args, context) {
  const requested = (args[0] ?? "").trim();
  if (!requested) {
    return immediateError4(
      "File path is required.",
      ["Usage: vxs hash <path>"]
    );
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const filePath = resolveInsideWorkspace(workspace.root, requested);
  if (!filePath) {
    return immediateError4("Requested file escapes the detected workspace.");
  }
  let bytes;
  try {
    const stat = fs6.statSync(filePath);
    if (!stat.isFile()) {
      return immediateError4(`Path is not a file: ${requested}`);
    }
    if (stat.size > 128 * 1024 * 1024) {
      return immediateError4("File exceeds the 128 MiB hash limit.");
    }
    bytes = fs6.readFileSync(filePath);
  } catch {
    return immediateError4(`File could not be read: ${requested}`);
  }
  const digest = (0, import_node_crypto3.createHash)("sha256").update(bytes).digest("hex");
  return {
    kind: "immediate",
    output: [
      "VXS HASH",
      `File: ${path8.relative(workspace.root, filePath)}`,
      `SHA256: ${digest}`,
      ""
    ].map(line5).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function statCommand(args, context) {
  const requested = (args[0] ?? ".").trim();
  const workspace = detectVxsWorkspace(context.cwd);
  const target = resolveInsideWorkspace(workspace.root, requested);
  if (!target) {
    return immediateError4("Requested path escapes the detected workspace.");
  }
  let stat;
  try {
    stat = fs6.statSync(target);
  } catch {
    return immediateError4(`Path not found: ${requested}`);
  }
  return {
    kind: "immediate",
    output: [
      "VXS STAT",
      `Path: ${path8.relative(workspace.root, target) || "."}`,
      `Type: ${stat.isDirectory() ? "directory" : stat.isFile() ? "file" : "other"}`,
      `Size: ${stat.size}`,
      `Modified: ${stat.mtime.toISOString()}`,
      `Created: ${stat.birthtime.toISOString()}`,
      ""
    ].map(line5).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsSourceInspectionCommands() {
  return [
    {
      name: "find",
      aliases: ["grep"],
      usage: "vxs find <text> [path]",
      summary: "Search workspace text with bounded reads",
      execute: findCommand
    },
    {
      name: "inspect",
      aliases: ["cat"],
      usage: "vxs inspect <path> [start-line] [count]",
      summary: "Read bounded line ranges from workspace files",
      execute: inspectCommand
    },
    {
      name: "hash",
      aliases: ["sha256"],
      usage: "vxs hash <path>",
      summary: "Compute SHA256 for a workspace file",
      execute: hashCommand
    },
    {
      name: "stat",
      aliases: [],
      usage: "vxs stat <path>",
      summary: "Show workspace file or directory metadata",
      execute: statCommand
    }
  ];
}

// src/main/shell/vxs/vxs-change-intelligence-capabilities.ts
var import_node_child_process4 = require("node:child_process");
var fs7 = __toESM(require("node:fs"), 1);
var path9 = __toESM(require("node:path"), 1);
function line6(value = "") {
  return `${value}
`;
}
function immediateError5(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line6).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function runGit(cwd, args) {
  try {
    const result = (0, import_node_child_process4.spawnSync)(
      "git",
      args,
      {
        cwd,
        windowsHide: true,
        shell: false,
        encoding: "utf-8",
        timeout: 8e3
      }
    );
    return {
      ok: result.status === 0,
      stdout: (result.stdout ?? "").trim(),
      stderr: (result.stderr ?? "").trim()
    };
  } catch (error2) {
    return {
      ok: false,
      stdout: "",
      stderr: error2 instanceof Error ? error2.message : String(error2)
    };
  }
}
function changedCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  if (!workspace.git) {
    return immediateError5(
      "Git repository was not detected.",
      [`Workspace Root: ${workspace.root}`]
    );
  }
  const result = runGit(
    workspace.root,
    ["status", "--short", "--untracked-files=normal"]
  );
  if (!result.ok) {
    return immediateError5("git status failed.", result.stderr ? [result.stderr] : []);
  }
  const rows = [
    "VXS CHANGED",
    `Workspace Root: ${workspace.root}`,
    ""
  ];
  if (!result.stdout) {
    rows.push("(clean working tree)");
  } else {
    rows.push(...result.stdout.split(/\r?\n/).slice(0, 300));
  }
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line6).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function diffstatCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  if (!workspace.git) {
    return immediateError5(
      "Git repository was not detected.",
      [`Workspace Root: ${workspace.root}`]
    );
  }
  const worktree = runGit(workspace.root, ["diff", "--stat"]);
  const staged = runGit(workspace.root, ["diff", "--cached", "--stat"]);
  if (!worktree.ok || !staged.ok) {
    return immediateError5(
      "git diff --stat failed.",
      [
        ...worktree.stderr ? [worktree.stderr] : [],
        ...staged.stderr ? [staged.stderr] : []
      ]
    );
  }
  const rows = [
    "VXS DIFFSTAT",
    `Workspace Root: ${workspace.root}`,
    "",
    "WORKTREE:",
    ...worktree.stdout ? worktree.stdout.split(/\r?\n/) : ["(none)"],
    "",
    "STAGED:",
    ...staged.stdout ? staged.stdout.split(/\r?\n/) : ["(none)"],
    ""
  ];
  return {
    kind: "immediate",
    output: rows.map(line6).join(""),
    exitCode: 0,
    stream: "system"
  };
}
var SEARCH_SKIP2 = /* @__PURE__ */ new Set([
  ".git",
  "node_modules",
  "target",
  "dist",
  "out",
  "coverage",
  ".vite",
  "__pycache__",
  ".venv",
  "venv",
  "runtime"
]);
var SOURCE_EXTENSIONS = /* @__PURE__ */ new Set([
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
  ".rs",
  ".py",
  ".go",
  ".java",
  ".kt",
  ".kts",
  ".cs",
  ".cpp",
  ".cc",
  ".c",
  ".h",
  ".hpp",
  ".vue",
  ".svelte",
  ".json",
  ".toml",
  ".yaml",
  ".yml",
  ".md",
  ".ps1",
  ".sh"
]);
function walkSourceFiles(root, callback) {
  let scanned = 0;
  const maxFiles = 5e3;
  function walk(current) {
    if (scanned >= maxFiles) return false;
    let entries;
    try {
      entries = fs7.readdirSync(current, { withFileTypes: true });
    } catch {
      return true;
    }
    for (const entry of entries) {
      if (scanned >= maxFiles) return false;
      const full = path9.join(current, entry.name);
      if (entry.isDirectory()) {
        if (SEARCH_SKIP2.has(entry.name)) continue;
        if (!walk(full)) return false;
        continue;
      }
      if (!entry.isFile()) continue;
      if (!SOURCE_EXTENSIONS.has(path9.extname(entry.name).toLowerCase())) continue;
      scanned += 1;
      const keepGoing = callback(full);
      if (keepGoing === false) return false;
    }
    return true;
  }
  walk(root);
}
function refsCommand(args, context) {
  const symbol = (args[0] ?? "").trim();
  if (!symbol) {
    return immediateError5(
      "Symbol is required.",
      ["Usage: vxs refs <symbol>"]
    );
  }
  if (!/^[A-Za-z_$][A-Za-z0-9_$.:/-]{0,127}$/.test(symbol)) {
    return immediateError5("Symbol contains unsupported characters.");
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const needle = symbol.toLowerCase();
  const hits = [];
  const maxHits = 120;
  const maxFileBytes = 2 * 1024 * 1024;
  walkSourceFiles(workspace.root, (filePath) => {
    if (hits.length >= maxHits) return false;
    let stat;
    try {
      stat = fs7.statSync(filePath);
    } catch {
      return;
    }
    if (stat.size > maxFileBytes) return;
    let text;
    try {
      text = fs7.readFileSync(filePath, "utf-8");
    } catch {
      return;
    }
    const rows2 = text.split(/\r?\n/);
    for (let index = 0; index < rows2.length; index += 1) {
      if (!rows2[index].toLowerCase().includes(needle)) continue;
      hits.push(
        `${path9.relative(workspace.root, filePath)}:${index + 1}: ${rows2[index].slice(0, 500)}`
      );
      if (hits.length >= maxHits) return false;
    }
  });
  const rows = [
    "VXS REFS",
    `Symbol: ${symbol}`,
    `Matches: ${hits.length}`,
    "",
    ...hits
  ];
  if (hits.length >= maxHits) {
    rows.push("");
    rows.push(`TRUNCATED at ${maxHits} matches.`);
  }
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line6).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function resolveInsideWorkspace2(workspaceRoot, requested) {
  const value = requested.trim();
  const resolved = path9.resolve(workspaceRoot, value || ".");
  const relative4 = path9.relative(workspaceRoot, resolved);
  if (relative4 === "" || !relative4.startsWith("..") && !path9.isAbsolute(relative4)) {
    return resolved;
  }
  return null;
}
function todoCommand(args, context) {
  const requested = (args[0] ?? ".").trim();
  const workspace = detectVxsWorkspace(context.cwd);
  const root = resolveInsideWorkspace2(workspace.root, requested);
  if (!root) {
    return immediateError5("Requested path escapes the detected workspace.");
  }
  if (!fs7.existsSync(root)) {
    return immediateError5(`Path not found: ${requested}`);
  }
  const tokens = ["TODO", "FIXME", "HACK", "XXX"];
  const hits = [];
  const maxHits = 120;
  const inspectFile = (filePath) => {
    if (hits.length >= maxHits) return false;
    let stat;
    try {
      stat = fs7.statSync(filePath);
    } catch {
      return;
    }
    if (!stat.isFile() || stat.size > 2 * 1024 * 1024) return;
    let text;
    try {
      text = fs7.readFileSync(filePath, "utf-8");
    } catch {
      return;
    }
    const rows2 = text.split(/\r?\n/);
    for (let index = 0; index < rows2.length; index += 1) {
      if (!tokens.some((token) => rows2[index].includes(token))) continue;
      hits.push(
        `${path9.relative(workspace.root, filePath)}:${index + 1}: ${rows2[index].slice(0, 500)}`
      );
      if (hits.length >= maxHits) return false;
    }
  };
  try {
    const stat = fs7.statSync(root);
    if (stat.isFile()) {
      inspectFile(root);
    } else if (stat.isDirectory()) {
      walkSourceFiles(root, inspectFile);
    }
  } catch {
    return immediateError5(`Unable to inspect: ${requested}`);
  }
  const rows = [
    "VXS TODO",
    `Root: ${path9.relative(workspace.root, root) || "."}`,
    `Matches: ${hits.length}`,
    "",
    ...hits
  ];
  if (hits.length >= maxHits) {
    rows.push("");
    rows.push(`TRUNCATED at ${maxHits} matches.`);
  }
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line6).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsChangeIntelligenceCommands() {
  return [
    {
      name: "changed",
      aliases: [],
      usage: "vxs changed",
      summary: "Show changed and untracked files",
      execute: changedCommand
    },
    {
      name: "diffstat",
      aliases: [],
      usage: "vxs diffstat",
      summary: "Show staged and worktree diff statistics",
      execute: diffstatCommand
    },
    {
      name: "refs",
      aliases: [],
      usage: "vxs refs <symbol>",
      summary: "Find bounded source references to a symbol",
      execute: refsCommand
    },
    {
      name: "todo",
      aliases: [],
      usage: "vxs todo [path]",
      summary: "Find TODO/FIXME/HACK/XXX markers",
      execute: todoCommand
    }
  ];
}

// src/main/shell/vxs/vxs-dependency-intelligence-capabilities.ts
var fs8 = __toESM(require("node:fs"), 1);
var path10 = __toESM(require("node:path"), 1);
function line7(value = "") {
  return `${value}
`;
}
function immediateError6(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line7).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function resolveInsideWorkspace3(workspaceRoot, requested) {
  const resolved = path10.resolve(workspaceRoot, requested);
  const relative4 = path10.relative(workspaceRoot, resolved);
  if (relative4 === "" || !relative4.startsWith("..") && !path10.isAbsolute(relative4)) {
    return resolved;
  }
  return null;
}
var SOURCE_EXTENSIONS2 = /* @__PURE__ */ new Set([
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
  ".vue",
  ".svelte",
  ".rs",
  ".py",
  ".go",
  ".java",
  ".kt",
  ".kts",
  ".cs"
]);
var SEARCH_SKIP3 = /* @__PURE__ */ new Set([
  ".git",
  "node_modules",
  "target",
  "dist",
  "out",
  "coverage",
  ".vite",
  "__pycache__",
  ".venv",
  "venv",
  "runtime"
]);
function readTextFile(filePath, maxBytes = 2 * 1024 * 1024) {
  try {
    const stat = fs8.statSync(filePath);
    if (!stat.isFile() || stat.size > maxBytes) return null;
    return fs8.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}
function extractImports(text) {
  const imports = /* @__PURE__ */ new Set();
  const patterns = [
    /\bimport\s+(?:type\s+)?(?:[^'"]+?\s+from\s+)?['"]([^'"]+)['"]/g,
    /\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)/g,
    /\bexport\s+(?:type\s+)?(?:[^'"]+?\s+from\s+)?['"]([^'"]+)['"]/g
  ];
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(text)) !== null) {
      if (match[1]) imports.add(match[1]);
      if (imports.size >= 200) break;
    }
  }
  return [...imports].sort();
}
function importsCommand(args, context) {
  const requested = (args[0] ?? "").trim();
  if (!requested) {
    return immediateError6(
      "File path is required.",
      ["Usage: vxs imports <path>"]
    );
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const filePath = resolveInsideWorkspace3(workspace.root, requested);
  if (!filePath) {
    return immediateError6("Requested file escapes the detected workspace.");
  }
  const text = readTextFile(filePath);
  if (text === null) {
    return immediateError6(
      "File is missing, unreadable, or larger than 2 MiB.",
      [`Path: ${requested}`]
    );
  }
  const imports = extractImports(text);
  return {
    kind: "immediate",
    output: [
      "VXS IMPORTS",
      `File: ${path10.relative(workspace.root, filePath)}`,
      `Imports: ${imports.length}`,
      "",
      ...imports.length ? imports : ["(none detected)"],
      ""
    ].map(line7).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function moduleCandidates(workspaceRoot, filePath) {
  const relative4 = path10.relative(workspaceRoot, filePath).replace(/\\/g, "/");
  const noExt = relative4.replace(/\.[^.\/]+$/, "");
  const base = path10.basename(noExt);
  const withDot = noExt.startsWith(".") ? noExt : `./${noExt}`;
  const values = /* @__PURE__ */ new Set([
    relative4,
    noExt,
    withDot,
    base,
    `./${base}`
  ]);
  if (base === "index") {
    const parent = path10.dirname(noExt).replace(/\\/g, "/");
    const parentBase = path10.basename(parent);
    values.add(parent);
    values.add(`./${parent}`);
    values.add(parentBase);
    values.add(`./${parentBase}`);
  }
  return [...values].filter(Boolean);
}
function walkSourceFiles2(root, callback) {
  let scanned = 0;
  const maxFiles = 5e3;
  function walk(current) {
    if (scanned >= maxFiles) return false;
    let entries;
    try {
      entries = fs8.readdirSync(current, { withFileTypes: true });
    } catch {
      return true;
    }
    for (const entry of entries) {
      if (scanned >= maxFiles) return false;
      const full = path10.join(current, entry.name);
      if (entry.isDirectory()) {
        if (SEARCH_SKIP3.has(entry.name)) continue;
        if (!walk(full)) return false;
        continue;
      }
      if (!entry.isFile()) continue;
      if (!SOURCE_EXTENSIONS2.has(path10.extname(entry.name).toLowerCase())) continue;
      scanned += 1;
      if (callback(full) === false) return false;
    }
    return true;
  }
  walk(root);
}
function findDependents(workspaceRoot, targetPath) {
  const targetNormalized = path10.resolve(targetPath);
  const candidates = moduleCandidates(workspaceRoot, targetPath).map((value) => value.toLowerCase());
  const hits = [];
  const maxHits = 120;
  walkSourceFiles2(workspaceRoot, (filePath) => {
    if (hits.length >= maxHits) return false;
    if (path10.resolve(filePath) === targetNormalized) return;
    const text = readTextFile(filePath);
    if (text === null) return;
    const imports = extractImports(text);
    const lowerImports = imports.map((value) => value.toLowerCase());
    const matched = lowerImports.some(
      (specifier) => candidates.some(
        (candidate) => specifier === candidate || specifier.endsWith("/" + candidate.replace(/^\.\//, "")) || candidate.endsWith("/" + specifier.replace(/^\.\//, ""))
      )
    );
    if (matched) {
      hits.push(path10.relative(workspaceRoot, filePath));
    }
  });
  return hits.sort();
}
function dependentsCommand(args, context) {
  const requested = (args[0] ?? "").trim();
  if (!requested) {
    return immediateError6(
      "File path is required.",
      ["Usage: vxs dependents <path>"]
    );
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const filePath = resolveInsideWorkspace3(workspace.root, requested);
  if (!filePath) {
    return immediateError6("Requested file escapes the detected workspace.");
  }
  if (!fs8.existsSync(filePath)) {
    return immediateError6(`File not found: ${requested}`);
  }
  const hits = findDependents(workspace.root, filePath);
  const rows = [
    "VXS DEPENDENTS",
    `File: ${path10.relative(workspace.root, filePath)}`,
    `Direct Dependents: ${hits.length}`,
    "",
    ...hits.length ? hits : ["(none detected)"],
    ""
  ];
  if (hits.length >= 120) {
    rows.splice(rows.length - 1, 0, "TRUNCATED at 120 matches.");
  }
  return {
    kind: "immediate",
    output: rows.map(line7).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function impactCommand(args, context) {
  const requested = (args[0] ?? "").trim();
  if (!requested) {
    return immediateError6(
      "File path is required.",
      ["Usage: vxs impact <path>"]
    );
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const filePath = resolveInsideWorkspace3(workspace.root, requested);
  if (!filePath) {
    return immediateError6("Requested file escapes the detected workspace.");
  }
  const text = readTextFile(filePath);
  if (text === null) {
    return immediateError6(
      "File is missing, unreadable, or larger than 2 MiB.",
      [`Path: ${requested}`]
    );
  }
  const imports = extractImports(text);
  const dependents = findDependents(workspace.root, filePath);
  let size = 0;
  let modified = "unknown";
  try {
    const stat = fs8.statSync(filePath);
    size = stat.size;
    modified = stat.mtime.toISOString();
  } catch {
  }
  let impact = "LOW";
  if (dependents.length >= 20) impact = "HIGH";
  else if (dependents.length >= 5) impact = "MEDIUM";
  return {
    kind: "immediate",
    output: [
      "VXS IMPACT",
      `File: ${path10.relative(workspace.root, filePath)}`,
      `Size: ${size}`,
      `Modified: ${modified}`,
      `Direct Imports: ${imports.length}`,
      `Direct Dependents: ${dependents.length}`,
      `Impact Hint: ${impact}`,
      "",
      "Top Dependents:",
      ...dependents.slice(0, 20).length ? dependents.slice(0, 20).map((value) => `  ${value}`) : ["  (none detected)"],
      "",
      "Impact Hint is a bounded static heuristic, not an execution guarantee.",
      ""
    ].map(line7).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsDependencyIntelligenceCommands() {
  return [
    {
      name: "imports",
      aliases: [],
      usage: "vxs imports <path>",
      summary: "List detected imports for a workspace source file",
      execute: importsCommand
    },
    {
      name: "dependents",
      aliases: [],
      usage: "vxs dependents <path>",
      summary: "Find bounded direct source dependents",
      execute: dependentsCommand
    },
    {
      name: "impact",
      aliases: [],
      usage: "vxs impact <path>",
      summary: "Summarize bounded static change impact",
      execute: impactCommand
    }
  ];
}

// src/main/shell/vxs/vxs-runtime-diagnostics-capabilities.ts
var import_node_child_process5 = require("node:child_process");
var fs9 = __toESM(require("node:fs"), 1);
var path11 = __toESM(require("node:path"), 1);
function line8(value = "") {
  return `${value}
`;
}
function immediateError7(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line8).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function runReadOnly(program, args, timeout = 5e3) {
  try {
    const result = (0, import_node_child_process5.spawnSync)(
      program,
      args,
      {
        windowsHide: true,
        shell: false,
        encoding: "utf-8",
        timeout
      }
    );
    return {
      ok: result.status === 0,
      stdout: (result.stdout ?? "").trim(),
      stderr: (result.stderr ?? "").trim(),
      status: result.status
    };
  } catch (error2) {
    return {
      ok: false,
      stdout: "",
      stderr: error2 instanceof Error ? error2.message : String(error2),
      status: null
    };
  }
}
function commandVersion(label, program, args) {
  const result = runReadOnly(program, args, 3e3);
  const text = result.stdout || result.stderr;
  if (!result.ok || !text) {
    return `${label}: unavailable`;
  }
  return `${label}: ${text.split(/\r?\n/)[0].slice(0, 300)}`;
}
function versionsCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const rows = [
    "VXS VERSIONS",
    `Platform: ${process.platform} ${process.arch}`,
    `Node: ${process.versions.node}`,
    `Electron: ${process.versions.electron ?? "not available"}`,
    `Chrome: ${process.versions.chrome ?? "not available"}`,
    commandVersion("Git", "git", ["--version"]),
    commandVersion(
      "PowerShell",
      process.platform === "win32" ? "pwsh.exe" : "pwsh",
      ["--version"]
    ),
    commandVersion("Python", "python", ["--version"]),
    commandVersion("Cargo", "cargo", ["--version"]),
    commandVersion("Rustc", "rustc", ["--version"]),
    commandVersion(
      "NPM",
      process.platform === "win32" ? "npm.cmd" : "npm",
      ["--version"]
    ),
    `Workspace Root: ${workspace.root}`,
    ""
  ];
  return {
    kind: "immediate",
    output: rows.map(line8).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function runtimeCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const workRoot = "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime";
  const portalRuntimeCandidates = [
    path11.join(
      process.env.APPDATA ?? "",
      "vertex-session-portal",
      "vra-dispatch"
    ),
    path11.join(
      process.env.APPDATA ?? "",
      "Vertex Session Portal",
      "vra-dispatch"
    )
  ].filter(Boolean);
  const rows = [
    "VXS RUNTIME",
    `PID: ${process.pid}`,
    `Uptime Seconds: ${Math.floor(process.uptime())}`,
    `Memory RSS MiB: ${(process.memoryUsage().rss / 1024 / 1024).toFixed(1)}`,
    `Heap Used MiB: ${(process.memoryUsage().heapUsed / 1024 / 1024).toFixed(1)}`,
    `Workspace Root: ${workspace.root}`,
    `Workstation Runtime: ${fs9.existsSync(workRoot) ? "present" : "missing"}`
  ];
  for (const candidate of portalRuntimeCandidates) {
    rows.push(
      `Portal Dispatch State: ${candidate} = ${fs9.existsSync(candidate) ? "present" : "missing"}`
    );
  }
  if (process.platform === "win32") {
    const ws = runReadOnly(
      "netstat.exe",
      ["-ano", "-p", "tcp"],
      5e3
    );
    if (ws.ok) {
      const listeners = ws.stdout.split(/\r?\n/).filter((value) => /\sLISTENING\s/i.test(value));
      rows.push(`TCP Listening Rows: ${listeners.length}`);
      const workstationPort = listeners.filter(
        (value) => /:47832\s/.test(value)
      );
      rows.push(
        `Workstation 127.0.0.1:47832: ${workstationPort.length ? "LISTENING" : "not observed"}`
      );
    } else {
      rows.push("TCP Listener Probe: unavailable");
    }
  } else {
    rows.push("TCP Listener Probe: Windows netstat adapter not active");
  }
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line8).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function portCommand(args, _context) {
  const rawPort = (args[0] ?? "").trim();
  const port = Number.parseInt(rawPort, 10);
  if (!Number.isFinite(port) || port < 1 || port > 65535 || String(port) !== rawPort) {
    return immediateError7(
      `Invalid port '${rawPort}'.`,
      ["Usage: vxs port <1-65535>"]
    );
  }
  if (process.platform !== "win32") {
    return immediateError7(
      "The current runtime diagnostic adapter supports Windows netstat only."
    );
  }
  const result = runReadOnly(
    "netstat.exe",
    ["-ano", "-p", "tcp"],
    5e3
  );
  if (!result.ok) {
    return immediateError7(
      "netstat query failed.",
      result.stderr ? [result.stderr] : []
    );
  }
  const portPattern = new RegExp(`:${port}\\s`);
  const hits = result.stdout.split(/\r?\n/).filter((value) => portPattern.test(value)).slice(0, 80);
  const pids = /* @__PURE__ */ new Set();
  for (const hit of hits) {
    const parts = hit.trim().split(/\s+/);
    const pid = parts[parts.length - 1];
    if (/^\d+$/.test(pid)) pids.add(pid);
  }
  const rows = [
    "VXS PORT",
    `Port: ${port}`,
    `Matches: ${hits.length}`,
    "",
    ...hits.length ? hits : ["(no TCP rows found)"],
    ""
  ];
  if (pids.size) {
    rows.push(`PIDs: ${[...pids].join(", ")}`);
    rows.push("");
  }
  return {
    kind: "immediate",
    output: rows.map(line8).join(""),
    exitCode: 0,
    stream: "system"
  };
}
var PROCESS_QUERY_PATTERN = /^[A-Za-z0-9._+\- ]{1,128}$/;
function processCommand(args, _context) {
  const query = (args[0] ?? "").trim();
  if (!query) {
    return immediateError7(
      "Process name or PID is required.",
      ["Usage: vxs process <name|pid>"]
    );
  }
  if (!PROCESS_QUERY_PATTERN.test(query)) {
    return immediateError7("Process query contains unsupported characters.");
  }
  if (process.platform !== "win32") {
    return immediateError7(
      "The current runtime diagnostic adapter supports Windows tasklist only."
    );
  }
  const result = runReadOnly(
    "tasklist.exe",
    ["/FO", "CSV", "/NH"],
    5e3
  );
  if (!result.ok) {
    return immediateError7(
      "tasklist query failed.",
      result.stderr ? [result.stderr] : []
    );
  }
  const numeric = /^\d+$/.test(query);
  const needle = query.toLowerCase();
  const hits = result.stdout.split(/\r?\n/).filter((value) => {
    const lower = value.toLowerCase();
    if (numeric) {
      return new RegExp(`"${query}"`).test(value);
    }
    return lower.includes(needle);
  }).slice(0, 80);
  return {
    kind: "immediate",
    output: [
      "VXS PROCESS",
      `Query: ${query}`,
      `Matches: ${hits.length}`,
      "",
      ...hits.length ? hits : ["(no matching process rows found)"],
      ""
    ].map(line8).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsRuntimeDiagnosticsCommands() {
  return [
    {
      name: "runtime",
      aliases: [],
      usage: "vxs runtime",
      summary: "Inspect local VXS/Portal/Workstation runtime state",
      execute: runtimeCommand
    },
    {
      name: "port",
      aliases: ["ports"],
      usage: "vxs port <number>",
      summary: "Inspect TCP ownership for a local port",
      execute: portCommand
    },
    {
      name: "process",
      aliases: ["ps"],
      usage: "vxs process <name|pid>",
      summary: "Inspect Windows process rows",
      execute: processCommand
    },
    {
      name: "versions",
      aliases: [],
      usage: "vxs versions",
      summary: "Show development runtime/tool versions",
      execute: versionsCommand
    }
  ];
}

// src/main/shell/vxs/vxs-orchestration-capabilities.ts
var import_node_child_process6 = require("node:child_process");
function line9(value = "") {
  return `${value}
`;
}
function immediateError8(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line9).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function runReadOnly2(program, args, cwd, timeout = 5e3) {
  try {
    const result = (0, import_node_child_process6.spawnSync)(
      program,
      args,
      {
        cwd,
        windowsHide: true,
        shell: false,
        encoding: "utf-8",
        timeout
      }
    );
    return {
      ok: result.status === 0,
      stdout: (result.stdout ?? "").trim(),
      stderr: (result.stderr ?? "").trim()
    };
  } catch (error2) {
    return {
      ok: false,
      stdout: "",
      stderr: error2 instanceof Error ? error2.message : String(error2)
    };
  }
}
function commandAvailable(name) {
  const resolver = process.platform === "win32" ? "where.exe" : "which";
  return runReadOnly2(resolver, [name], void 0, 2e3).ok;
}
function packageExecutable2(packageManager) {
  if (process.platform !== "win32") return packageManager;
  return `${packageManager}.cmd`;
}
function hasMarker(workspace, marker) {
  return workspace.markers.includes(marker);
}
function unique(values) {
  return [...new Set(values)];
}
function preflightCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const gitStatus = workspace.git ? runReadOnly2(
    "git",
    ["status", "--short", "--branch", "--untracked-files=normal"],
    workspace.root,
    5e3
  ) : null;
  let changed = 0;
  let branch = "(git not detected)";
  if (gitStatus?.ok) {
    const rows2 = gitStatus.stdout.split(/\r?\n/).filter(Boolean);
    branch = rows2[0] ?? "(branch unknown)";
    changed = Math.max(0, rows2.length - 1);
  }
  let workstation = "not observed";
  if (process.platform === "win32") {
    const netstat = runReadOnly2(
      "netstat.exe",
      ["-ano", "-p", "tcp"],
      void 0,
      5e3
    );
    if (netstat.ok && netstat.stdout.split(/\r?\n/).some((value) => /127\.0\.0\.1:47832\s+.*LISTENING/i.test(value))) {
      workstation = "LISTENING";
    }
  }
  const tools = [
    ["git", commandAvailable(process.platform === "win32" ? "git.exe" : "git")],
    ["pwsh", commandAvailable(process.platform === "win32" ? "pwsh.exe" : "pwsh")],
    ["python", commandAvailable(process.platform === "win32" ? "python.exe" : "python")],
    ["cargo", commandAvailable(process.platform === "win32" ? "cargo.exe" : "cargo")]
  ];
  if (workspace.packageManager) {
    tools.push([
      workspace.packageManager,
      commandAvailable(packageExecutable2(workspace.packageManager))
    ]);
  }
  const rows = [
    "VXS PREFLIGHT",
    `Workspace Root: ${workspace.root}`,
    `Workspace Type: ${workspace.kind}`,
    `Markers: ${workspace.markers.length ? workspace.markers.join(", ") : "none"}`,
    `Package Manager: ${workspace.packageManager ?? "not detected"}`,
    `Branch: ${branch}`,
    `Changed/Untracked Rows: ${changed}`,
    `Workstation 127.0.0.1:47832: ${workstation}`,
    "",
    "Tool Availability:",
    ...tools.map(
      ([name, available]) => `  [${available ? "PASS" : "WARN"}] ${name}`
    ),
    "",
    `Scripts: ${workspace.scripts.length ? workspace.scripts.join(", ") : "none detected"}`,
    "",
    "PREFLIGHT is observation-only. No build/test/check has been executed.",
    ""
  ];
  return {
    kind: "immediate",
    output: rows.map(line9).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function addNodeVerifySteps(workspace, mode, steps, labels) {
  if (!workspace.packageManager) return;
  const executable = packageExecutable2(workspace.packageManager);
  const scripts = new Set(workspace.scripts);
  for (const candidate of ["typecheck", "check"]) {
    if (scripts.has(candidate)) {
      steps.push(`${executable} run ${candidate}`);
      labels.push(`node:${candidate}`);
      break;
    }
  }
  if (scripts.has("lint")) {
    steps.push(`${executable} run lint`);
    labels.push("node:lint");
  }
  for (const candidate of ["format:check", "format-check", "prettier:check"]) {
    if (scripts.has(candidate)) {
      steps.push(`${executable} run ${candidate}`);
      labels.push(`node:${candidate}`);
      break;
    }
  }
  if (scripts.has("test")) {
    steps.push(`${executable} run test`);
    labels.push("node:test");
  }
  if (mode === "full" && scripts.has("build")) {
    steps.push(`${executable} run build`);
    labels.push("node:build");
  }
}
function addRustVerifySteps(workspace, mode, steps, labels) {
  if (!hasMarker(workspace, "Cargo.toml")) return;
  steps.push("cargo check");
  labels.push("rust:check");
  steps.push("cargo fmt --all -- --check");
  labels.push("rust:fmt-check");
  steps.push("cargo test");
  labels.push("rust:test");
  if (mode === "full") {
    steps.push("cargo clippy --all-targets");
    labels.push("rust:clippy");
    steps.push("cargo build");
    labels.push("rust:build");
  }
}
function addPythonVerifySteps(workspace, mode, steps, labels) {
  const pythonWorkspace = hasMarker(workspace, "pyproject.toml") || hasMarker(workspace, "requirements.txt") || hasMarker(workspace, "setup.py");
  if (!pythonWorkspace) return;
  steps.push("python -m ruff check .");
  labels.push("python:ruff-check");
  steps.push("python -m ruff format --check .");
  labels.push("python:format-check");
  steps.push("python -m pytest");
  labels.push("python:test");
  if (mode === "full" && hasMarker(workspace, "pyproject.toml")) {
    steps.push("python -m build");
    labels.push("python:build");
  }
}
function changedFilesForWorkspace(workspace) {
  if (!workspace.git) {
    return {
      ok: false,
      files: [],
      error: "Git repository was not detected."
    };
  }
  const status = runReadOnly2(
    "git",
    ["status", "--short", "--untracked-files=normal"],
    workspace.root,
    5e3
  );
  if (!status.ok) {
    return {
      ok: false,
      files: [],
      error: status.stderr || "git status failed"
    };
  }
  const files = status.stdout.split(/\r?\n/).filter(Boolean).map((row) => row.length >= 4 ? row.slice(3).trim() : row.trim()).map((value) => {
    const arrow = value.lastIndexOf(" -> ");
    return arrow >= 0 ? value.slice(arrow + 4).trim() : value;
  }).map((value) => value.replace(/^"(.*)"$/, "$1")).filter(Boolean);
  return {
    ok: true,
    files: unique(files),
    error: ""
  };
}
function classifyChangedEcosystems(workspace, files) {
  const ecosystems = /* @__PURE__ */ new Set();
  const nodeExtensions = /* @__PURE__ */ new Set([
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".html"
  ]);
  const nodeNames = /* @__PURE__ */ new Set([
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "npm-shrinkwrap.json",
    "vite.config.ts",
    "vite.config.js",
    "tsconfig.json"
  ]);
  const rustNames = /* @__PURE__ */ new Set([
    "cargo.toml",
    "cargo.lock"
  ]);
  const pythonNames = /* @__PURE__ */ new Set([
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "tox.ini",
    "pytest.ini"
  ]);
  for (const raw of files) {
    const normalized = raw.replace(/\\/g, "/");
    const lower = normalized.toLowerCase();
    const base = lower.split("/").pop() ?? lower;
    const extension = base.includes(".") ? `.${base.split(".").pop()}` : "";
    if (nodeExtensions.has(extension) || nodeNames.has(base) || base.endsWith(".json")) {
      ecosystems.add("node");
    }
    if (extension === ".rs" || rustNames.has(base)) {
      ecosystems.add("rust");
    }
    if (extension === ".py" || pythonNames.has(base) || /^requirements.*\.txt$/.test(base)) {
      ecosystems.add("python");
    }
  }
  if (!ecosystems.size && files.length) {
    if (workspace.packageManager) ecosystems.add("node");
    if (hasMarker(workspace, "Cargo.toml")) ecosystems.add("rust");
    if (hasMarker(workspace, "pyproject.toml") || hasMarker(workspace, "requirements.txt") || hasMarker(workspace, "setup.py")) {
      ecosystems.add("python");
    }
  }
  return [...ecosystems];
}
function createVxsVerificationPlan(workspace, mode) {
  const steps = [];
  const labels = [];
  let changedFiles = [];
  let ecosystems = [];
  if (mode === "changed") {
    const changed = changedFilesForWorkspace(workspace);
    if (!changed.ok) return { error: changed.error };
    changedFiles = changed.files;
    if (!changedFiles.length) {
      return {
        mode,
        commands: [],
        labels: [],
        changedFiles: [],
        ecosystems: [],
        clean: true
      };
    }
    ecosystems = classifyChangedEcosystems(workspace, changedFiles);
    if (ecosystems.includes("node")) {
      addNodeVerifySteps(workspace, "quick", steps, labels);
    }
    if (ecosystems.includes("rust")) {
      addRustVerifySteps(workspace, "quick", steps, labels);
    }
    if (ecosystems.includes("python")) {
      addPythonVerifySteps(workspace, "quick", steps, labels);
    }
  } else {
    addNodeVerifySteps(workspace, mode, steps, labels);
    addRustVerifySteps(workspace, mode, steps, labels);
    addPythonVerifySteps(workspace, mode, steps, labels);
    if (workspace.packageManager) ecosystems.push("node");
    if (hasMarker(workspace, "Cargo.toml")) ecosystems.push("rust");
    if (hasMarker(workspace, "pyproject.toml") || hasMarker(workspace, "requirements.txt") || hasMarker(workspace, "setup.py")) {
      ecosystems.push("python");
    }
  }
  return {
    mode,
    commands: unique(steps),
    labels: unique(labels),
    changedFiles,
    ecosystems: unique(ecosystems),
    clean: false
  };
}
function renderVerificationPlan(plan, workspace) {
  const rows = [
    "VXS VERIFY PLAN",
    `Mode: ${plan.mode}`,
    `Workspace Root: ${workspace.root}`,
    `Ecosystems: ${plan.ecosystems.length ? plan.ecosystems.join(", ") : "none"}`,
    `Changed Files: ${plan.changedFiles.length}`,
    ""
  ];
  if (plan.changedFiles.length) {
    rows.push("Changed Scope:");
    rows.push(...plan.changedFiles.slice(0, 80).map((value) => `  ${value}`));
    if (plan.changedFiles.length > 80) {
      rows.push(`  ... ${plan.changedFiles.length - 80} more`);
    }
    rows.push("");
  }
  rows.push("Pipeline:");
  if (plan.clean) {
    rows.push("  (clean working tree; nothing to verify)");
  } else if (!plan.commands.length) {
    rows.push("  (no supported verification commands detected)");
  } else {
    plan.commands.forEach((command, index) => {
      rows.push(`  ${index + 1}. ${command}`);
    });
  }
  rows.push("");
  rows.push("PLAN_ONLY=YES");
  rows.push("");
  return rows.map(line9).join("");
}
function verifyPlanCommand(args, context) {
  const rawMode = (args[0] ?? "changed").toLowerCase();
  if (rawMode !== "quick" && rawMode !== "full" && rawMode !== "changed") {
    return immediateError8(
      `Unknown verify-plan mode '${rawMode}'.`,
      ["Usage: vxs verify-plan [quick|full|changed]"]
    );
  }
  const workspace = detectVxsWorkspace(context.cwd);
  const plan = createVxsVerificationPlan(workspace, rawMode);
  if ("error" in plan) {
    return immediateError8(plan.error);
  }
  return {
    kind: "immediate",
    output: renderVerificationPlan(plan, workspace),
    exitCode: 0,
    stream: "system"
  };
}
function chainVxsVerificationCommands(commands) {
  if (process.platform === "win32") {
    return commands.map(
      (command) => `${command}; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`
    ).join("; ");
  }
  return commands.join(" && ");
}
function verifyCommand(args, context) {
  const rawMode = (args[0] ?? "quick").toLowerCase();
  if (rawMode !== "quick" && rawMode !== "full" && rawMode !== "changed") {
    return immediateError8(
      `Unknown verify mode '${rawMode}'.`,
      ["Usage: vxs verify [quick|full|changed]"]
    );
  }
  const mode = rawMode;
  const workspace = detectVxsWorkspace(context.cwd);
  const plan = createVxsVerificationPlan(workspace, mode);
  if ("error" in plan) {
    return immediateError8(plan.error);
  }
  if (plan.clean) {
    return {
      kind: "immediate",
      output: [
        "VXS VERIFY CHANGED",
        `Workspace Root: ${workspace.root}`,
        "Changed Files: 0",
        "",
        "Clean working tree; no changed-scope verification required.",
        ""
      ].map(line9).join(""),
      exitCode: 0,
      stream: "system"
    };
  }
  if (!plan.commands.length) {
    return immediateError8(
      "No supported verification pipeline was detected.",
      [
        `Workspace Root: ${workspace.root}`,
        `Mode: ${mode}`,
        "Expected Node scripts, Cargo.toml, or a Python project marker."
      ]
    );
  }
  const result = {
    kind: "execute",
    executionCommand: chainVxsVerificationCommands(plan.commands),
    executionCwd: workspace.root,
    capability: mode === "full" ? "VERIFY_FULL" : mode === "changed" ? "VERIFY_CHANGED" : "VERIFY_QUICK",
    routeSummary: `VXS verify ${mode}: ${plan.labels.join(" -> ")}`
  };
  return result;
}
function createVxsOrchestrationCommands() {
  return [
    {
      name: "preflight",
      aliases: [],
      usage: "vxs preflight",
      summary: "Summarize workspace/runtime readiness without execution",
      execute: preflightCommand
    },
    {
      name: "verify",
      aliases: [],
      usage: "vxs verify [quick|full|changed]",
      summary: "Run a fail-fast workspace verification pipeline",
      execute: verifyCommand
    },
    {
      name: "verify-plan",
      aliases: ["vplan"],
      usage: "vxs verify-plan [quick|full|changed]",
      summary: "Preview a verification pipeline without executing it",
      execute: verifyPlanCommand
    }
  ];
}

// src/main/shell/vxs/vxs-failure-intelligence-capabilities.ts
var fs10 = __toESM(require("node:fs"), 1);
var path12 = __toESM(require("node:path"), 1);
function line10(value = "") {
  return `${value}
`;
}
function immediateError9(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line10).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
var JOB_ID_PATTERN3 = /^[A-Za-z0-9._:-]{1,256}$/;
function readJsonFile(filePath, maxBytes = 4 * 1024 * 1024) {
  try {
    const stat = fs10.statSync(filePath);
    if (!stat.isFile() || stat.size > maxBytes) return null;
    return JSON.parse(fs10.readFileSync(filePath, "utf-8"));
  } catch {
    return null;
  }
}
function readTextFile2(filePath, maxBytes = 4 * 1024 * 1024) {
  try {
    const stat = fs10.statSync(filePath);
    if (!stat.isFile() || stat.size > maxBytes) return null;
    return fs10.readFileSync(filePath, "utf-8");
  } catch {
    return null;
  }
}
function asRecord(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value;
}
function stringValue(record, key) {
  const value = record?.[key];
  return typeof value === "string" ? value : "";
}
function boolValue(record, key) {
  const value = record?.[key];
  return typeof value === "boolean" ? value : null;
}
function findRecordWithJobId(value, jobId, depth = 0) {
  if (depth > 8) return null;
  const record = asRecord(value);
  if (record) {
    if (record.job_id === jobId) return record;
    for (const child of Object.values(record)) {
      const found = findRecordWithJobId(child, jobId, depth + 1);
      if (found) return found;
    }
    return null;
  }
  if (Array.isArray(value)) {
    for (const child of value) {
      const found = findRecordWithJobId(child, jobId, depth + 1);
      if (found) return found;
    }
  }
  return null;
}
function portalMetadataRoots() {
  const appData = process.env.APPDATA ?? "";
  const localAppData = process.env.LOCALAPPDATA ?? "";
  return [
    path12.join(appData, "vertex-session-portal", "vra-dispatch"),
    path12.join(appData, "Vertex Session Portal", "vra-dispatch"),
    path12.join(localAppData, "vertex-session-portal", "vra-dispatch")
  ].filter((value) => value.length > 0);
}
function findPortalMetadata(jobId) {
  for (const root of portalMetadataRoots()) {
    if (!fs10.existsSync(root)) continue;
    let names;
    try {
      names = fs10.readdirSync(root).filter((name) => name.endsWith(".json")).slice(-600).reverse();
    } catch {
      continue;
    }
    for (const name of names) {
      const filePath = path12.join(root, name);
      const text = readTextFile2(filePath);
      if (!text || !text.includes(jobId)) continue;
      const data = readJsonFile(filePath);
      const found = findRecordWithJobId(data, jobId);
      if (found) return { path: filePath, record: found };
      const record = asRecord(data);
      if (record && record.job_id === jobId) {
        return { path: filePath, record };
      }
    }
  }
  return null;
}
function findRegistryRecord(jobId) {
  const root = "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry";
  if (!fs10.existsSync(root)) return null;
  let names;
  try {
    names = fs10.readdirSync(root).filter((name) => name.endsWith(".json")).slice(-1e3).reverse();
  } catch {
    return null;
  }
  for (const name of names) {
    const filePath = path12.join(root, name);
    const text = readTextFile2(filePath);
    if (!text || !text.includes(jobId)) continue;
    const data = readJsonFile(filePath);
    const found = findRecordWithJobId(data, jobId);
    if (found) return { path: filePath, record: found };
  }
  return null;
}
function findEvidence(jobId) {
  const roots = [
    "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\evidence",
    "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\lanes"
  ];
  let scanned = 0;
  const maxFiles = 1600;
  function walk(current, depth) {
    if (depth > 6 || scanned >= maxFiles) return null;
    let entries;
    try {
      entries = fs10.readdirSync(current, { withFileTypes: true });
    } catch {
      return null;
    }
    const ordered = [...entries].sort((a, b) => b.name.localeCompare(a.name));
    for (const entry of ordered) {
      if (scanned >= maxFiles) return null;
      const full = path12.join(current, entry.name);
      if (entry.isDirectory()) {
        const found2 = walk(full, depth + 1);
        if (found2) return found2;
        continue;
      }
      if (!entry.isFile() || !entry.name.endsWith(".json")) continue;
      scanned += 1;
      const text = readTextFile2(full);
      if (!text || !text.includes(jobId)) continue;
      const data = readJsonFile(full);
      const found = findRecordWithJobId(data, jobId);
      if (found) return { path: full, record: found };
      const record = asRecord(data);
      if (record) return { path: full, record };
    }
    return null;
  }
  for (const root of roots) {
    if (!fs10.existsSync(root)) continue;
    const found = walk(root, 0);
    if (found) return found;
  }
  return null;
}
function classify(portal, registry, evidence) {
  const lastError = (stringValue(portal, "workstation_last_error") || stringValue(portal, "workstationLastError") || stringValue(portal, "error")).toLowerCase();
  if (lastError) {
    if (lastError.includes("inspector") || lastError.includes("parse manifest")) {
      return "INSPECTOR_REJECT";
    }
    if (lastError.includes("sha") || lastError.includes("hash")) {
      return "SHA_MISMATCH";
    }
    if (lastError.includes("approval") || lastError.includes("human")) {
      return "APPROVAL_REJECT";
    }
    if (lastError.includes("routing") || lastError.includes("origin")) {
      return "ROUTING_REJECT";
    }
    if (lastError.includes("409") || lastError.includes("conflict") || lastError.includes("duplicate")) {
      return "IDENTITY_CONFLICT";
    }
    return "REGISTRATION_ERROR";
  }
  const evidenceSuccess = boolValue(evidence, "success") ?? boolValue(evidence, "verified");
  const evidenceState = (stringValue(evidence, "final_state") || stringValue(evidence, "state") || stringValue(registry, "evidence_state")).toUpperCase();
  if (evidenceSuccess === false || evidenceState === "FAILED") {
    return "VERIFY_FAILED";
  }
  const returnState = (stringValue(registry, "evidence_return_state") || stringValue(portal, "workstation_evidence_return_state") || stringValue(evidence, "evidence_return_state")).toUpperCase();
  if (returnState === "RETURNED") return "RETURNED";
  if (returnState === "RETURN_QUEUED") return "RETURN_QUEUED";
  const state2 = (stringValue(registry, "state") || stringValue(asRecord(registry?.record), "state") || stringValue(portal, "workstation_job_state")).toUpperCase();
  if (state2 === "FAILED" || state2 === "REJECTED") return state2;
  const allocated = stringValue(registry, "allocated_lane") || stringValue(asRecord(registry?.record), "execution_lane");
  if (allocated) {
    if (state2 === "EXECUTING") return "EXECUTING";
    if (state2 === "SUCCEEDED") return "SUCCEEDED";
    return "ALLOCATED";
  }
  if (state2 === "REGISTERED") return "REGISTERED";
  const registration = stringValue(portal, "workstation_registration").toUpperCase();
  if (registration === "REGISTERED") return "REGISTERED";
  if (registration === "BLOCKED") return "REGISTRATION_BLOCKED";
  if (portal || registry || evidence) return "OBSERVED_UNCLASSIFIED";
  return "NOT_FOUND";
}
function triageCommand(args, _context) {
  const jobId = (args[0] ?? "").trim();
  if (!jobId) {
    return immediateError9(
      "Job ID is required.",
      ["Usage: vxs triage <job-id>"]
    );
  }
  if (!JOB_ID_PATTERN3.test(jobId)) {
    return immediateError9("Job ID contains unsupported characters.");
  }
  const portalHit = findPortalMetadata(jobId);
  const registryHit = findRegistryRecord(jobId);
  const evidenceHit = findEvidence(jobId);
  const portal = portalHit?.record ?? null;
  const registry = registryHit?.record ?? null;
  const evidence = evidenceHit?.record ?? null;
  const classification = classify(portal, registry, evidence);
  const lastError = stringValue(portal, "workstation_last_error") || stringValue(portal, "workstationLastError") || stringValue(portal, "error");
  const state2 = stringValue(registry, "state") || stringValue(asRecord(registry?.record), "state") || stringValue(portal, "workstation_job_state");
  const allocated = stringValue(registry, "allocated_lane") || stringValue(asRecord(registry?.record), "execution_lane");
  const evidenceState = stringValue(registry, "evidence_state") || stringValue(portal, "workstation_evidence_state") || stringValue(evidence, "final_state") || stringValue(evidence, "state");
  const returnState = stringValue(registry, "evidence_return_state") || stringValue(portal, "workstation_evidence_return_state") || stringValue(evidence, "evidence_return_state");
  const rows = [
    "VXS TRIAGE",
    `Job ID: ${jobId}`,
    `Classification: ${classification}`,
    `Job State: ${state2 || "(unknown)"}`,
    `Allocated Lane: ${allocated || "(none)"}`,
    `Evidence State: ${evidenceState || "(none)"}`,
    `Return State: ${returnState || "(none)"}`,
    "",
    `Portal Metadata: ${portalHit?.path ?? "(not found)"}`,
    `Job Registry: ${registryHit?.path ?? "(not found)"}`,
    `Evidence: ${evidenceHit?.path ?? "(not found)"}`,
    ""
  ];
  if (lastError) {
    rows.push("Last Error:");
    rows.push(lastError.slice(0, 3e3));
    rows.push("");
  }
  rows.push("TRIAGE_MUTATION=NONE");
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line10).join(""),
    exitCode: classification === "NOT_FOUND" ? 1 : 0,
    stream: classification === "NOT_FOUND" ? "stderr" : "system"
  };
}
function createVxsFailureIntelligenceCommands() {
  return [
    {
      name: "triage",
      aliases: ["diagnose-job"],
      usage: "vxs triage <job-id>",
      summary: "Classify Portal/Workstation failure and lifecycle evidence",
      execute: triageCommand
    }
  ];
}

// src/main/shell/vxs/vxs-job-intelligence-capabilities.ts
var fs11 = __toESM(require("node:fs"), 1);
var path13 = __toESM(require("node:path"), 1);
function line11(value = "") {
  return `${value}
`;
}
function immediateError10(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line11).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
var JOB_ID_PATTERN4 = /^[A-Za-z0-9._:-]{1,256}$/;
var JOB_REGISTRY_ROOT = "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry";
function asRecord2(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value;
}
function stringField(record, ...keys) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}
function numberField(record, ...keys) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && /^\d+$/.test(value)) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}
function collectRecordsWithJobId(value, out, depth = 0) {
  if (depth > 8 || out.length >= 2e3) return;
  const record = asRecord2(value);
  if (record) {
    if (typeof record.job_id === "string" && record.job_id.trim()) {
      out.push(record);
    }
    for (const child of Object.values(record)) {
      collectRecordsWithJobId(child, out, depth + 1);
      if (out.length >= 2e3) return;
    }
    return;
  }
  if (Array.isArray(value)) {
    for (const child of value) {
      collectRecordsWithJobId(child, out, depth + 1);
      if (out.length >= 2e3) return;
    }
  }
}
function recordTimestamp(record, fallbackMs) {
  const direct = numberField(
    record,
    "updated_ms",
    "completed_ms",
    "created_ms",
    "started_ms"
  );
  if (direct !== null) return direct;
  const timestamps = asRecord2(record.timestamps);
  if (timestamps) {
    for (const key of [
      "updated_at",
      "completed_at",
      "created_at",
      "started_at",
      "returned_at"
    ]) {
      const value = timestamps[key];
      if (typeof value === "string") {
        const unixMatch = /^unix-ms:(\d+)$/.exec(value);
        if (unixMatch) return Number(unixMatch[1]);
        const parsed = Date.parse(value);
        if (Number.isFinite(parsed)) return parsed;
      }
      if (typeof value === "number" && Number.isFinite(value)) return value;
    }
  }
  for (const key of [
    "updated_at",
    "completed_at",
    "created_at",
    "started_at",
    "registered_utc"
  ]) {
    const value = record[key];
    if (typeof value !== "string") continue;
    const unixMatch = /^unix-ms:(\d+)$/.exec(value);
    if (unixMatch) return Number(unixMatch[1]);
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallbackMs;
}
function normalizeJob(record, sourcePath, fallbackMs) {
  const nestedRecord = asRecord2(record.record);
  const nestedEvidence = asRecord2(record.evidence);
  return {
    jobId: stringField(record, "job_id"),
    state: stringField(record, "state", "job_state", "status") || (nestedRecord ? stringField(nestedRecord, "state", "status") : ""),
    result: stringField(record, "result") || (nestedEvidence ? stringField(nestedEvidence, "result") : ""),
    artifactId: stringField(record, "artifact_id") || (nestedRecord ? stringField(nestedRecord, "artifact_id") : ""),
    lane: stringField(record, "allocated_lane", "execution_lane") || (nestedRecord ? stringField(nestedRecord, "allocated_lane", "execution_lane") : ""),
    updatedMs: recordTimestamp(record, fallbackMs),
    sourcePath,
    record
  };
}
function loadJobs() {
  if (!fs11.existsSync(JOB_REGISTRY_ROOT)) return [];
  let names;
  try {
    names = fs11.readdirSync(JOB_REGISTRY_ROOT).filter((name) => name.endsWith(".json")).slice(-1500);
  } catch {
    return [];
  }
  const dedupe = /* @__PURE__ */ new Map();
  for (const name of names) {
    const filePath = path13.join(JOB_REGISTRY_ROOT, name);
    let stat;
    let data;
    try {
      stat = fs11.statSync(filePath);
      if (!stat.isFile() || stat.size > 4 * 1024 * 1024) continue;
      data = JSON.parse(fs11.readFileSync(filePath, "utf-8"));
    } catch {
      continue;
    }
    const records = [];
    collectRecordsWithJobId(data, records);
    for (const record of records) {
      const jobId = stringField(record, "job_id");
      if (!jobId || !JOB_ID_PATTERN4.test(jobId)) continue;
      const candidate = normalizeJob(record, filePath, stat.mtimeMs);
      const existing = dedupe.get(jobId);
      if (!existing || candidate.updatedMs >= existing.updatedMs) {
        dedupe.set(jobId, candidate);
      }
    }
  }
  return [...dedupe.values()].sort((a, b) => b.updatedMs - a.updatedMs);
}
function parseLimit(raw, usage) {
  const value = (raw ?? "20").trim();
  const limit = Number.parseInt(value, 10);
  if (!Number.isFinite(limit) || limit < 1 || limit > 100 || String(limit) !== value) {
    return immediateError10(
      `Invalid limit '${value}'.`,
      [`Usage: ${usage}`, "Allowed range: 1-100"]
    );
  }
  return limit;
}
function renderJobRow(job) {
  const stamp = new Date(job.updatedMs).toISOString();
  return [
    stamp,
    job.state || job.result || "(unknown)",
    job.lane || "-",
    job.jobId,
    job.artifactId || "-"
  ].join(" | ");
}
function jobsCommand(args, _context) {
  const parsed = parseLimit(args[0], "vxs jobs [1-100]");
  if (typeof parsed !== "number") return parsed;
  const jobs = loadJobs().slice(0, parsed);
  return {
    kind: "immediate",
    output: [
      "VXS JOBS",
      `Registry Root: ${JOB_REGISTRY_ROOT}`,
      `Showing: ${jobs.length}`,
      "",
      ...jobs.length ? jobs.map(renderJobRow) : ["(no durable jobs found)"],
      ""
    ].map(line11).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function isFailedJob(job) {
  const haystack = [
    job.state,
    job.result,
    stringField(job.record, "error", "last_error", "failure_reason")
  ].join(" ").toLowerCase();
  return haystack.includes("fail") || haystack.includes("reject") || haystack.includes("rollback") || haystack.includes("error") || haystack.includes("conflict");
}
function failuresCommand(args, _context) {
  const parsed = parseLimit(args[0], "vxs failures [1-100]");
  if (typeof parsed !== "number") return parsed;
  const jobs = loadJobs().filter(isFailedJob).slice(0, parsed);
  return {
    kind: "immediate",
    output: [
      "VXS FAILURES",
      `Showing: ${jobs.length}`,
      "",
      ...jobs.length ? jobs.map(renderJobRow) : ["(no failed jobs found)"],
      ""
    ].map(line11).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function timelineEntries(record) {
  const entries = [];
  function add(label, value) {
    if (typeof value === "string" && value.trim()) {
      entries.push({ label, value: value.trim() });
      return;
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      entries.push({ label, value: String(value) });
    }
  }
  const timestamps = asRecord2(record.timestamps);
  if (timestamps) {
    for (const key of [
      "created_at",
      "registered_at",
      "started_at",
      "completed_at",
      "returned_at"
    ]) {
      add(`timestamps.${key}`, timestamps[key]);
    }
  }
  for (const key of [
    "created_at",
    "registered_utc",
    "registration_attempt_utc",
    "registered_utc",
    "started_at",
    "completed_at",
    "returned_at",
    "updated_at",
    "created_ms",
    "started_ms",
    "finished_ms",
    "completed_ms",
    "updated_ms"
  ]) {
    add(key, record[key]);
  }
  return entries;
}
function timelineCommand(args, _context) {
  const jobId = (args[0] ?? "").trim();
  if (!jobId) {
    return immediateError10(
      "Job ID is required.",
      ["Usage: vxs timeline <job-id>"]
    );
  }
  if (!JOB_ID_PATTERN4.test(jobId)) {
    return immediateError10("Job ID contains unsupported characters.");
  }
  const job = loadJobs().find((value) => value.jobId === jobId);
  if (!job) {
    return immediateError10(
      `Job was not found in the durable registry: ${jobId}`,
      ["Try: vxs jobs 100"]
    );
  }
  const entries = timelineEntries(job.record);
  const rows = [
    "VXS TIMELINE",
    `Job ID: ${job.jobId}`,
    `Artifact: ${job.artifactId || "(unknown)"}`,
    `State: ${job.state || "(unknown)"}`,
    `Result: ${job.result || "(unknown)"}`,
    `Lane: ${job.lane || "(none)"}`,
    `Registry Source: ${job.sourcePath}`,
    "",
    "Timeline:"
  ];
  if (entries.length) {
    for (const entry of entries) {
      rows.push(`  ${entry.label}: ${entry.value}`);
    }
  } else {
    rows.push("  (no explicit timestamp fields found)");
    rows.push(`  registry_file_mtime: ${new Date(job.updatedMs).toISOString()}`);
  }
  rows.push("");
  rows.push("TIMELINE_MUTATION=NONE");
  rows.push("");
  return {
    kind: "immediate",
    output: rows.map(line11).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsJobIntelligenceCommands() {
  return [
    {
      name: "jobs",
      aliases: ["job-list"],
      usage: "vxs jobs [1-100]",
      summary: "List recent durable Workstation jobs",
      execute: jobsCommand
    },
    {
      name: "failures",
      aliases: ["failed-jobs"],
      usage: "vxs failures [1-100]",
      summary: "List recent failed/rejected Workstation jobs",
      execute: failuresCommand
    },
    {
      name: "timeline",
      aliases: ["job-timeline"],
      usage: "vxs timeline <job-id>",
      summary: "Show durable lifecycle timestamps for a Job",
      execute: timelineCommand
    }
  ];
}

// src/main/shell/vxs/vxs-agent-context-capabilities.ts
var import_node_child_process7 = require("node:child_process");
var fs12 = __toESM(require("node:fs"), 1);
var path14 = __toESM(require("node:path"), 1);
function line12(value = "") {
  return `${value}
`;
}
function immediateError11(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line12).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function runReadOnly3(program, args, cwd, timeout = 5e3) {
  try {
    const result = (0, import_node_child_process7.spawnSync)(
      program,
      args,
      {
        cwd,
        windowsHide: true,
        shell: false,
        encoding: "utf-8",
        timeout
      }
    );
    return {
      ok: result.status === 0,
      stdout: (result.stdout ?? "").trim(),
      stderr: (result.stderr ?? "").trim()
    };
  } catch (error2) {
    return {
      ok: false,
      stdout: "",
      stderr: error2 instanceof Error ? error2.message : String(error2)
    };
  }
}
function firstLine(text) {
  return text.split(/\r?\n/)[0]?.trim() ?? "";
}
function toolVersion(name, program, args) {
  const result = runReadOnly3(program, args, void 0, 3e3);
  const text = firstLine(result.stdout || result.stderr);
  return {
    name,
    version: result.ok && text ? text.slice(0, 300) : null
  };
}
function workstationListenerState() {
  if (process.platform !== "win32") return "UNAVAILABLE";
  const result = runReadOnly3(
    "netstat.exe",
    ["-ano", "-p", "tcp"],
    void 0,
    5e3
  );
  if (!result.ok) return "UNAVAILABLE";
  const listening = result.stdout.split(/\r?\n/).some(
    (value) => /127\.0\.0\.1:47832\s+.*LISTENING/i.test(value)
  );
  return listening ? "LISTENING" : "NOT_OBSERVED";
}
function gitSnapshot(root, enabled) {
  if (!enabled) {
    return {
      branch: null,
      changed_count: 0,
      changed: []
    };
  }
  const branchResult = runReadOnly3(
    "git",
    ["branch", "--show-current"],
    root,
    4e3
  );
  const statusResult = runReadOnly3(
    "git",
    ["status", "--short", "--untracked-files=normal"],
    root,
    5e3
  );
  const changed = statusResult.ok ? statusResult.stdout.split(/\r?\n/).filter(Boolean).slice(0, 120) : [];
  return {
    branch: branchResult.ok && branchResult.stdout ? firstLine(branchResult.stdout) : null,
    changed_count: changed.length,
    changed
  };
}
function asRecord3(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value;
}
function stringField2(record, ...keys) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}
function numberField2(record, ...keys) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && /^\d+$/.test(value)) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return null;
}
function collectJobRecords(value, out, depth = 0) {
  if (depth > 8 || out.length >= 1200) return;
  const record = asRecord3(value);
  if (record) {
    if (typeof record.job_id === "string" && record.job_id.trim()) {
      out.push(record);
    }
    for (const child of Object.values(record)) {
      collectJobRecords(child, out, depth + 1);
      if (out.length >= 1200) return;
    }
    return;
  }
  if (Array.isArray(value)) {
    for (const child of value) {
      collectJobRecords(child, out, depth + 1);
      if (out.length >= 1200) return;
    }
  }
}
function jobTimestamp(record, fallbackMs) {
  const direct = numberField2(
    record,
    "updated_ms",
    "completed_ms",
    "created_ms",
    "started_ms"
  );
  if (direct !== null) return direct;
  const timestamps = asRecord3(record.timestamps);
  if (timestamps) {
    for (const key of [
      "updated_at",
      "completed_at",
      "created_at",
      "started_at"
    ]) {
      const value = timestamps[key];
      if (typeof value === "string") {
        const unix = /^unix-ms:(\d+)$/.exec(value);
        if (unix) return Number(unix[1]);
        const parsed = Date.parse(value);
        if (Number.isFinite(parsed)) return parsed;
      }
    }
  }
  return fallbackMs;
}
function isFailure(record) {
  const nested = asRecord3(record.record);
  const values = [
    stringField2(record, "state", "status", "result", "error", "last_error"),
    nested ? stringField2(nested, "state", "status", "result", "error") : ""
  ].join(" ").toLowerCase();
  return values.includes("fail") || values.includes("reject") || values.includes("rollback") || values.includes("error") || values.includes("conflict");
}
function recentJobs() {
  const root = "G:\\Vertex_Project\\Development\\vertex_workstation\\runtime\\headless\\job-registry";
  if (!fs12.existsSync(root)) {
    return {
      recent: [],
      failures: []
    };
  }
  let names;
  try {
    names = fs12.readdirSync(root).filter((name) => name.endsWith(".json")).slice(-800);
  } catch {
    return {
      recent: [],
      failures: []
    };
  }
  const dedupe = /* @__PURE__ */ new Map();
  for (const name of names) {
    const filePath = path14.join(root, name);
    try {
      const stat = fs12.statSync(filePath);
      if (!stat.isFile() || stat.size > 4 * 1024 * 1024) continue;
      const data = JSON.parse(
        fs12.readFileSync(filePath, "utf-8")
      );
      const records = [];
      collectJobRecords(data, records);
      for (const record of records) {
        const jobId = stringField2(record, "job_id");
        if (!jobId) continue;
        const updatedMs = jobTimestamp(record, stat.mtimeMs);
        const existing = dedupe.get(jobId);
        if (!existing || updatedMs >= existing.updatedMs) {
          dedupe.set(jobId, { record, updatedMs });
        }
      }
    } catch {
    }
  }
  const ordered = [...dedupe.entries()].sort((a, b) => b[1].updatedMs - a[1].updatedMs);
  function summarize(jobId, record, updatedMs) {
    const nested = asRecord3(record.record);
    return {
      job_id: jobId,
      state: stringField2(record, "state", "status", "job_state") || (nested ? stringField2(nested, "state", "status") : ""),
      result: stringField2(record, "result") || (nested ? stringField2(nested, "result") : ""),
      artifact_id: stringField2(record, "artifact_id") || (nested ? stringField2(nested, "artifact_id") : ""),
      lane: stringField2(record, "allocated_lane", "execution_lane") || (nested ? stringField2(nested, "allocated_lane", "execution_lane") : ""),
      updated_at: new Date(updatedMs).toISOString()
    };
  }
  const recent = ordered.slice(0, 12).map(
    ([jobId, value]) => summarize(jobId, value.record, value.updatedMs)
  );
  const failures = ordered.filter(([, value]) => isFailure(value.record)).slice(0, 8).map(
    ([jobId, value]) => summarize(jobId, value.record, value.updatedMs)
  );
  return {
    recent,
    failures
  };
}
function buildVxsAgentContextSnapshot(context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const git = gitSnapshot(workspace.root, workspace.git);
  const jobs = recentJobs();
  const memory = process.memoryUsage();
  const tools = [
    toolVersion("git", "git", ["--version"]),
    toolVersion(
      "pwsh",
      process.platform === "win32" ? "pwsh.exe" : "pwsh",
      ["--version"]
    ),
    toolVersion("python", "python", ["--version"]),
    toolVersion("cargo", "cargo", ["--version"]),
    toolVersion("rustc", "rustc", ["--version"])
  ];
  if (workspace.packageManager) {
    tools.push(
      toolVersion(
        workspace.packageManager,
        process.platform === "win32" ? `${workspace.packageManager}.cmd` : workspace.packageManager,
        ["--version"]
      )
    );
  }
  return {
    schema: "vxs-agent-context/1",
    generated_at: (/* @__PURE__ */ new Date()).toISOString(),
    host: {
      platform: process.platform,
      arch: process.arch,
      node: process.versions.node,
      electron: process.versions.electron ?? null,
      chrome: process.versions.chrome ?? null
    },
    workspace: {
      cwd: workspace.cwd,
      root: workspace.root,
      kind: workspace.kind,
      markers: workspace.markers.slice(0, 40),
      package_manager: workspace.packageManager,
      frameworks: workspace.frameworks.slice(0, 40),
      scripts: workspace.scripts.slice(0, 80),
      git: workspace.git
    },
    git,
    runtime: {
      pid: process.pid,
      uptime_seconds: Math.floor(process.uptime()),
      rss_mib: Number((memory.rss / 1024 / 1024).toFixed(1)),
      heap_used_mib: Number((memory.heapUsed / 1024 / 1024).toFixed(1)),
      workstation_47832: workstationListenerState()
    },
    tools,
    jobs,
    safety: {
      secret_env_values_included: false,
      full_log_bodies_included: false,
      filesystem_mutation: false,
      network_mutation: false
    }
  };
}
function renderText(snapshot2) {
  const rows = [
    "VXS AGENT CONTEXT",
    `Schema: ${snapshot2.schema}`,
    `Generated: ${snapshot2.generated_at}`,
    "",
    "Workspace:",
    `  Root: ${snapshot2.workspace.root}`,
    `  Type: ${snapshot2.workspace.kind}`,
    `  Package Manager: ${snapshot2.workspace.package_manager ?? "not detected"}`,
    `  Frameworks: ${snapshot2.workspace.frameworks.length ? snapshot2.workspace.frameworks.join(", ") : "none detected"}`,
    "",
    "Git:",
    `  Branch: ${snapshot2.git.branch ?? "(none)"}`,
    `  Changed Rows: ${snapshot2.git.changed_count}`,
    "",
    "Runtime:",
    `  PID: ${snapshot2.runtime.pid}`,
    `  Workstation 47832: ${snapshot2.runtime.workstation_47832}`,
    `  RSS MiB: ${snapshot2.runtime.rss_mib}`,
    "",
    "Tools:"
  ];
  for (const tool of snapshot2.tools) {
    rows.push(`  ${tool.name}: ${tool.version ?? "unavailable"}`);
  }
  rows.push("");
  rows.push(`Recent Jobs: ${snapshot2.jobs.recent.length}`);
  for (const job of snapshot2.jobs.recent.slice(0, 6)) {
    rows.push(
      `  ${job.updated_at} | ${job.state || job.result || "unknown"} | ${job.lane || "-"} | ${job.job_id}`
    );
  }
  rows.push("");
  rows.push(`Recent Failures: ${snapshot2.jobs.failures.length}`);
  for (const job of snapshot2.jobs.failures.slice(0, 5)) {
    rows.push(
      `  ${job.updated_at} | ${job.state || job.result || "unknown"} | ${job.job_id}`
    );
  }
  rows.push("");
  rows.push("Safety:");
  rows.push("  Secret environment values: NOT INCLUDED");
  rows.push("  Full log bodies: NOT INCLUDED");
  rows.push("  Mutation: NONE");
  rows.push("");
  return rows.map(line12).join("");
}
function contextCommand(args, context) {
  const option = (args[0] ?? "").trim();
  if (option && option !== "--json") {
    return immediateError11(
      `Unknown option '${option}'.`,
      ["Usage: vxs context [--json]"]
    );
  }
  const snapshot2 = buildVxsAgentContextSnapshot(context);
  return {
    kind: "immediate",
    output: option === "--json" ? `${JSON.stringify(snapshot2, null, 2)}
` : renderText(snapshot2),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsAgentContextCommands() {
  return [
    {
      name: "context",
      aliases: ["ctx"],
      usage: "vxs context [--json]",
      summary: "Create a bounded safe development context snapshot",
      execute: contextCommand
    }
  ];
}

// src/main/shell/vxs/vxs-agent-decision-capabilities.ts
function line13(value = "") {
  return `${value}
`;
}
function immediateError12(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line13).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)));
}
function assessVxsReadiness(snapshot2) {
  const signals = [];
  let score = 100;
  if (snapshot2.workspace.kind === "directory") {
    signals.push({
      level: "WARN",
      code: "WORKSPACE_UNTYPED",
      message: "No Node/Rust/Python project marker was detected."
    });
    score -= 20;
  } else {
    signals.push({
      level: "INFO",
      code: "WORKSPACE_TYPED",
      message: `Workspace type is ${snapshot2.workspace.kind}.`
    });
  }
  if (snapshot2.git.changed_count > 0) {
    signals.push({
      level: "INFO",
      code: "WORKTREE_ACTIVE",
      message: `${snapshot2.git.changed_count} changed/untracked Git rows are present.`
    });
    score -= 5;
  } else {
    signals.push({
      level: "INFO",
      code: "WORKTREE_CLEAN",
      message: "No changed/untracked Git rows were observed."
    });
  }
  if (snapshot2.jobs.failures.length > 0) {
    signals.push({
      level: "WARN",
      code: "RECENT_FAILURES",
      message: `${snapshot2.jobs.failures.length} recent failed/rejected Jobs were observed.`
    });
    score -= 25;
  } else {
    signals.push({
      level: "INFO",
      code: "NO_RECENT_FAILURES",
      message: "No recent failed/rejected Jobs were observed."
    });
  }
  if (snapshot2.runtime.workstation_47832 === "LISTENING") {
    signals.push({
      level: "INFO",
      code: "WORKSTATION_LISTENING",
      message: "Workstation loopback listener 127.0.0.1:47832 is present."
    });
  } else if (snapshot2.runtime.workstation_47832 === "NOT_OBSERVED") {
    signals.push({
      level: "WARN",
      code: "WORKSTATION_NOT_OBSERVED",
      message: "Workstation loopback listener 127.0.0.1:47832 was not observed."
    });
    score -= 15;
  } else {
    signals.push({
      level: "WARN",
      code: "WORKSTATION_PROBE_UNAVAILABLE",
      message: "Workstation listener state could not be determined."
    });
    score -= 10;
  }
  const unavailableTools = snapshot2.tools.filter((tool) => tool.version === null).map((tool) => tool.name);
  if (unavailableTools.length) {
    signals.push({
      level: "WARN",
      code: "TOOLS_UNAVAILABLE",
      message: `Unavailable tools: ${unavailableTools.join(", ")}`
    });
    score -= Math.min(20, unavailableTools.length * 4);
  }
  const boundedScore = clampScore(score);
  let state2 = "READY";
  if (signals.some((signal) => signal.level === "WARN")) {
    state2 = "ATTENTION";
  } else if (snapshot2.git.changed_count > 0) {
    state2 = "ACTIVE";
  }
  return {
    schema: "vxs-agent-readiness/1",
    generated_at: snapshot2.generated_at,
    state: state2,
    score: boundedScore,
    signals
  };
}
function recommendVxsNextCommands(snapshot2, readiness) {
  const recommendations = [];
  const latestFailure = snapshot2.jobs.failures[0];
  if (latestFailure) {
    recommendations.push({
      priority: 10,
      code: "TRIAGE_LATEST_FAILURE",
      command: `vxs triage ${latestFailure.job_id}`,
      reason: "A recent failed/rejected Workstation Job is present."
    });
  }
  if (snapshot2.runtime.workstation_47832 !== "LISTENING") {
    recommendations.push({
      priority: 20,
      code: "CHECK_RUNTIME",
      command: "vxs runtime",
      reason: "Workstation loopback listener is not currently confirmed."
    });
    recommendations.push({
      priority: 30,
      code: "CHECK_WORKSTATION",
      command: "vxs workstation status",
      reason: "Confirm the Workstation health endpoint before dispatch-oriented work."
    });
  }
  if (snapshot2.git.changed_count > 0) {
    recommendations.push({
      priority: 40,
      code: "PLAN_CHANGED_VERIFY",
      command: "vxs verify-plan changed",
      reason: "The working tree has changes; preview the scoped verification pipeline."
    });
    recommendations.push({
      priority: 50,
      code: "RUN_CHANGED_VERIFY",
      command: "vxs verify changed",
      reason: "Run only the ecosystem checks selected from the current Git changes."
    });
  } else {
    recommendations.push({
      priority: 60,
      code: "PREFLIGHT",
      command: "vxs preflight",
      reason: "The working tree is clean; refresh readiness before the next development action."
    });
  }
  if (snapshot2.workspace.kind === "directory") {
    recommendations.push({
      priority: 70,
      code: "RAY_WORKSPACE",
      command: "vxs ray",
      reason: "No typed project marker was detected; inspect the workspace before choosing a build path."
    });
  }
  return {
    schema: "vxs-agent-recommendations/1",
    generated_at: snapshot2.generated_at,
    readiness: readiness.state,
    recommendations: recommendations.sort(
      (a, b) => a.priority - b.priority
    )
  };
}
function renderReadiness(value) {
  const rows = [
    "VXS READINESS",
    `Schema: ${value.schema}`,
    `Generated: ${value.generated_at}`,
    `State: ${value.state}`,
    `Score: ${value.score}/100`,
    "",
    "Signals:"
  ];
  for (const signal of value.signals) {
    rows.push(`  [${signal.level}] ${signal.code} - ${signal.message}`);
  }
  rows.push("");
  rows.push("READINESS_EXECUTION=NONE");
  rows.push("");
  return rows.map(line13).join("");
}
function renderRecommendations(value) {
  const rows = [
    "VXS RECOMMEND",
    `Schema: ${value.schema}`,
    `Generated: ${value.generated_at}`,
    `Readiness: ${value.readiness}`,
    "",
    "Recommended Next Commands:"
  ];
  if (!value.recommendations.length) {
    rows.push("  (none)");
  } else {
    for (const item of value.recommendations) {
      rows.push(`  P${item.priority} ${item.code}`);
      rows.push(`    ${item.command}`);
      rows.push(`    ${item.reason}`);
    }
  }
  rows.push("");
  rows.push("RECOMMENDATION_EXECUTION=NONE");
  rows.push("");
  return rows.map(line13).join("");
}
function parseJsonOption(args, usage) {
  const option = (args[0] ?? "").trim();
  if (!option) return false;
  if (option === "--json") return true;
  return immediateError12(
    `Unknown option '${option}'.`,
    [`Usage: ${usage}`]
  );
}
function readinessCommand(args, context) {
  const json = parseJsonOption(args, "vxs readiness [--json]");
  if (typeof json !== "boolean") return json;
  const snapshot2 = buildVxsAgentContextSnapshot(context);
  const value = assessVxsReadiness(snapshot2);
  return {
    kind: "immediate",
    output: json ? `${JSON.stringify(value, null, 2)}
` : renderReadiness(value),
    exitCode: 0,
    stream: "system"
  };
}
function recommendCommand(args, context) {
  const json = parseJsonOption(args, "vxs recommend [--json]");
  if (typeof json !== "boolean") return json;
  const snapshot2 = buildVxsAgentContextSnapshot(context);
  const readiness = assessVxsReadiness(snapshot2);
  const value = recommendVxsNextCommands(snapshot2, readiness);
  return {
    kind: "immediate",
    output: json ? `${JSON.stringify(value, null, 2)}
` : renderRecommendations(value),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsAgentDecisionCommands() {
  return [
    {
      name: "readiness",
      aliases: ["ready"],
      usage: "vxs readiness [--json]",
      summary: "Assess bounded development readiness from current context",
      execute: readinessCommand
    },
    {
      name: "recommend",
      aliases: ["next"],
      usage: "vxs recommend [--json]",
      summary: "Recommend existing VXS commands without executing them",
      execute: recommendCommand
    }
  ];
}

// src/main/shell/vxs/vxs-agent-handoff-capabilities.ts
function line14(value = "") {
  return `${value}
`;
}
function immediateError13(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line14).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function buildVxsAgentHandoffPacket(context) {
  const snapshot2 = buildVxsAgentContextSnapshot(context);
  const readiness = assessVxsReadiness(snapshot2);
  const recommendations = recommendVxsNextCommands(
    snapshot2,
    readiness
  );
  return {
    schema: "vxs-agent-handoff/1",
    generated_at: snapshot2.generated_at,
    context: snapshot2,
    readiness,
    recommendations,
    authority: {
      advisory_only: true,
      human_gate_required_for_vra_execution: true,
      workstation_lane_authority_preserved: true,
      automatic_execution: false
    }
  };
}
function renderHandoff(packet) {
  const rows = [
    "VXS AGENT HANDOFF",
    `Schema: ${packet.schema}`,
    `Generated: ${packet.generated_at}`,
    "",
    "Workspace:",
    `  Root: ${packet.context.workspace.root}`,
    `  Type: ${packet.context.workspace.kind}`,
    `  Branch: ${packet.context.git.branch ?? "(none)"}`,
    `  Changed Rows: ${packet.context.git.changed_count}`,
    "",
    "Readiness:",
    `  State: ${packet.readiness.state}`,
    `  Score: ${packet.readiness.score}/100`,
    "",
    "Signals:"
  ];
  for (const signal of packet.readiness.signals.slice(0, 12)) {
    rows.push(
      `  [${signal.level}] ${signal.code} - ${signal.message}`
    );
  }
  rows.push("");
  rows.push("Recommended Next Commands:");
  if (!packet.recommendations.recommendations.length) {
    rows.push("  (none)");
  } else {
    for (const item of packet.recommendations.recommendations.slice(0, 8)) {
      rows.push(
        `  P${item.priority} ${item.code}: ${item.command}`
      );
      rows.push(`    ${item.reason}`);
    }
  }
  rows.push("");
  rows.push("Recent Jobs:");
  if (!packet.context.jobs.recent.length) {
    rows.push("  (none)");
  } else {
    for (const job of packet.context.jobs.recent.slice(0, 6)) {
      rows.push(
        `  ${job.updated_at} | ${job.state || job.result || "unknown"} | ${job.job_id}`
      );
    }
  }
  rows.push("");
  rows.push("Recent Failures:");
  if (!packet.context.jobs.failures.length) {
    rows.push("  (none)");
  } else {
    for (const job of packet.context.jobs.failures.slice(0, 5)) {
      rows.push(
        `  ${job.updated_at} | ${job.state || job.result || "unknown"} | ${job.job_id}`
      );
    }
  }
  rows.push("");
  rows.push("Authority:");
  rows.push("  Advisory only: YES");
  rows.push("  Automatic execution: NO");
  rows.push("  Human Gate required for VRA execution: YES");
  rows.push("  Workstation lane authority preserved: YES");
  rows.push("");
  rows.push("HANDOFF_MUTATION=NONE");
  rows.push("");
  return rows.map(line14).join("");
}
function handoffCommand(args, context) {
  const option = (args[0] ?? "").trim();
  if (option && option !== "--json") {
    return immediateError13(
      `Unknown option '${option}'.`,
      ["Usage: vxs handoff [--json]"]
    );
  }
  const packet = buildVxsAgentHandoffPacket(context);
  return {
    kind: "immediate",
    output: option === "--json" ? `${JSON.stringify(packet, null, 2)}
` : renderHandoff(packet),
    exitCode: 0,
    stream: "system"
  };
}
function createVxsAgentHandoffCommands() {
  return [
    {
      name: "handoff",
      aliases: ["brief"],
      usage: "vxs handoff [--json]",
      summary: "Bundle context, readiness and recommendations for agent handoff",
      execute: handoffCommand
    }
  ];
}

// src/main/shell/vxs/vxs-capability-discovery.ts
var EXECUTE_LOCAL = /* @__PURE__ */ new Set([
  "build",
  "test",
  "lint",
  "run",
  "check",
  "verify",
  "prepare"
]);
var HUMAN_GATED = /* @__PURE__ */ new Set([
  "vra"
]);
function classify2(command) {
  if (HUMAN_GATED.has(command.name)) {
    return {
      safetyClass: "HUMAN_GATED",
      requiresHumanGate: true,
      automaticExecution: false
    };
  }
  if (EXECUTE_LOCAL.has(command.name)) {
    return {
      safetyClass: "EXECUTE_LOCAL",
      requiresHumanGate: false,
      automaticExecution: false
    };
  }
  return {
    safetyClass: "OBSERVE",
    requiresHumanGate: false,
    automaticExecution: false
  };
}
function describeVxsCapability(command) {
  const safety = classify2(command);
  return {
    name: command.name,
    aliases: [...command.aliases],
    usage: command.usage,
    summary: command.summary,
    safety_class: safety.safetyClass,
    requires_human_gate: safety.requiresHumanGate,
    automatic_execution: safety.automaticExecution
  };
}
function buildVxsCapabilityCatalog(commands) {
  const capabilities = commands.map(describeVxsCapability).sort((a, b) => a.name.localeCompare(b.name));
  return {
    schema: "vxs-capabilities/1",
    command_count: capabilities.length,
    capabilities
  };
}
function line15(value = "") {
  return `${value}
`;
}
function errorResult3(message, usage) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      `Usage: ${usage}`,
      ""
    ].map(line15).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function createVxsCapabilityDiscoveryCommands(getCommands) {
  function capabilitiesCommand(args) {
    const option = (args[0] ?? "").trim();
    if (option && option !== "--json") {
      return errorResult3(
        `Unknown option '${option}'.`,
        "vxs capabilities [--json]"
      );
    }
    const catalog = buildVxsCapabilityCatalog(getCommands());
    const capabilities = catalog.capabilities;
    if (option === "--json") {
      return {
        kind: "immediate",
        output: `${JSON.stringify(catalog, null, 2)}
`,
        exitCode: 0,
        stream: "system"
      };
    }
    const rows = [
      "VXS CAPABILITIES",
      `Schema: ${catalog.schema}`,
      `Commands: ${catalog.command_count}`,
      ""
    ];
    for (const item of capabilities) {
      rows.push(
        `${item.name} | ${item.safety_class} | ${item.usage}`
      );
      rows.push(`  ${item.summary}`);
    }
    rows.push("");
    rows.push("CAPABILITY_DISCOVERY_EXECUTION=NONE");
    rows.push("");
    return {
      kind: "immediate",
      output: rows.map(line15).join(""),
      exitCode: 0,
      stream: "system"
    };
  }
  function describeCommand(args) {
    const token = (args[0] ?? "").trim().toLowerCase();
    const option = (args[1] ?? "").trim();
    if (!token) {
      return errorResult3(
        "Command name is required.",
        "vxs describe <command> [--json]"
      );
    }
    if (option && option !== "--json") {
      return errorResult3(
        `Unknown option '${option}'.`,
        "vxs describe <command> [--json]"
      );
    }
    const command = getCommands().find(
      (item2) => item2.name.toLowerCase() === token || item2.aliases.some((alias) => alias.toLowerCase() === token)
    );
    if (!command) {
      return {
        kind: "immediate",
        output: [
          `ERROR: Unknown VXS command '${token}'.`,
          "Run: vxs capabilities",
          ""
        ].map(line15).join(""),
        exitCode: 2,
        stream: "stderr"
      };
    }
    const detail = {
      schema: "vxs-capability/1",
      capability: describeVxsCapability(command)
    };
    if (option === "--json") {
      return {
        kind: "immediate",
        output: `${JSON.stringify(detail, null, 2)}
`,
        exitCode: 0,
        stream: "system"
      };
    }
    const item = detail.capability;
    const rows = [
      "VXS CAPABILITY",
      `Schema: ${detail.schema}`,
      `Name: ${item.name}`,
      `Aliases: ${item.aliases.length ? item.aliases.join(", ") : "(none)"}`,
      `Usage: ${item.usage}`,
      `Summary: ${item.summary}`,
      `Safety: ${item.safety_class}`,
      `Human Gate: ${item.requires_human_gate ? "REQUIRED" : "NO"}`,
      `Automatic Execution: ${item.automatic_execution ? "YES" : "NO"}`,
      "",
      "CAPABILITY_DISCOVERY_EXECUTION=NONE",
      ""
    ];
    return {
      kind: "immediate",
      output: rows.map(line15).join(""),
      exitCode: 0,
      stream: "system"
    };
  }
  return [
    {
      name: "capabilities",
      aliases: ["caps"],
      usage: "vxs capabilities [--json]",
      summary: "List machine-discoverable VXS command capabilities",
      execute: capabilitiesCommand
    },
    {
      name: "describe",
      aliases: ["capability"],
      usage: "vxs describe <command> [--json]",
      summary: "Describe one VXS command and its safety class",
      execute: describeCommand
    }
  ];
}

// src/main/shell/vxs/vxs-autonomy-foundation-capabilities.ts
function line16(value = "") {
  return `${value}
`;
}
function errorResult4(message, usage) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      `Usage: ${usage}`,
      ""
    ].map(line16).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
var NAME_PATTERN = /^[a-z0-9][a-z0-9-]*$/;
var ALIAS_PATTERN = /^(?:--?[a-z0-9][a-z0-9-]*|[a-z0-9][a-z0-9-]*)$/;
var AUTO_LOCAL_ALLOWLIST = /* @__PURE__ */ new Set([
  "check",
  "lint",
  "test",
  "build",
  "verify",
  "prepare"
]);
var AUTO_EXECUTION_DENYLIST = /* @__PURE__ */ new Set([
  "run",
  "vra"
]);
function pushCheck(checks, code, ok, detail) {
  checks.push({
    code,
    status: ok ? "PASS" : "FAIL",
    detail
  });
}
function duplicateValues(values) {
  const counts = /* @__PURE__ */ new Map();
  for (const raw of values) {
    const value = raw.toLowerCase();
    counts.set(value, (counts.get(value) ?? 0) + 1);
  }
  return [...counts.entries()].filter(([, count]) => count > 1).map(([value]) => value).sort();
}
function runVxsSelfTest(commands) {
  const checks = [];
  const catalog = buildVxsCapabilityCatalog(commands);
  const names = commands.map((command) => command.name);
  const aliases = commands.flatMap((command) => command.aliases);
  const duplicateNames = duplicateValues(names);
  pushCheck(
    checks,
    "UNIQUE_COMMAND_NAMES",
    duplicateNames.length === 0,
    duplicateNames.length ? `Duplicates: ${duplicateNames.join(", ")}` : "All canonical command names are unique."
  );
  const duplicateAliases = duplicateValues(aliases);
  pushCheck(
    checks,
    "UNIQUE_ALIASES",
    duplicateAliases.length === 0,
    duplicateAliases.length ? `Duplicates: ${duplicateAliases.join(", ")}` : "All aliases are unique."
  );
  const canonical = new Set(names.map((value) => value.toLowerCase()));
  const shadowedAliases = aliases.map((value) => value.toLowerCase()).filter((value) => canonical.has(value));
  pushCheck(
    checks,
    "ALIASES_DO_NOT_SHADOW_COMMANDS",
    shadowedAliases.length === 0,
    shadowedAliases.length ? `Shadowing aliases: ${[...new Set(shadowedAliases)].join(", ")}` : "No alias shadows a canonical command name."
  );
  const invalidNames = names.filter((value) => !NAME_PATTERN.test(value));
  pushCheck(
    checks,
    "COMMAND_NAME_FORMAT",
    invalidNames.length === 0,
    invalidNames.length ? `Invalid names: ${invalidNames.join(", ")}` : "Canonical names satisfy the VXS command token contract."
  );
  const invalidAliases = aliases.filter(
    (value) => !ALIAS_PATTERN.test(value)
  );
  pushCheck(
    checks,
    "ALIAS_FORMAT",
    invalidAliases.length === 0,
    invalidAliases.length ? `Invalid aliases: ${invalidAliases.join(", ")}` : "Aliases satisfy the VXS token contract."
  );
  const invalidUsage = commands.filter((command) => !/^vxs(?:\s|$)/.test(command.usage)).map((command) => command.name);
  pushCheck(
    checks,
    "USAGE_PREFIX",
    invalidUsage.length === 0,
    invalidUsage.length ? `Usage missing vxs prefix: ${invalidUsage.join(", ")}` : "Every usage string starts with vxs."
  );
  pushCheck(
    checks,
    "CATALOG_COUNT_MATCH",
    catalog.command_count === commands.length,
    `${catalog.command_count}/${commands.length} commands represented.`
  );
  const invalidHumanGate = catalog.capabilities.filter(
    (item) => item.safety_class === "HUMAN_GATED" && (!item.requires_human_gate || item.automatic_execution)
  ).map((item) => item.name);
  pushCheck(
    checks,
    "HUMAN_GATE_CONTRACT",
    invalidHumanGate.length === 0,
    invalidHumanGate.length ? `Invalid HUMAN_GATED metadata: ${invalidHumanGate.join(", ")}` : "HUMAN_GATED commands require Human Gate and disable auto execution."
  );
  const vra = catalog.capabilities.find((item) => item.name === "vra");
  pushCheck(
    checks,
    "VRA_IS_HUMAN_GATED",
    Boolean(vra && vra.safety_class === "HUMAN_GATED"),
    vra ? `vra safety=${vra.safety_class}` : "vra capability was not found."
  );
  const arbitraryRun = catalog.capabilities.find(
    (item) => item.name === "run"
  );
  pushCheck(
    checks,
    "ARBITRARY_RUN_NOT_AUTOMATIC",
    Boolean(
      arbitraryRun && arbitraryRun.safety_class === "EXECUTE_LOCAL" && !arbitraryRun.automatic_execution
    ),
    arbitraryRun ? `run safety=${arbitraryRun.safety_class}, automatic=${arbitraryRun.automatic_execution}` : "run capability was not found."
  );
  const status = checks.some((check) => check.status === "FAIL") ? "FAIL" : "PASS";
  return {
    schema: "vxs-selftest/1",
    status,
    command_count: commands.length,
    checks
  };
}
function buildVxsAutonomyPolicy(capabilities) {
  const existing = new Set(capabilities.map((item) => item.name));
  const automaticExecutionAllowlist = [...AUTO_LOCAL_ALLOWLIST].filter((name) => existing.has(name)).sort();
  const automaticExecutionDenylist = [...AUTO_EXECUTION_DENYLIST].filter((name) => existing.has(name)).sort();
  const humanGatedCommands = capabilities.filter((item) => item.safety_class === "HUMAN_GATED").map((item) => item.name).sort();
  return {
    schema: "vxs-autonomy-policy/1",
    mode: "AUTONOMOUS_PREPARATION",
    automatic_observation: true,
    automatic_local_verification: true,
    automatic_execution_allowlist: automaticExecutionAllowlist,
    automatic_execution_denylist: automaticExecutionDenylist,
    human_gated_commands: humanGatedCommands,
    rules: {
      human_gate_bypass: false,
      workstation_lane_allocation_authority: "WORKSTATION",
      observation_authoritative: false,
      production_mutation_during_verify: false,
      arbitrary_run_auto_execution: false
    }
  };
}
function renderSelfTest(result) {
  const rows = [
    "VXS SELFTEST",
    `Schema: ${result.schema}`,
    `Status: ${result.status}`,
    `Commands: ${result.command_count}`,
    ""
  ];
  for (const check of result.checks) {
    rows.push(
      `  [${check.status}] ${check.code} - ${check.detail}`
    );
  }
  rows.push("");
  rows.push("SELFTEST_MUTATION=NONE");
  rows.push("");
  return rows.map(line16).join("");
}
function renderPolicy(policy) {
  const rows = [
    "VXS AUTONOMY POLICY",
    `Schema: ${policy.schema}`,
    `Mode: ${policy.mode}`,
    "",
    `Automatic Observation: ${policy.automatic_observation ? "YES" : "NO"}`,
    `Automatic Local Verification: ${policy.automatic_local_verification ? "YES" : "NO"}`,
    `Auto Execute Allowlist: ${policy.automatic_execution_allowlist.length ? policy.automatic_execution_allowlist.join(", ") : "(none)"}`,
    `Auto Execute Denylist: ${policy.automatic_execution_denylist.length ? policy.automatic_execution_denylist.join(", ") : "(none)"}`,
    `Human Gated Commands: ${policy.human_gated_commands.length ? policy.human_gated_commands.join(", ") : "(none)"}`,
    "",
    "Fixed Rules:",
    "  Human Gate bypass: NO",
    "  Lane Allocation Authority: WORKSTATION",
    "  Observation authoritative: NO",
    "  Production mutation during VERIFY: NO",
    "  Arbitrary run auto execution: NO",
    "",
    "POLICY_EXECUTION=NONE",
    ""
  ];
  return rows.map(line16).join("");
}
function createVxsAutonomyFoundationCommands(getCommands) {
  function selftestCommand(args) {
    const option = (args[0] ?? "").trim();
    if (option && option !== "--json") {
      return errorResult4(
        `Unknown option '${option}'.`,
        "vxs selftest [--json]"
      );
    }
    const result = runVxsSelfTest(getCommands());
    return {
      kind: "immediate",
      output: option === "--json" ? `${JSON.stringify(result, null, 2)}
` : renderSelfTest(result),
      exitCode: result.status === "PASS" ? 0 : 1,
      stream: result.status === "PASS" ? "system" : "stderr"
    };
  }
  function policyCommand(args) {
    const option = (args[0] ?? "").trim();
    if (option && option !== "--json") {
      return errorResult4(
        `Unknown option '${option}'.`,
        "vxs policy [--json]"
      );
    }
    const catalog = buildVxsCapabilityCatalog(getCommands());
    const policy = buildVxsAutonomyPolicy(catalog.capabilities);
    return {
      kind: "immediate",
      output: option === "--json" ? `${JSON.stringify(policy, null, 2)}
` : renderPolicy(policy),
      exitCode: 0,
      stream: "system"
    };
  }
  return [
    {
      name: "selftest",
      aliases: ["contract-check"],
      usage: "vxs selftest [--json]",
      summary: "Validate VXS registry and authority contracts",
      execute: selftestCommand
    },
    {
      name: "policy",
      aliases: ["authority-policy"],
      usage: "vxs policy [--json]",
      summary: "Describe autonomous preparation and Human Gate policy",
      execute: policyCommand
    }
  ];
}

// src/main/shell/vxs/vxs-autonomous-preparation-capabilities.ts
function line17(value = "") {
  return `${value}
`;
}
function immediateError14(message, hints = []) {
  return {
    kind: "immediate",
    output: [`ERROR: ${message}`, ...hints, ""].map(line17).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function powerShellLiteral(value) {
  return `'${value.replace(/'/g, "''")}'`;
}
function posixLiteral(value) {
  return `'${value.replace(/'/g, `'"'"'`)}'`;
}
function appendApprovalEmitter(verificationCommand, packet) {
  const json = JSON.stringify(packet);
  if (process.platform === "win32") {
    return [
      verificationCommand,
      `Write-Output 'VXS_APPROVAL_POINT/1'`,
      `Write-Output ${powerShellLiteral(json)}`,
      `Write-Output '[/VXS_APPROVAL_POINT/1]'`
    ].join("; ");
  }
  return [
    verificationCommand,
    `printf '%s\\n' 'VXS_APPROVAL_POINT/1' ${posixLiteral(json)} '[/VXS_APPROVAL_POINT/1]'`
  ].join(" && ");
}
function buildPlan2(context, commands) {
  const selftest = runVxsSelfTest(commands);
  if (selftest.status !== "PASS") {
    const failed = selftest.checks.filter((check) => check.status === "FAIL").map((check) => check.code).join(", ");
    return {
      error: `VXS self-test failed: ${failed || "unknown contract failure"}`
    };
  }
  const catalog = buildVxsCapabilityCatalog(commands);
  const policy = buildVxsAutonomyPolicy(catalog.capabilities);
  if (!policy.automatic_local_verification || !policy.automatic_execution_allowlist.includes("verify") || !policy.automatic_execution_allowlist.includes("prepare")) {
    return {
      error: "Autonomy policy does not permit autonomous safe preparation."
    };
  }
  const snapshot2 = buildVxsAgentContextSnapshot(context);
  const readiness = assessVxsReadiness(snapshot2);
  const recommendations = recommendVxsNextCommands(
    snapshot2,
    readiness
  );
  const workspace = detectVxsWorkspace(context.cwd);
  const verifyMode = snapshot2.workspace.git ? "changed" : "quick";
  const verifyPlan = createVxsVerificationPlan(
    workspace,
    verifyMode
  );
  if ("error" in verifyPlan) {
    return {
      error: `Verification planning failed: ${verifyPlan.error}`
    };
  }
  const plan = {
    schema: "vxs-preparation-plan/1",
    generated_at: snapshot2.generated_at,
    mode: "AUTONOMOUS_PREPARATION",
    workspace: {
      root: snapshot2.workspace.root,
      branch: snapshot2.git.branch,
      changed_count: snapshot2.git.changed_count
    },
    selftest: "PASS",
    readiness: {
      state: readiness.state,
      score: readiness.score
    },
    verification: {
      mode: verifyPlan.mode,
      ecosystems: verifyPlan.ecosystems,
      changed_files: verifyPlan.changedFiles.length,
      steps: verifyPlan.labels,
      clean: verifyPlan.clean
    },
    authority: {
      automatic_safe_verification: true,
      arbitrary_run_auto_execution: false,
      vra_auto_dispatch: false,
      human_gate_bypass: false,
      workstation_lane_allocation_authority: "WORKSTATION"
    }
  };
  const recommendedNextCommands = recommendations.recommendations.map((item) => item.command).filter((command) => !/^vxs\s+prepare(?:\s|$)/i.test(command)).slice(0, 8);
  const noChanges = verifyPlan.mode === "changed" && verifyPlan.clean;
  const approval = {
    schema: "vxs-approval-point/1",
    generated_at: snapshot2.generated_at,
    status: noChanges ? "NO_CHANGES" : "READY_FOR_HUMAN_REVIEW",
    workspace: {
      root: snapshot2.workspace.root,
      branch: snapshot2.git.branch,
      changed_count: snapshot2.git.changed_count
    },
    readiness: {
      state: readiness.state,
      score: readiness.score
    },
    safe_verification: {
      mode: verifyPlan.mode,
      result: noChanges ? "SKIPPED_CLEAN" : "PASS_IF_PACKET_EMITTED",
      steps: verifyPlan.labels
    },
    recommended_next_commands: recommendedNextCommands,
    approval: {
      required: !noChanges,
      type: noChanges ? "NONE" : "HUMAN_GATE",
      instruction: noChanges ? "No changed-scope approval is required." : "Review the proposed mutation/VRA at the existing Human Gate. VXS has not dispatched or applied it."
    },
    authority: {
      human_gate_bypass: false,
      automatic_vra_dispatch: false,
      arbitrary_run_auto_execution: false,
      workstation_lane_allocation_authority: "WORKSTATION",
      observation_authoritative: false
    }
  };
  return {
    plan,
    verifyPlan,
    approval
  };
}
function renderPlan(plan, approval) {
  const rows = [
    "VXS AUTONOMOUS PREPARATION PLAN",
    `Schema: ${plan.schema}`,
    `Generated: ${plan.generated_at}`,
    `Workspace: ${plan.workspace.root}`,
    `Branch: ${plan.workspace.branch ?? "(none)"}`,
    `Changed Rows: ${plan.workspace.changed_count}`,
    `Readiness: ${plan.readiness.state} (${plan.readiness.score}/100)`,
    `Verification Mode: ${plan.verification.mode}`,
    `Verification Steps: ${plan.verification.steps.length}`,
    ""
  ];
  if (plan.verification.steps.length) {
    for (const step of plan.verification.steps) {
      rows.push(`  ${step}`);
    }
  } else if (plan.verification.clean) {
    rows.push("  (clean working tree; no changed-scope verification required)");
  } else {
    rows.push("  (no supported verification steps detected)");
  }
  rows.push("");
  rows.push(`Approval Status: ${approval.status}`);
  rows.push(`Human Gate Required: ${approval.approval.required ? "YES" : "NO"}`);
  rows.push("Automatic VRA Dispatch: NO");
  rows.push("Arbitrary run Auto Execution: NO");
  rows.push("Lane Allocation Authority: WORKSTATION");
  rows.push("");
  rows.push("PLAN_ONLY=YES");
  rows.push("");
  return rows.map(line17).join("");
}
function renderApproval(packet) {
  return [
    "VXS_APPROVAL_POINT/1",
    JSON.stringify(packet),
    "[/VXS_APPROVAL_POINT/1]",
    ""
  ].map(line17).join("");
}
function createVxsAutonomousPreparationCommands(getCommands) {
  function prepareCommand(args, context) {
    const option = (args[0] ?? "").trim();
    if (option && option !== "--plan" && option !== "--json") {
      return immediateError14(
        `Unknown option '${option}'.`,
        [
          "Usage: vxs prepare [--plan|--json]",
          "Default: execute policy-approved safe verification and emit an approval point only after success."
        ]
      );
    }
    const built = buildPlan2(context, getCommands());
    if ("error" in built) {
      return immediateError14(
        built.error,
        [
          "Autonomous preparation stopped fail-closed.",
          "No VRA was dispatched and no Human Gate was bypassed."
        ]
      );
    }
    const { plan, verifyPlan, approval } = built;
    if (option === "--json") {
      return {
        kind: "immediate",
        output: `${JSON.stringify({
          schema: "vxs-autonomous-preparation/1",
          plan,
          approval_preview: approval
        }, null, 2)}
`,
        exitCode: 0,
        stream: "system"
      };
    }
    if (option === "--plan") {
      return {
        kind: "immediate",
        output: renderPlan(plan, approval),
        exitCode: 0,
        stream: "system"
      };
    }
    if (verifyPlan.clean) {
      return {
        kind: "immediate",
        output: renderApproval(approval),
        exitCode: 0,
        stream: "system"
      };
    }
    if (!verifyPlan.commands.length) {
      return immediateError14(
        "Autonomous preparation has changes but no supported safe verification pipeline.",
        [
          "Run: vxs prepare --plan",
          "Run: vxs ray",
          "No approval point was emitted."
        ]
      );
    }
    const verificationCommand = chainVxsVerificationCommands(verifyPlan.commands);
    const result = {
      kind: "execute",
      executionCommand: appendApprovalEmitter(
        verificationCommand,
        approval
      ),
      executionCwd: plan.workspace.root,
      capability: "AUTONOMOUS_PREPARATION_SAFE_VERIFY",
      routeSummary: `VXS prepare: selftest PASS -> ${verifyPlan.mode} safe verify -> Human Gate approval point`
    };
    return result;
  }
  return [
    {
      name: "prepare",
      aliases: ["prep"],
      usage: "vxs prepare [--plan|--json]",
      summary: "Autonomously prepare safe verification up to the Human Gate",
      execute: prepareCommand
    }
  ];
}

// src/main/shell/vxs/vxs-powershell-engine-adapter.ts
var import_node_buffer = require("node:buffer");
var ENGINE_SCHEMA = "vxs-powershell-engine/1";
function encodeRequest(request2) {
  return import_node_buffer.Buffer.from(
    JSON.stringify({ schema: ENGINE_SCHEMA, ...request2 }),
    "utf8"
  ).toString("base64");
}
var ENGINE_CORE = String.raw`
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-VxsJson([object]$Value) {
  $Value | ConvertTo-Json -Depth 24 -Compress
}

function Resolve-VxsCommandInfo([string]$Name) {
  $info = Get-Command -Name $Name -ErrorAction Stop | Select-Object -First 1
  $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  while ($info -is [System.Management.Automation.AliasInfo]) {
    if (-not $seen.Add($info.Name)) { break }
    $info = $info.ResolvedCommand
    if ($null -eq $info) { throw "Alias '$Name' could not be resolved." }
  }
  return $info
}

function Get-VxsCommandSafety([System.Management.Automation.CommandInfo]$Info) {
  $safeVerbs = @('Get','Test','Find','Measure','Compare','Resolve')
  $safeNames = @(
    'Where-Object','ForEach-Object','Select-Object','Sort-Object','Group-Object',
    'Format-Table','Format-List','Format-Wide','Out-String',
    'Write-Output','Write-Host','Write-Verbose','Write-Debug','Write-Information',
    'ConvertTo-Json','ConvertFrom-Json','ConvertTo-Csv','ConvertFrom-Csv',
    'ConvertTo-Xml','Select-Xml'
  )
  $interactiveDeny = @('Get-Credential','Read-Host','Out-GridView','Show-Command')

  $metadata = $null
  try { $metadata = [System.Management.Automation.CommandMetadata]::new($Info) } catch {}
  $supportsShouldProcess = $false
  $confirmImpact = $null
  if ($null -ne $metadata) {
    $supportsShouldProcess = [bool]$metadata.SupportsShouldProcess
    $confirmImpact = [string]$metadata.ConfirmImpact
  }

  $verb = if ($Info.Name -match '^([^-]+)-') { $Matches[1] } else { '' }
  $commandType = [string]$Info.CommandType
  $trustedType = $Info.CommandType -eq [System.Management.Automation.CommandTypes]::Cmdlet

  if ($interactiveDeny -contains $Info.Name) {
    return [pscustomobject]@{ safety='HUMAN_GATED'; authority='HUMAN_APPLY'; reason='INTERACTIVE_COMMAND'; supports_should_process=$supportsShouldProcess; confirm_impact=$confirmImpact }
  }
  if ($supportsShouldProcess) {
    return [pscustomobject]@{ safety='HUMAN_GATED'; authority='HUMAN_APPLY'; reason='SUPPORTS_SHOULD_PROCESS'; supports_should_process=$supportsShouldProcess; confirm_impact=$confirmImpact }
  }
  if (-not $trustedType) {
    return [pscustomobject]@{ safety='HUMAN_GATED'; authority='HUMAN_APPLY'; reason="UNTRUSTED_COMMAND_TYPE:$commandType"; supports_should_process=$supportsShouldProcess; confirm_impact=$confirmImpact }
  }
  if (($safeVerbs -contains $verb) -or ($safeNames -contains $Info.Name)) {
    return [pscustomobject]@{ safety='SAFE_READ'; authority='AUTO_SAFE'; reason='READ_ONLY_CMDLET_METADATA'; supports_should_process=$supportsShouldProcess; confirm_impact=$confirmImpact }
  }
  return [pscustomobject]@{ safety='HUMAN_GATED'; authority='HUMAN_APPLY'; reason="VERB_NOT_READ_SAFE:$verb"; supports_should_process=$supportsShouldProcess; confirm_impact=$confirmImpact }
}

function Get-VxsDescriptor([System.Management.Automation.CommandInfo]$Info) {
  $resolved = $Info
  if ($resolved -is [System.Management.Automation.AliasInfo]) {
    $resolved = Resolve-VxsCommandInfo $resolved.Name
  }
  $safety = Get-VxsCommandSafety $resolved
  $metadata = $null
  try { $metadata = [System.Management.Automation.CommandMetadata]::new($resolved) } catch {}
  $parameterNames = @()
  $parameterSets = @()
  if ($null -ne $metadata) {
    $parameterNames = @($metadata.Parameters.Keys | Sort-Object)
    $parameterSets = @($resolved.ParameterSets | ForEach-Object {
      [pscustomobject]@{
        name = $_.Name
        is_default = $_.IsDefault
        parameters = @($_.Parameters | ForEach-Object { $_.Name })
      }
    })
  }
  [pscustomobject]@{
    name = $Info.Name
    resolved_name = $resolved.Name
    command_type = [string]$Info.CommandType
    resolved_command_type = [string]$resolved.CommandType
    module = $resolved.ModuleName
    source = $resolved.Source
    version = if ($resolved.Version) { $resolved.Version.ToString() } else { $null }
    visibility = [string]$resolved.Visibility
    output_type = @($resolved.OutputType | ForEach-Object { $_.Type.Name })
    parameters = $parameterNames
    parameter_sets = $parameterSets
    safety = $safety
  }
}

function Get-VxsScriptAnalysis([string]$Script) {
  $tokens = $null
  $errors = $null
  $ast = [System.Management.Automation.Language.Parser]::ParseInput($Script, [ref]$tokens, [ref]$errors)
  $reasons = [System.Collections.Generic.List[string]]::new()
  $descriptors = [System.Collections.Generic.List[object]]::new()

  if (@($errors).Count -gt 0) {
    foreach ($err in @($errors)) { $reasons.Add("PARSE_ERROR:$($err.Message)") }
  }

  $redirections = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.RedirectionAst] }, $true))
  if ($redirections.Count -gt 0) { $reasons.Add('REDIRECTION_PRESENT') }

  $assignments = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] }, $true))
  if ($assignments.Count -gt 0) { $reasons.Add('ASSIGNMENT_PRESENT') }

  $memberInvocations = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.InvokeMemberExpressionAst] }, $true))
  if ($memberInvocations.Count -gt 0) { $reasons.Add('MEMBER_INVOCATION_PRESENT') }

  $commands = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] }, $true))
  foreach ($commandAst in $commands) {
    $name = $commandAst.GetCommandName()
    if ([string]::IsNullOrWhiteSpace($name)) {
      $reasons.Add('DYNAMIC_COMMAND_PRESENT')
      continue
    }
    try {
      $info = Get-Command -Name $name -ErrorAction Stop | Select-Object -First 1
      $descriptor = Get-VxsDescriptor $info
      $descriptors.Add($descriptor)
      if ($descriptor.safety.safety -ne 'SAFE_READ') {
        $reasons.Add("COMMAND_REQUIRES_HUMAN:$($name):$($descriptor.safety.reason)")
      }
    } catch {
      $reasons.Add("UNKNOWN_COMMAND:$name")
    }
  }

  $uniqueReasons = @($reasons | Select-Object -Unique)
  $safe = $uniqueReasons.Count -eq 0
  [pscustomobject]@{
    schema = 'vxs-powershell-analysis/1'
    script_sha256 = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($Script))).ToLowerInvariant()
    parse_errors = @($errors | ForEach-Object { $_.Message })
    command_count = $commands.Count
    commands = @($descriptors)
    blocked_constructs = $uniqueReasons
    safety_class = if ($safe) { 'SAFE_READ' } else { 'HUMAN_GATED' }
    authority = if ($safe) { 'AUTO_SAFE' } else { 'HUMAN_APPLY' }
    executable = $safe
  }
}

$payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__VXS_PAYLOAD__')) | ConvertFrom-Json
if ($payload.schema -ne 'vxs-powershell-engine/1') { throw 'VXS PowerShell engine payload schema mismatch.' }

switch ([string]$payload.action) {
  'engine' {
    Write-VxsJson ([pscustomobject]@{
      schema = 'vxs-powershell-engine/1'
      provider = 'System.Management.Automation'
      powershell_version = $PSVersionTable.PSVersion.ToString()
      edition = [string]$PSVersionTable.PSEdition
      clr = [System.Runtime.InteropServices.RuntimeInformation]::FrameworkDescription
      language_mode = [string]$ExecutionContext.SessionState.LanguageMode
      automation_assembly = [System.Management.Automation.PSObject].Assembly.Location
      automation_assembly_version = [System.Management.Automation.PSObject].Assembly.GetName().Version.ToString()
      process_path = [Environment]::ProcessPath
      runspace_id = if ([System.Management.Automation.Runspaces.Runspace]::DefaultRunspace) { [System.Management.Automation.Runspaces.Runspace]::DefaultRunspace.InstanceId.ToString() } else { $null }
    })
  }
  'commands' {
    $pattern = if ($payload.pattern) { [string]$payload.pattern } else { '*' }
    $items = @(Get-Command -Name $pattern -ErrorAction SilentlyContinue | Select-Object -First 500 | ForEach-Object { Get-VxsDescriptor $_ })
    Write-VxsJson ([pscustomobject]@{ schema='vxs-powershell-command-catalog/1'; pattern=$pattern; count=$items.Count; commands=$items })
  }
  'describe' {
    if (-not $payload.command) { throw 'PowerShell command name is required.' }
    $info = Get-Command -Name ([string]$payload.command) -ErrorAction Stop | Select-Object -First 1
    Write-VxsJson ([pscustomobject]@{ schema='vxs-powershell-command-descriptor/1'; command=(Get-VxsDescriptor $info) })
  }
  'providers' {
    $providers = @(Get-PSProvider | ForEach-Object {
      $providerName = $_.Name
      [pscustomobject]@{
        name = $providerName
        module = $_.ModuleName
        capabilities = [string]$_.Capabilities
        home = $_.Home
        drives = @(Get-PSDrive -PSProvider $providerName -ErrorAction SilentlyContinue | ForEach-Object {
          [pscustomobject]@{ name=$_.Name; root=$_.Root; current_location=$_.CurrentLocation; description=$_.Description }
        })
      }
    })
    Write-VxsJson ([pscustomobject]@{ schema='vxs-powershell-provider-catalog/1'; count=$providers.Count; providers=$providers })
  }
  'modules' {
    $pattern = if ($payload.pattern) { [string]$payload.pattern } else { '*' }
    $modules = @(Get-Module -ListAvailable -Name $pattern | Sort-Object Name,Version -Unique | Select-Object -First 500 | ForEach-Object {
      [pscustomobject]@{ name=$_.Name; version=$_.Version.ToString(); module_base=$_.ModuleBase; path=$_.Path; exported_commands=@($_.ExportedCommands.Keys | Sort-Object) }
    })
    Write-VxsJson ([pscustomobject]@{ schema='vxs-powershell-module-catalog/1'; pattern=$pattern; count=$modules.Count; modules=$modules })
  }
  'plan' {
    if (-not $payload.script) { throw 'PowerShell script is required.' }
    Write-VxsJson (Get-VxsScriptAnalysis ([string]$payload.script))
  }
  'invoke' {
    if (-not $payload.script) { throw 'PowerShell script is required.' }
    $analysis = Get-VxsScriptAnalysis ([string]$payload.script)
    if (-not $analysis.executable) {
      Write-VxsJson ([pscustomobject]@{ schema='vxs-powershell-execution/1'; status='BLOCKED_HUMAN_APPLY'; executed=$false; analysis=$analysis })
      break
    }
    $output = & ([scriptblock]::Create([string]$payload.script)) | Out-String -Width 4096
    Write-VxsJson ([pscustomobject]@{ schema='vxs-powershell-execution/1'; status='EXECUTED_SAFE_READ'; executed=$true; analysis=$analysis; output=$output })
  }
  default { throw "Unsupported VXS PowerShell engine action: $($payload.action)" }
}
`;
function buildVxsPowerShellEnginePlan(request2) {
  const payload = encodeRequest(request2);
  const body = ENGINE_CORE.replace("__VXS_PAYLOAD__", payload);
  return {
    executionCommand: `& {${body}}`,
    capability: `POWERSHELL_ENGINE_${request2.action.toUpperCase()}`,
    routeSummary: `VXS PowerShell Engine Provider: ${request2.action} via System.Management.Automation metadata/AST`
  };
}

// src/main/shell/vxs/vxs-powershell-capabilities.ts
function line18(value = "") {
  return `${value}
`;
}
function immediateError15(message, hints = []) {
  return {
    kind: "immediate",
    output: [
      `ERROR: ${message}`,
      ...hints,
      ""
    ].map(line18).join(""),
    exitCode: 2,
    stream: "stderr"
  };
}
function helpResult() {
  return {
    kind: "immediate",
    output: [
      "VXS POWERSHELL ENGINE PROVIDER",
      "",
      "PowerShell is treated as a structured engine provider, not only as a text shell.",
      "",
      "Commands:",
      "  vxs ps engine",
      "  vxs ps commands [pattern]",
      "  vxs ps describe <command>",
      "  vxs ps providers",
      "  vxs ps modules [pattern]",
      "  vxs ps plan <PowerShell script>",
      "  vxs ps invoke <PowerShell script>",
      "",
      "Safety:",
      "  plan never executes the script.",
      "  invoke executes only SAFE_READ scripts.",
      "  mutation/dynamic/untrusted constructs are recognized and BLOCKED_HUMAN_APPLY.",
      "  Human Gate remains the authority boundary.",
      ""
    ].map(line18).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function engineExecution(request2, context) {
  const plan = buildVxsPowerShellEnginePlan(request2);
  return {
    kind: "execute",
    executionCommand: plan.executionCommand,
    executionCwd: context.cwd,
    capability: plan.capability,
    routeSummary: plan.routeSummary
  };
}
function psCommand(args, context) {
  const actionToken = (args[0] ?? "help").toLowerCase();
  if (actionToken === "help" || actionToken === "--help" || actionToken === "-h") {
    return helpResult();
  }
  const simpleActions = {
    engine: "engine",
    commands: "commands",
    discover: "commands",
    describe: "describe",
    providers: "providers",
    modules: "modules",
    plan: "plan",
    invoke: "invoke"
  };
  const action = simpleActions[actionToken];
  if (!action) {
    return immediateError15(
      `Unknown PowerShell engine action '${actionToken}'.`,
      ["Run: vxs ps help"]
    );
  }
  if (action === "engine" || action === "providers") {
    return engineExecution({ action }, context);
  }
  if (action === "commands" || action === "modules") {
    const pattern = args.slice(1).join(" ").trim() || void 0;
    return engineExecution({ action, pattern }, context);
  }
  if (action === "describe") {
    const command = args.slice(1).join(" ").trim();
    if (!command) {
      return immediateError15("PowerShell command name is required.", [
        "Example: vxs ps describe Get-Process"
      ]);
    }
    return engineExecution({ action, command }, context);
  }
  const script = args.slice(1).join(" ").trim();
  if (!script) {
    return immediateError15("PowerShell script is required.", [
      `Example: vxs ps ${action} Get-Process | Select-Object -First 5`
    ]);
  }
  return engineExecution({ action, script }, context);
}
function createVxsPowerShellCommands() {
  return [
    {
      name: "powershell",
      aliases: ["ps", "pwsh"],
      usage: "vxs ps <engine|commands|describe|providers|modules|plan|invoke> [...]",
      summary: "Use PowerShell as a structured VXS engine provider with AST/metadata safety analysis",
      execute: psCommand
    }
  ];
}

// src/main/shell/vxs/vxs-command-registry.ts
function line19(value = "") {
  return `${value}
`;
}
function executableName(base) {
  if (process.platform !== "win32") return base;
  if (base === "npm") return "npm.cmd";
  if (base === "pnpm") return "pnpm.cmd";
  if (base === "yarn") return "yarn.cmd";
  return base.endsWith(".exe") || base.endsWith(".cmd") ? base : `${base}.exe`;
}
function commandAvailable2(base) {
  const program = process.platform === "win32" ? "where.exe" : "which";
  const name = executableName(base);
  try {
    const result = (0, import_node_child_process8.spawnSync)(
      program,
      [name],
      {
        windowsHide: true,
        shell: false,
        stdio: "ignore",
        timeout: 2e3
      }
    );
    return result.status === 0;
  } catch {
    return false;
  }
}
function workspaceLabel(workspace) {
  const pieces = [];
  if (workspace.packageName) {
    pieces.push(
      workspace.packageVersion ? `${workspace.packageName}@${workspace.packageVersion}` : workspace.packageName
    );
  }
  if (workspace.frameworks.length > 0) {
    pieces.push(workspace.frameworks.join(" + "));
  }
  if (pieces.length === 0) {
    pieces.push(
      workspace.kind === "directory" ? "Generic directory" : workspace.kind.toUpperCase()
    );
  }
  return pieces.join(" \xB7 ");
}
function helpCommand(_args, context) {
  const rows = [
    "VXS COMMAND REGISTRY",
    `${context.canonicalName} ${context.version}`,
    "",
    "Core commands:",
    "  vxs --version          Show VXS identity",
    "  vxs --help             Show this command registry",
    "  vxs help               Alias for --help",
    "  vxs status             Inspect current workspace",
    "  vxs doctor             Diagnose current development environment",
    "",
    "Development commands:",
    "  vxs workspace          Show detected workspace details",
    "  vxs scripts            List detected package scripts",
    "  vxs check              Auto-route non-mutating code checks",
    "  vxs format --check     Auto-route formatting verification",
    "  vxs build              Auto-route workspace build",
    "  vxs test               Auto-route workspace tests",
    "  vxs lint               Auto-route workspace lint",
    "  vxs run <script>       Run a detected package script",
    "  vxs git help           Show Git observe + AUTO-gated mutation commands",
    "",
    "Inspection commands:",
    "  vxs env                Safe environment summary",
    "  vxs which <tool>       Resolve a tool path",
    "  vxs tree [1-4]         Bounded workspace tree",
    "  vxs deps               Inspect local package dependencies",
    "",
    "Observability commands:",
    "  vxs logs [scope] [n]   Tail bounded Portal/Workstation logs",
    "  vxs trace <job-id>     Find local traces for a Workstation Job",
    "",
    "Source inspection commands:",
    "  vxs find <text> [path] Search workspace source text",
    "  vxs inspect <path>     Read bounded source line ranges",
    "  vxs hash <path>        Compute SHA256 for a workspace file",
    "  vxs stat <path>        Show workspace path metadata",
    "",
    "Change intelligence commands:",
    "  vxs changed            Show changed/untracked files",
    "  vxs diffstat           Show staged/worktree diff statistics",
    "  vxs refs <symbol>      Find bounded source references",
    "  vxs todo [path]        Find TODO/FIXME/HACK/XXX markers",
    "",
    "Dependency intelligence commands:",
    "  vxs imports <path>     List detected imports",
    "  vxs dependents <path>  Find bounded direct dependents",
    "  vxs impact <path>      Summarize static change impact",
    "",
    "Runtime diagnostics commands:",
    "  vxs runtime            Inspect local VXS/Portal/Workstation runtime",
    "  vxs port <number>      Inspect TCP ownership for a port",
    "  vxs process <name|pid> Inspect Windows process rows",
    "  vxs versions           Show runtime/tool versions",
    "",
    "Orchestration commands:",
    "  vxs preflight          Summarize readiness without execution",
    "  vxs verify quick       Run fail-fast checks/tests",
    "  vxs verify full        Run checks/tests plus build validation",
    "  vxs verify changed     Verify only ecosystems touched by Git changes",
    "  vxs verify-plan [mode] Preview quick/full/changed verification plan",
    "",
    "Failure intelligence commands:",
    "  vxs triage <job-id>    Classify Portal/Workstation job failure state",
    "",
    "Job intelligence commands:",
    "  vxs jobs [n]           List recent durable Workstation jobs",
    "  vxs failures [n]       List recent failed/rejected jobs",
    "  vxs timeline <job-id>  Show durable Job lifecycle timestamps",
    "",
    "Agent context commands:",
    "  vxs context            Create a safe bounded development snapshot",
    "  vxs context --json     Emit machine-readable agent context",
    "",
    "Agent decision commands:",
    "  vxs readiness          Assess current development readiness",
    "  vxs readiness --json   Emit machine-readable readiness",
    "  vxs recommend          Recommend next VXS commands",
    "  vxs recommend --json   Emit machine-readable recommendations",
    "",
    "Agent handoff commands:",
    "  vxs handoff            Bundle context/readiness/recommendations",
    "  vxs handoff --json     Emit machine-readable agent handoff packet",
    "",
    "Capability discovery commands:",
    "  vxs capabilities       List VXS capabilities and safety classes",
    "  vxs capabilities --json Emit machine-readable capability catalog",
    "  vxs describe <command> Describe one VXS command",
    "  vxs describe <command> --json Emit machine-readable capability detail",
    "",
    "Autonomous preparation foundation:",
    "  vxs selftest           Validate VXS registry/authority contracts",
    "  vxs selftest --json    Emit machine-readable self-test result",
    "  vxs policy             Show autonomous preparation policy",
    "  vxs policy --json      Emit machine-readable autonomy policy",
    "",
    "Autonomous development preparation:",
    "  vxs prepare            Self-test, plan, safe-verify, then emit approval point",
    "  vxs prepare --plan     Preview autonomous preparation without execution",
    "  vxs prepare --json     Emit machine-readable preparation plan",
    "",
    "PowerShell engine provider:",
    "  vxs ps engine          Inspect the embedded PowerShell engine/runtime",
    "  vxs ps commands [pat]  Discover PowerShell commands through engine metadata",
    "  vxs ps describe <cmd>  Describe CommandMetadata/parameters/safety signals",
    "  vxs ps providers       Inspect PowerShell Providers and PSDrives",
    "  vxs ps modules [pat]   Inspect available PowerShell modules",
    "  vxs ps plan <script>   Parse AST and classify a PowerShell script without execution",
    "  vxs ps invoke <script> Execute only when engine analysis classifies SAFE_READ",
    "",
    "Vertex commands:",
    "  vxs ray [pattern]      Read-only workspace Ray",
    "  vxs vra ...            Alias to existing Native VRA commands",
    "  vxs workstation ...    Read Workstation control-plane state",
    "  vxs evidence <job-id>  Read Workstation Evidence",
    "",
    "Compatibility:",
    `  Non-VXS commands continue to ${context.compatibilityBackend}.`,
    "",
    "Foundation:",
    "  Command Registry       READY",
    "  Workspace Detector     READY",
    "  Capability adapters    EXTENSIBLE",
    ""
  ];
  return {
    kind: "immediate",
    output: rows.map(line19).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function statusCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const rows = [
    "VXS STATUS",
    `Version: ${context.version}`,
    `CWD: ${workspace.cwd}`,
    `Workspace Root: ${workspace.root}`,
    `Workspace Type: ${workspace.kind}`,
    `Workspace: ${workspaceLabel(workspace)}`,
    `Package Manager: ${workspace.packageManager ?? "not detected"}`,
    `Frameworks: ${workspace.frameworks.length > 0 ? workspace.frameworks.join(", ") : "not detected"}`,
    `Git: ${workspace.git ? "detected" : "not detected"}`,
    `Markers: ${workspace.markers.length > 0 ? workspace.markers.join(", ") : "none"}`,
    `Scripts: ${workspace.scripts.length > 0 ? workspace.scripts.join(", ") : "none detected"}`,
    `Backend: ${context.compatibilityBackend} (compatibility)`,
    "Command Registry: READY",
    "Workspace Detector: READY",
    ""
  ];
  return {
    kind: "immediate",
    output: rows.map(line19).join(""),
    exitCode: 0,
    stream: "system"
  };
}
function doctorCommand(_args, context) {
  const workspace = detectVxsWorkspace(context.cwd);
  const checks = [];
  checks.push({
    level: fs13.existsSync(workspace.cwd) ? "PASS" : "FAIL",
    name: "CWD",
    detail: workspace.cwd
  });
  checks.push({
    level: "PASS",
    name: "Node runtime",
    detail: process.versions.node
  });
  checks.push({
    level: commandAvailable2("pwsh") ? "PASS" : "FAIL",
    name: "PowerShell",
    detail: commandAvailable2("pwsh") ? "pwsh.exe available" : "pwsh.exe not found"
  });
  checks.push({
    level: commandAvailable2("git") ? "PASS" : "WARN",
    name: "Git",
    detail: commandAvailable2("git") ? "git available" : "git not found"
  });
  if (workspace.packageManager) {
    const available = commandAvailable2(workspace.packageManager);
    checks.push({
      level: available ? "PASS" : "FAIL",
      name: `Package manager (${workspace.packageManager})`,
      detail: available ? `${workspace.packageManager} available` : `${workspace.packageManager} not found`
    });
  }
  if (workspace.kind === "rust" || workspace.kind === "mixed") {
    const available = commandAvailable2("cargo");
    checks.push({
      level: available ? "PASS" : "FAIL",
      name: "Rust / Cargo",
      detail: available ? "cargo available" : "cargo not found"
    });
  }
  if (workspace.kind === "python" || workspace.kind === "mixed") {
    const pythonAvailable = commandAvailable2("python") || commandAvailable2("py");
    checks.push({
      level: pythonAvailable ? "PASS" : "FAIL",
      name: "Python",
      detail: pythonAvailable ? "Python launcher available" : "python / py not found"
    });
  }
  if (workspace.kind === "directory") {
    checks.push({
      level: "WARN",
      name: "Workspace markers",
      detail: "No package.json / Cargo.toml / Python marker detected"
    });
  } else {
    checks.push({
      level: "PASS",
      name: "Workspace detection",
      detail: workspaceLabel(workspace)
    });
  }
  const pass = checks.filter((check) => check.level === "PASS").length;
  const warn = checks.filter((check) => check.level === "WARN").length;
  const fail = checks.filter((check) => check.level === "FAIL").length;
  const rows = [
    "VXS DOCTOR",
    `Workspace Root: ${workspace.root}`,
    "",
    ...checks.map(
      (check) => `[${check.level}] ${check.name}: ${check.detail}`
    ),
    "",
    `Summary: PASS=${pass} WARN=${warn} FAIL=${fail}`,
    fail === 0 ? "VXS DOCTOR RESULT: PASS" : "VXS DOCTOR RESULT: FAILED",
    ""
  ];
  return {
    kind: "immediate",
    output: rows.map(line19).join(""),
    exitCode: fail === 0 ? 0 : 1,
    stream: "system"
  };
}
var COMMANDS = [
  {
    name: "help",
    aliases: ["--help", "-h"],
    usage: "vxs --help",
    summary: "Show VXS commands",
    execute: helpCommand
  },
  {
    name: "status",
    aliases: [],
    usage: "vxs status",
    summary: "Inspect the current workspace",
    execute: statusCommand
  },
  {
    name: "doctor",
    aliases: [],
    usage: "vxs doctor",
    summary: "Diagnose the development environment",
    execute: doctorCommand
  },
  ...createVxsDevelopmentCommands(),
  ...createVxsNativeCommands(),
  ...createVxsInspectionCommands(),
  ...createVxsObservabilityCommands(),
  ...createVxsSourceInspectionCommands(),
  ...createVxsChangeIntelligenceCommands(),
  ...createVxsDependencyIntelligenceCommands(),
  ...createVxsRuntimeDiagnosticsCommands(),
  ...createVxsOrchestrationCommands(),
  ...createVxsFailureIntelligenceCommands(),
  ...createVxsJobIntelligenceCommands(),
  ...createVxsAgentContextCommands(),
  ...createVxsAgentDecisionCommands(),
  ...createVxsAgentHandoffCommands(),
  ...createVxsPowerShellCommands(),
  ...createVxsVertexCommands(),
  ...createVxsCapabilityDiscoveryCommands(() => COMMANDS),
  ...createVxsAutonomyFoundationCommands(() => COMMANDS),
  ...createVxsAutonomousPreparationCommands(() => COMMANDS)
];
function resolveCommand(token) {
  const normalized = token.toLowerCase();
  return COMMANDS.find(
    (command) => command.name === normalized || command.aliases.includes(normalized)
  ) ?? null;
}
function executeVxsCommand(rawCommand, context) {
  const trimmed = rawCommand.trim();
  if (!/^vxs(?:\s|$)/i.test(trimmed)) return null;
  const body = trimmed.replace(/^vxs\b/i, "").trim();
  const tokens = body ? body.split(/\s+/) : ["help"];
  const commandToken = tokens[0] ?? "help";
  const args = tokens.slice(1);
  if (commandToken === "--version") {
    return null;
  }
  const command = resolveCommand(commandToken);
  if (!command) {
    return {
      kind: "immediate",
      output: [
        `ERROR: Unknown VXS command '${commandToken}'.`,
        "Run: vxs --help",
        ""
      ].map(line19).join(""),
      exitCode: 2,
      stream: "stderr"
    };
  }
  return command.execute(args, context);
}

// src/main/shell/vxs/vxs-native-organ-provider.ts
var import_child_process = require("child_process");
var import_crypto = require("crypto");
var import_fs = require("fs");
var import_path = require("path");
var DESCRIPTOR_RELATIVE_PATH = "runtime/vxs/native/providers/vxs-native-observer.json";
function sha256File(path17) {
  return (0, import_crypto.createHash)("sha256").update((0, import_fs.readFileSync)(path17)).digest("hex");
}
function normalizeResource(resource) {
  return resource.trim().toLowerCase();
}
function normalizeAction(action) {
  return action.trim().toLowerCase();
}
function mapInvocation(request2) {
  const resource = request2.resource.trim().toUpperCase();
  const action = request2.action.trim().toUpperCase();
  if (resource === "SYSTEM" && action === "OBSERVE") {
    return ["system"];
  }
  if (resource === "FILESYSTEM") {
    if (!request2.target) return null;
    if (action === "TEST" || action === "EXISTS") {
      return ["fs-exists", request2.target];
    }
    if (action === "OBSERVE" || action === "METADATA") {
      return ["fs-meta", request2.target];
    }
    if (action === "FIND" || action === "LIST") {
      return ["fs-list", request2.target];
    }
  }
  return null;
}
var VxsNativeOrganProvider = class {
  constructor(projectRoot) {
    this.projectRoot = projectRoot;
  }
  descriptorPath() {
    return (0, import_path.join)(this.projectRoot, DESCRIPTOR_RELATIVE_PATH);
  }
  probe(request2) {
    const descriptorPath = this.descriptorPath();
    if (!(0, import_fs.existsSync)(descriptorPath)) {
      return { available: false, reason: "DESCRIPTOR_MISSING" };
    }
    let descriptor;
    try {
      descriptor = JSON.parse(
        (0, import_fs.readFileSync)(descriptorPath, "utf8")
      );
    } catch {
      return { available: false, reason: "DESCRIPTOR_INVALID" };
    }
    if (descriptor.schema !== "vertex-vxs/native-provider-binding-1" || descriptor.provider_id !== "vxs-native-observer") {
      return { available: false, reason: "DESCRIPTOR_INVALID" };
    }
    if (!descriptor.authority.allowed.includes(request2.authority)) {
      return {
        available: false,
        reason: "AUTHORITY_NOT_ALLOWED",
        descriptor
      };
    }
    const resourceKey = normalizeResource(request2.resource);
    const actionKey = normalizeAction(request2.action);
    const declared = descriptor.capabilities[resourceKey] ?? [];
    const invocation = mapInvocation(request2);
    const declaredAlias = resourceKey === "system" && actionKey === "observe" ? "observe" : resourceKey === "filesystem" && (actionKey === "test" || actionKey === "exists") ? "exists" : resourceKey === "filesystem" && (actionKey === "observe" || actionKey === "metadata") ? "metadata" : resourceKey === "filesystem" && (actionKey === "find" || actionKey === "list") ? "list" : "";
    if (!invocation || !declaredAlias || !declared.includes(declaredAlias)) {
      return {
        available: false,
        reason: "CAPABILITY_UNSUPPORTED",
        descriptor
      };
    }
    const descriptorBinary = descriptor.binary.path;
    const binaryPath = (0, import_path.isAbsolute)(descriptorBinary) ? descriptorBinary : (0, import_path.join)(this.projectRoot, descriptorBinary);
    if (!(0, import_fs.existsSync)(binaryPath)) {
      return {
        available: false,
        reason: "BINARY_MISSING",
        descriptor,
        binaryPath
      };
    }
    const actualSha256 = sha256File(binaryPath);
    if (actualSha256 !== descriptor.binary.sha256.toLowerCase()) {
      return {
        available: false,
        reason: "BINARY_HASH_MISMATCH",
        descriptor,
        binaryPath
      };
    }
    return {
      available: true,
      reason: "AVAILABLE",
      descriptor,
      binaryPath
    };
  }
  plan(request2) {
    const probe = this.probe(request2);
    if (!probe.available || !probe.binaryPath || !probe.descriptor) {
      return null;
    }
    const args = mapInvocation(request2);
    if (!args) {
      return null;
    }
    return {
      providerId: probe.descriptor.provider_id,
      program: probe.binaryPath,
      args
    };
  }
  execute(request2) {
    const probe = this.probe(request2);
    if (!probe.available || !probe.binaryPath || !probe.descriptor) {
      return Promise.reject(
        new Error(`Native provider unavailable: ${probe.reason}`)
      );
    }
    const args = mapInvocation(request2);
    if (!args) {
      return Promise.reject(
        new Error("Native capability invocation is unsupported")
      );
    }
    return new Promise((resolve10, reject) => {
      const child = (0, import_child_process.spawn)(probe.binaryPath, args, {
        cwd: this.projectRoot,
        shell: false,
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"]
      });
      let stdout = "";
      let stderr = "";
      child.stdout.setEncoding("utf8");
      child.stderr.setEncoding("utf8");
      child.stdout.on("data", (chunk) => {
        stdout += chunk;
      });
      child.stderr.on("data", (chunk) => {
        stderr += chunk;
      });
      child.on("error", reject);
      child.on("close", (code) => {
        const exitCode = code ?? -1;
        let payload;
        if (stdout.trim()) {
          try {
            const lines = stdout.trim().split(/\r?\n/);
            payload = JSON.parse(lines[lines.length - 1]);
          } catch {
            payload = void 0;
          }
        }
        resolve10({
          provider: "native",
          providerId: probe.descriptor?.provider_id ?? "unknown",
          ok: exitCode === 0,
          exitCode,
          stdout,
          stderr,
          payload
        });
      });
    });
  }
};

// src/main/shell/vxs/vxs-provider-resolver.ts
function planVxsProviderExecution(projectRoot, request2, powerShellProgram, powerShellCommand) {
  if (request2.authority !== "AUTO_SAFE") {
    throw new Error("HUMAN_APPLY_REQUIRED");
  }
  const nativeProvider = new VxsNativeOrganProvider(projectRoot);
  const nativePlan = nativeProvider.plan(request2);
  if (nativePlan) {
    return {
      route: "NATIVE",
      program: nativePlan.program,
      args: nativePlan.args,
      providerId: nativePlan.providerId,
      reason: "NATIVE_PROVIDER_AVAILABLE"
    };
  }
  return {
    route: "POWERSHELL",
    program: powerShellProgram,
    args: ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", powerShellCommand],
    providerId: "powershell",
    reason: "NATIVE_PROVIDER_UNAVAILABLE"
  };
}

// src/main/shell/vertex-shell-service.ts
var fs14 = __toESM(require("node:fs"), 1);
var path15 = __toESM(require("node:path"), 1);
var GENERATION = "000080V4A";
var VXS_VERSION = "0.1.0";
var VXS_CANONICAL_NAME = "Vertex eXecution Shell";
var DEFAULT_CWD = "G:\\Vertex_Project\\Development";
var MAX_COMMAND_CHARS = 32e3;
var MAX_STREAM_BYTES = 2 * 1024 * 1024;
function nowIso() {
  return (/* @__PURE__ */ new Date()).toISOString();
}
function redactCommand(command) {
  return command.replace(/(api[_-]?key|token|password|passwd|secret)\s*=\s*("[^"]*"|'[^']*'|\S+)/gi, "$1=[REDACTED]").replace(/(authorization\s*:\s*bearer)\s+\S+/gi, "$1 [REDACTED]").replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, "[REDACTED]");
}
function safeExistingDirectory(candidate) {
  const resolved = path15.resolve(candidate);
  const stat = fs14.statSync(resolved);
  if (!stat.isDirectory()) {
    throw new Error(`Not a directory: ${resolved}`);
  }
  return resolved;
}
function resolveBackend() {
  return "pwsh.exe";
}
var VertexShellService = class {
  syncVxsBranding() {
    const script = String.raw`(() => {
      const ROOT_ID = 'vertex-shell-internal-unit'
      const SETTINGS_KEY = 'vxs:editor-settings:v1'
      const root = document.getElementById(ROOT_ID)
      if (!root || !root.shadowRoot) return 'vxs-host-not-ready'

      const shadow = root.shadowRoot

      if (root.__VXS_RUNTIME__?.refresh) {
        root.__VXS_RUNTIME__.refresh()
        return 'vxs-runtime-refreshed'
      }

      const closedTabs = new Set()
      let settingsOpenPinned = false
      let closeTimer = 0
      let styling = false
      let refreshQueued = false
      let lastStyledText = ''
      let lastStyledMode = ''

      const q = selector => shadow.querySelector(selector)
      const qa = selector => Array.from(shadow.querySelectorAll(selector))

      const output = () => q('.output')
      const shellPanel = () => q('.vsh')

      const installNativeVraAlias = () => {
        if (root.__VXS_NATIVE_VRA_ALIAS__) return

        const rewrite = () => {
          const input = q('.command')
          if (!input) return
          const current = String(input.value || '').trim()
          if (!/^vxs\s+vra(?:\s|$)/i.test(current)) return
          input.value = current.replace(/^vxs\s+/i, '')
          input.dispatchEvent(new Event('input', { bubbles: true }))
        }

        shadow.addEventListener(
          'keydown',
          event => {
            if (event.isComposing || event.key !== 'Enter') return
            rewrite()
          },
          true
        )

        shadow.addEventListener(
          'click',
          event => {
            const target = event.target
            if (!(target instanceof Element)) return
            if (!target.closest('.run')) return
            rewrite()
          },
          true
        )

        root.__VXS_NATIVE_VRA_ALIAS__ = true
      }

      const normalizeVxsBrandText = value =>
        String(value ?? '')
          .replaceAll('VSH │', 'VXS │')
          .replaceAll('VSH ›', 'VXS ›')
          .replaceAll(
            'VERTEX SHELL 000080V4G · SHELL',
            'VXS 0.1.0 · SHELL'
          )


      const installCanonicalClipboardCopy = () => {
        if (root.__VXS_CANONICAL_CLIPBOARD_COPY__) return

        shadow.addEventListener(
          'click',
          event => {
            const target = event.target
            if (!(target instanceof Element)) return

            const button = target.closest('button')
            if (!button) return

            const label = String(button.textContent || '')
              .trim()
              .toUpperCase()

            // Scope strictly to the VXS transcript COPY button.
            // Explorer COPY PATH lives outside this shell shadow root.
            if (label !== 'COPY') return

            const node = output()
            if (!node) return

            const clipboard = navigator.clipboard
            if (!clipboard?.writeText) return

            const canonicalTranscript = normalizeVxsBrandText(
              node.textContent || ''
            )

            // VXS owns transcript COPY.
            //
            // The legacy Host COPY handler reads the internal transcript,
            // whose historical prefix can still be VSH even though the
            // presentation layer is already canonicalized to VXS.
            //
            // Intercept during capture before the button's legacy handler
            // runs, then stop the legacy path so two asynchronous clipboard
            // writes cannot race and re-introduce VSH.
            event.preventDefault()
            event.stopImmediatePropagation()

            void clipboard
              .writeText(canonicalTranscript)
              .catch(() => undefined)
          },
          true
        )

        root.__VXS_CANONICAL_CLIPBOARD_COPY__ = true
      }

      const installSynchronousOutputBranding = () => {
        const node = output()
        if (!node || node.__VXS_TEXT_CONTENT_PATCHED__) return

        const descriptor = Object.getOwnPropertyDescriptor(
          Node.prototype,
          'textContent'
        )

        if (!descriptor?.get || !descriptor?.set) return

        Object.defineProperty(node, 'textContent', {
          configurable: true,
          enumerable: descriptor.enumerable ?? false,
          get() {
            return descriptor.get.call(this)
          },
          set(value) {
            descriptor.set.call(this, normalizeVxsBrandText(value))
          }
        })

        node.__VXS_TEXT_CONTENT_PATCHED__ = true
        node.textContent = normalizeVxsBrandText(node.textContent)
      }

      const addRuntimeStyle = () => {
        if (q('#vxs-runtime-style')) return
        const style = document.createElement('style')
        style.id = 'vxs-runtime-style'
        style.textContent = [
          '.vsh{--vxs-editor-font-size:11px}',
          '.vxsSettingsButton{width:29px!important;padding:0!important;font-size:15px!important;color:#3AB8FF!important;border-color:#26394B!important}',
          '.vxsSettingsButton:hover,.vxsSettingsButton.open{border-color:#168CFF!important;background:#102C44!important;box-shadow:0 0 15px rgba(22,140,255,.18)!important}',
          '.vxsSettingsPopover{position:absolute;top:38px;right:8px;width:min(320px,calc(100% - 16px));z-index:80;padding:12px;background:rgba(12,18,26,.985);border:1px solid #168CFF;border-radius:8px;box-shadow:0 18px 46px rgba(0,0,0,.52),0 0 18px rgba(22,140,255,.12);font-family:system-ui,sans-serif;color:#CBD5DF;opacity:0;visibility:hidden;pointer-events:none;transform:translateY(-4px);transition:opacity .12s ease,transform .12s ease,visibility .12s ease}',
          '.vxsSettingsPopover.open{opacity:1;visibility:visible;pointer-events:auto;transform:translateY(0)}',
          '.vxsSettingsTitle{display:flex;align-items:center;justify-content:space-between;margin:0 0 10px;font-size:11px;font-weight:800;letter-spacing:.06em;color:#CBD5DF}',
          '.vxsSettingsSection{padding-top:10px;margin-top:10px;border-top:1px solid #26394B}',
          '.vxsSettingsSection:first-of-type{padding-top:0;margin-top:0;border-top:0}',
          '.vxsSettingsLabel{display:block;margin-bottom:8px;font-size:10px;font-weight:800;color:#CBD5DF}',
          '.vxsMode{display:grid;grid-template-columns:18px minmax(0,1fr);gap:7px;padding:8px;margin:0 0 7px;border:1px solid #1C2935;border-radius:7px;background:#0C121A;cursor:pointer}',
          '.vxsMode:has(input:checked){border-color:#168CFF;background:#102C44}',
          '.vxsMode input{margin:2px 0 0;accent-color:#168CFF}',
          '.vxsModeName{font-size:10px;font-weight:800;color:#CBD5DF}',
          '.vxsLegend{display:grid;gap:5px;margin-top:7px;font-size:9px;color:#718195}',
          '.vxsLegendRow{display:flex;align-items:center;gap:7px}',
          '.vxsDot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:none}',
          '.vxsFontRow{display:grid;grid-template-columns:16px minmax(0,1fr) 44px;gap:8px;align-items:center}',
          '.vxsFontRow input[type=range]{width:100%;accent-color:#168CFF}',
          '.vxsFontValue{text-align:right;font:800 9px "Cascadia Mono",Consolas,monospace;color:#CBD5DF}',
          '.output,.cwd,.command,.prompt{font-size:var(--vxs-editor-font-size)!important}',
          '.vxsLine{color:#CBD5DF}',
          '[data-vxs-editor-mode="default"] .vxsLine.info{color:#CBD5DF}',
          '[data-vxs-editor-mode="default"] .vxsLine.success{color:#55D69E}',
          '[data-vxs-editor-mode="default"] .vxsLine.warning{color:#F1B85B}',
          '[data-vxs-editor-mode="default"] .vxsLine.error{color:#FF6F7C}',
          '[data-vxs-editor-mode="old"] .vxsLine{color:#55D69E}',
          '[data-vxs-editor-mode="old"] .vxsLine.error{color:#FF6F7C}',
          '.tab{position:relative!important;padding-right:27px!important}',
          '.vxsTabClose{position:absolute;right:5px;top:50%;transform:translateY(-50%);display:grid;place-items:center;width:15px;height:15px;border-radius:4px;color:#718195;font:800 12px/1 system-ui,sans-serif;cursor:pointer;opacity:.72}',
          '.tab:hover .vxsTabClose,.tab.active .vxsTabClose{opacity:1}',
          '.vxsTabClose:hover{color:#FF6F7C;background:rgba(255,111,124,.10)}',
          '.vxsTabClose.busy{opacity:.25!important;cursor:not-allowed}',
          '.vxsTabClosed{display:none!important}'
        ].join('')
        shadow.appendChild(style)
      }

      const readSettings = () => {
        let saved = null
        try { saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || 'null') } catch {}
        const currentOutput = output()
        const currentSize = currentOutput
          ? Math.round(parseFloat(getComputedStyle(currentOutput).fontSize) || 11)
          : 11
        const mode = saved?.mode === 'old' ? 'old' : 'default'
        const fontSize = Number.isFinite(Number(saved?.fontSize))
          ? Math.max(9, Math.min(20, Number(saved.fontSize)))
          : currentSize
        return { mode, fontSize }
      }

      let settings = readSettings()

      const saveSettings = () => {
        try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings)) } catch {}
      }

      const classifyLine = line => {
        const upper = String(line || '').toUpperCase()
        if (
          upper.startsWith('ERR │') ||
          /\b(ERROR|FAILED|FAILURE|REJECTED|ROLLED_BACK)\b/.test(upper) ||
          /\bEXIT\s+[1-9][0-9]*\b/.test(upper) ||
          /\bRESULT\s+EXIT=[1-9][0-9]*\b/.test(upper)
        ) return 'error'
        if (
          /\b(WARN|WARNING|CAUTION|ATTN|RUNNING|HOLD|TRUNCATED|STOPPED)\b/.test(upper)
        ) return 'warning'
        if (
          /\b(PASS|SUCCESS|SUCCEEDED|VERIFIED|READY)\b/.test(upper) ||
          /\bEXIT\s+0\b/.test(upper) ||
          /\bRESULT\s+EXIT=0\b/.test(upper)
        ) return 'success'
        return 'info'
      }

      const styleOutput = () => {
        if (styling) return
        const node = output()
        if (!node) return
        const raw = node.textContent || ''
        if (
          raw === lastStyledText &&
          settings.mode === lastStyledMode &&
          node.querySelector('.vxsLine')
        ) return

        styling = true
        const wasNearBottom =
          node.scrollHeight - node.scrollTop - node.clientHeight < 32
        const parts = raw.split('\n')
        const fragment = document.createDocumentFragment()

        parts.forEach((line, index) => {
          const span = document.createElement('span')
          span.className = 'vxsLine ' + classifyLine(line)
          span.textContent = line
          fragment.appendChild(span)
          if (index < parts.length - 1) {
            fragment.appendChild(document.createTextNode('\n'))
          }
        })

        node.replaceChildren(fragment)
        lastStyledText = raw
        lastStyledMode = settings.mode
        if (wasNearBottom) node.scrollTop = node.scrollHeight
        styling = false
      }

      const applySettings = () => {
        const panel = shellPanel()
        if (!panel) return
        panel.dataset.vxsEditorMode = settings.mode
        panel.style.setProperty(
          '--vxs-editor-font-size',
          Math.round(settings.fontSize) + 'px'
        )

        const modeDefault = q('#vxs-mode-default')
        const modeOld = q('#vxs-mode-old')
        const font = q('#vxs-font-size')
        const value = q('.vxsFontValue')

        if (modeDefault) modeDefault.checked = settings.mode === 'default'
        if (modeOld) modeOld.checked = settings.mode === 'old'
        if (font) font.value = String(Math.round(settings.fontSize))
        if (value) value.textContent = Math.round(settings.fontSize) + ' px'

        lastStyledMode = ''
        styleOutput()
      }

      const setPopoverOpen = open => {
        const popover = q('.vxsSettingsPopover')
        const gear = q('.vxsSettingsButton')
        if (!popover || !gear) return
        popover.classList.toggle('open', Boolean(open))
        gear.classList.toggle('open', Boolean(open))
      }

      const cancelClose = () => {
        if (closeTimer) window.clearTimeout(closeTimer)
        closeTimer = 0
      }

      const scheduleClose = () => {
        cancelClose()
        if (settingsOpenPinned) return
        closeTimer = window.setTimeout(() => setPopoverOpen(false), 160)
      }

      const ensureSettingsUi = () => {
        addRuntimeStyle()

        let gear = q('.vxsSettingsButton')
        const collapse = q('.collapse')

        if (!gear && collapse) {
          gear = collapse.cloneNode(true)
          gear.classList.add('vxsSettingsButton')
          gear.dataset.vxsSettingsButton = '1'
          gear.textContent = '⚙'
          gear.title = 'VXS Settings'
          gear.setAttribute('aria-label', 'VXS Settings')
          collapse.replaceWith(gear)

          gear.addEventListener('mouseenter', () => {
            cancelClose()
            setPopoverOpen(true)
          })
          gear.addEventListener('mouseleave', scheduleClose)
          gear.addEventListener('click', event => {
            event.preventDefault()
            event.stopPropagation()
            settingsOpenPinned = !settingsOpenPinned
            setPopoverOpen(settingsOpenPinned || !q('.vxsSettingsPopover')?.classList.contains('open'))
          })
        } else if (gear) {
          gear.textContent = '⚙'
          gear.title = 'VXS Settings'
        }

        let popover = q('.vxsSettingsPopover')
        if (!popover) {
          popover = document.createElement('section')
          popover.className = 'vxsSettingsPopover'
          popover.setAttribute('aria-label', 'VXS Settings')
          popover.innerHTML =
            '<div class="vxsSettingsTitle"><span>VXS SETTINGS</span><span>0.1.0</span></div>' +
            '<div class="vxsSettingsSection">' +
              '<span class="vxsSettingsLabel">Editor Display Mode</span>' +
              '<label class="vxsMode">' +
                '<input id="vxs-mode-default" type="radio" name="vxs-display-mode" value="default">' +
                '<span><span class="vxsModeName">Default Mode</span>' +
                  '<span class="vxsLegend">' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#CBD5DF"></i>White = Standard / Info</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#55D69E"></i>Green = Success / Ready</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#F1B85B"></i>Orange = Warning / Caution</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#FF6F7C"></i>Red = Error / Failed</span>' +
                  '</span>' +
                '</span>' +
              '</label>' +
              '<label class="vxsMode">' +
                '<input id="vxs-mode-old" type="radio" name="vxs-display-mode" value="old">' +
                '<span><span class="vxsModeName">OLD Mode</span>' +
                  '<span class="vxsLegend">' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#55D69E"></i>Green = Default text</span>' +
                    '<span class="vxsLegendRow"><i class="vxsDot" style="background:#FF6F7C"></i>Red = Error only</span>' +
                  '</span>' +
                '</span>' +
              '</label>' +
            '</div>' +
            '<div class="vxsSettingsSection">' +
              '<span class="vxsSettingsLabel">Font Size</span>' +
              '<div class="vxsFontRow"><span>A</span><input id="vxs-font-size" type="range" min="9" max="20" step="1"><span class="vxsFontValue"></span></div>' +
            '</div>'

          shellPanel()?.appendChild(popover)

          popover.addEventListener('mouseenter', cancelClose)
          popover.addEventListener('mouseleave', scheduleClose)

          q('#vxs-mode-default')?.addEventListener('change', event => {
            if (!event.target.checked) return
            settings = { ...settings, mode: 'default' }
            saveSettings()
            applySettings()
          })

          q('#vxs-mode-old')?.addEventListener('change', event => {
            if (!event.target.checked) return
            settings = { ...settings, mode: 'old' }
            saveSettings()
            applySettings()
          })

          q('#vxs-font-size')?.addEventListener('input', event => {
            settings = {
              ...settings,
              fontSize: Math.max(9, Math.min(20, Number(event.target.value) || 11))
            }
            saveSettings()
            applySettings()
          })
        }

        applySettings()
      }

      const tabLabel = tab =>
        String(tab?.title || '').split(' · ')[0].trim() ||
        String(tab?.firstChild?.textContent || '').trim()

      const visibleTabs = () =>
        qa('.tab').filter(tab => !closedTabs.has(tabLabel(tab)))

      const dismissTab = tab => {
        const label = tabLabel(tab)
        if (!label) return

        if (tab.classList.contains('busy')) {
          const close = tab.querySelector('.vxsTabClose')
          if (close) {
            close.classList.add('busy')
            close.title = 'Running shell cannot be closed'
          }
          return
        }

        const visible = visibleTabs()
        const active = tab.classList.contains('active')

        if (visible.length <= 1) {
          q('.tabAdd')?.click()
          closedTabs.add(label)
          queueRefresh()
          return
        }

        if (active) {
          const index = visible.indexOf(tab)
          const target = visible[index - 1] || visible[index + 1]
          target?.click()
        }

        closedTabs.add(label)
        queueRefresh()
      }

      const enhanceTabs = () => {
        for (const tab of qa('.tab')) {
          const label = tabLabel(tab)
          tab.classList.toggle('vxsTabClosed', closedTabs.has(label))
          if (closedTabs.has(label)) continue

          let close = tab.querySelector('.vxsTabClose')
          if (!close) {
            close = document.createElement('span')
            close.className = 'vxsTabClose'
            close.textContent = '×'
            close.setAttribute('role', 'button')
            close.setAttribute('aria-label', 'Close ' + label)
            close.title = 'Close ' + label
            close.addEventListener('pointerdown', event => {
              event.preventDefault()
              event.stopPropagation()
            })
            close.addEventListener('click', event => {
              event.preventDefault()
              event.stopPropagation()
              dismissTab(tab)
            })
            tab.appendChild(close)
          }

          const busy = tab.classList.contains('busy')
          close.classList.toggle('busy', busy)
          close.title = busy
            ? 'Running shell cannot be closed'
            : 'Close ' + label
        }
      }

      const applyBranding = () => {
        const brand = q('.title strong')
        if (brand) brand.textContent = 'Vertex eXecution Shell'

        const prompt = q('.prompt')
        if (prompt && prompt.textContent?.includes('VSH')) {
          prompt.textContent = prompt.textContent.replace('VSH', 'VXS')
        }

        const node = output()
        if (node) {
          const currentText = node.textContent || ''
          const nextText = normalizeVxsBrandText(currentText)

          if (nextText !== currentText) {
            node.textContent = nextText
            lastStyledText = ''
          }
        }

        qa('[title]').forEach(node => {
          const title = node.getAttribute('title')
          if (title?.includes('Vertex Shell')) {
            node.setAttribute('title', title.replaceAll('Vertex Shell', 'VXS'))
          }
        })
      }

      const refresh = () => {
        refreshQueued = false
        installSynchronousOutputBranding()
        installCanonicalClipboardCopy()
        installNativeVraAlias()
        applyBranding()
        ensureSettingsUi()
        enhanceTabs()
        styleOutput()
      }

      function queueRefresh() {
        if (refreshQueued) return
        refreshQueued = true
        window.requestAnimationFrame(refresh)
      }

      const observer = new MutationObserver(() => queueRefresh())
      observer.observe(shadow, {
        subtree: true,
        childList: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['class', 'title']
      })

      root.__VXS_RUNTIME__ = {
        refresh,
        settingsVersion: 1,
        closedTabs
      }

      refresh()
      return 'vxs-settings-tabs-runtime-installed'
    })()`;
    for (const window of import_electron3.BrowserWindow.getAllWindows()) {
      if (window.isDestroyed() || window.webContents.isDestroyed()) continue;
      window.setTitle("Vertex eXecution Shell");
      void window.webContents.executeJavaScript(script, true).catch(() => void 0);
    }
  }
  active = null;
  cwd = fs14.existsSync(DEFAULT_CWD) ? DEFAULT_CWD : process.cwd();
  historyPath() {
    const root = path15.join(import_electron3.app.getPath("userData"), "vertex-shell");
    fs14.mkdirSync(root, { recursive: true });
    return path15.join(root, "command-history.jsonl");
  }
  state() {
    this.syncVxsBranding();
    return {
      generation: GENERATION,
      backend: resolveBackend(),
      cwd: this.cwd,
      busy: this.active !== null,
      activePid: this.active?.child.pid ?? null,
      activeCommandId: this.active?.commandId ?? null,
      historyPath: this.historyPath()
    };
  }
  setCwd(request2) {
    if (this.active) {
      throw new Error("VERTEX_SHELL_BUSY");
    }
    if (!request2?.cwd?.trim()) {
      throw new Error("VERTEX_SHELL_CWD_REQUIRED");
    }
    this.cwd = safeExistingDirectory(request2.cwd.trim());
    return this.state();
  }
  async execute(request2, sink) {
    this.syncVxsBranding();
    if (this.active) {
      throw new Error("VERTEX_SHELL_BUSY");
    }
    const command = request2?.command?.trim() ?? "";
    if (!command) {
      throw new Error("VERTEX_SHELL_COMMAND_REQUIRED");
    }
    if (command.length > MAX_COMMAND_CHARS) {
      throw new Error("VERTEX_SHELL_COMMAND_TOO_LARGE");
    }
    const cwd = request2.cwd?.trim() ? safeExistingDirectory(request2.cwd.trim()) : this.cwd;
    this.cwd = cwd;
    if (/^(?:vxs\s+)?--version$/i.test(command)) {
      const commandId2 = (0, import_node_crypto4.randomUUID)();
      const versionText = [
        `VXS ${VXS_VERSION}`,
        VXS_CANONICAL_NAME,
        "Host: Vertex Session Portal",
        `Backend: ${resolveBackend()} (compatibility)`,
        ""
      ].join("\n");
      sink({
        commandId: commandId2,
        kind: "system",
        chunk: versionText,
        at: nowIso()
      });
      const result = {
        commandId: commandId2,
        command: redactCommand(command),
        cwd: this.cwd,
        backend: "VXS_META",
        pid: null,
        exitCode: 0,
        durationMs: 0,
        stdoutBytes: Buffer.byteLength(versionText, "utf8"),
        stderrBytes: 0,
        stopped: false
      };
      this.appendHistory(result);
      return result;
    }
    const vxsRegistryCommand = /^--help$/i.test(command) ? "vxs --help" : command;
    const vxsStartedAt = Date.now();
    const vxsDispatch = executeVxsCommand(
      vxsRegistryCommand,
      {
        cwd: this.cwd,
        version: VXS_VERSION,
        canonicalName: VXS_CANONICAL_NAME,
        compatibilityBackend: resolveBackend()
      }
    );
    if (vxsDispatch?.kind === "immediate") {
      const commandId2 = (0, import_node_crypto4.randomUUID)();
      const outputBytes = Buffer.byteLength(vxsDispatch.output, "utf8");
      sink({
        commandId: commandId2,
        kind: vxsDispatch.stream,
        chunk: vxsDispatch.output,
        at: nowIso()
      });
      const result = {
        commandId: commandId2,
        command: redactCommand(command),
        cwd: this.cwd,
        backend: "VXS_COMMAND",
        pid: null,
        exitCode: vxsDispatch.exitCode,
        durationMs: Date.now() - vxsStartedAt,
        stdoutBytes: vxsDispatch.stream === "system" ? outputBytes : 0,
        stderrBytes: vxsDispatch.stream === "stderr" ? outputBytes : 0,
        stopped: false
      };
      this.appendHistory(result);
      return result;
    }
    const routedExecution = vxsDispatch?.kind === "execute" ? vxsDispatch : null;
    const hasCommandSeparator = /[;\r\n|&]/.test(command);
    const cd = routedExecution || hasCommandSeparator ? null : command.match(/^(?:cd|set-location)\s+(.+)$/i);
    if (cd) {
      const raw = cd[1].trim().replace(/^(['"])(.*)\1$/, "$2");
      const candidate = path15.isAbsolute(raw) ? raw : path15.resolve(cwd, raw);
      this.cwd = safeExistingDirectory(candidate);
      const commandId2 = (0, import_node_crypto4.randomUUID)();
      sink({
        commandId: commandId2,
        kind: "system",
        chunk: `CWD \u2192 ${this.cwd}
`,
        at: nowIso()
      });
      const result = {
        commandId: commandId2,
        command: redactCommand(command),
        cwd: this.cwd,
        backend: "VERTEX_META",
        pid: null,
        exitCode: 0,
        durationMs: 0,
        stdoutBytes: 0,
        stderrBytes: 0,
        stopped: false
      };
      this.appendHistory(result);
      return result;
    }
    const backend = resolveBackend();
    const executionCommand = routedExecution?.executionCommand ?? command;
    const executionCwd = routedExecution?.executionCwd ?? cwd;
    const providerPlan = routedExecution?.providerRequest ? planVxsProviderExecution(
      process.cwd(),
      routedExecution.providerRequest,
      backend,
      executionCommand
    ) : null;
    const executionBackend = providerPlan ? `VXS_${providerPlan.route}_${routedExecution?.capability ?? "CAPABILITY"}` : routedExecution ? `VXS_${routedExecution.capability}` : backend;
    const executionProgram = providerPlan?.program ?? backend;
    const executionArgs = providerPlan?.args ?? [
      "-NoLogo",
      "-NoProfile",
      "-NonInteractive",
      "-Command",
      executionCommand
    ];
    const commandId = (0, import_node_crypto4.randomUUID)();
    const startedAt = Date.now();
    if (routedExecution) {
      sink({
        commandId,
        kind: "system",
        chunk: [
          `VXS ROUTE ${routedExecution.capability}`,
          `Workspace: ${executionCwd}`,
          `Adapter: ${routedExecution.routeSummary}`,
          `Provider: ${providerPlan?.route ?? "POWERSHELL"}${providerPlan ? ` (${providerPlan.reason})` : ""}`,
          `Execute: ${providerPlan ? [executionProgram, ...executionArgs].join(" ") : executionCommand}`,
          ""
        ].join("\n"),
        at: nowIso()
      });
    }
    const child = (0, import_node_child_process9.spawn)(
      executionProgram,
      executionArgs,
      {
        cwd: executionCwd,
        windowsHide: true,
        shell: false,
        stdio: ["pipe", "pipe", "pipe"]
      }
    );
    const active = {
      commandId,
      command,
      cwd: executionCwd,
      backend: executionBackend,
      child,
      startedAt,
      stdoutBytes: 0,
      stderrBytes: 0,
      stdoutTruncated: false,
      stderrTruncated: false,
      stopped: false
    };
    this.active = active;
    sink({
      commandId,
      kind: "system",
      chunk: `RUN ${executionBackend} \xB7 PID ${child.pid ?? "pending"} \xB7 ${executionCwd}
`,
      at: nowIso()
    });
    const stream = (kind, chunk) => {
      const current = this.active;
      if (!current || current.commandId !== commandId) return;
      const byteField = kind === "stdout" ? "stdoutBytes" : "stderrBytes";
      const truncateField = kind === "stdout" ? "stdoutTruncated" : "stderrTruncated";
      current[byteField] += chunk.byteLength;
      if (current[truncateField]) return;
      if (current[byteField] > MAX_STREAM_BYTES) {
        current[truncateField] = true;
        sink({
          commandId,
          kind: "system",
          chunk: `[${kind.toUpperCase()} TRUNCATED AFTER ${MAX_STREAM_BYTES} BYTES]
`,
          at: nowIso()
        });
        return;
      }
      sink({
        commandId,
        kind,
        chunk: chunk.toString("utf8"),
        at: nowIso()
      });
    };
    child.stdout.on("data", (chunk) => stream("stdout", chunk));
    child.stderr.on("data", (chunk) => stream("stderr", chunk));
    return await new Promise((resolve10, reject) => {
      child.once("error", (error2) => {
        if (this.active?.commandId === commandId) {
          this.active = null;
        }
        sink({
          commandId,
          kind: "stderr",
          chunk: `START ERROR: ${error2.message}
`,
          at: nowIso()
        });
        reject(error2);
      });
      child.once("close", (code) => {
        const snapshot2 = this.active?.commandId === commandId ? this.active : active;
        const result = {
          commandId,
          command: redactCommand(command),
          cwd: executionCwd,
          backend: executionBackend,
          pid: child.pid ?? null,
          exitCode: typeof code === "number" ? code : -1,
          durationMs: Date.now() - startedAt,
          stdoutBytes: snapshot2.stdoutBytes,
          stderrBytes: snapshot2.stderrBytes,
          stopped: snapshot2.stopped
        };
        if (this.active?.commandId === commandId) {
          this.active = null;
        }
        this.appendHistory(result);
        sink({
          commandId,
          kind: "system",
          chunk: `EXIT ${result.exitCode} \xB7 ${result.durationMs} ms${result.stopped ? " \xB7 STOPPED" : ""}
`,
          at: nowIso()
        });
        resolve10(result);
      });
    });
  }
  async stop() {
    const current = this.active;
    if (!current) return this.state();
    current.stopped = true;
    const pid = current.child.pid;
    if (typeof pid === "number" && pid > 0) {
      await new Promise((resolve10) => {
        const killer = (0, import_node_child_process9.spawn)(
          "taskkill.exe",
          ["/PID", String(pid), "/T", "/F"],
          {
            windowsHide: true,
            shell: false,
            stdio: "ignore"
          }
        );
        killer.once("error", () => {
          try {
            current.child.kill();
          } catch {
          }
          resolve10();
        });
        killer.once("close", () => resolve10());
      });
    } else {
      try {
        current.child.kill();
      } catch {
      }
    }
    return this.state();
  }
  appendHistory(result) {
    const record = {
      schema: "vertex-shell/command-evidence-1",
      generation: GENERATION,
      at: nowIso(),
      command_id: result.commandId,
      command: result.command,
      cwd: result.cwd,
      backend: result.backend,
      pid: result.pid,
      exit_code: result.exitCode,
      duration_ms: result.durationMs,
      stdout_bytes: result.stdoutBytes,
      stderr_bytes: result.stderrBytes,
      stopped: result.stopped
    };
    fs14.appendFileSync(
      this.historyPath(),
      `${JSON.stringify(record)}
`,
      "utf8"
    );
  }
};

// src/main/ipc/register-vertex-shell-ipc.ts
var import_electron4 = require("electron");
function registerVeraVxsProductionIpc(service) {
  import_electron4.ipcMain.removeHandler("vera-vxs:execute");
  import_electron4.ipcMain.handle("vera-vxs:execute", async (_event, request2) => {
    const module2 = await Promise.resolve().then(() => (init_vera_vxs_interface(), vera_vxs_interface_exports));
    return module2.executeVeraVxsRequest(service, request2);
  });
}

// scripts/vera_vxs_human_full_access_e2e_000088V4.ts
init_vera_vxs_human_authority();
var receiptPath = process.env.VERA_VXS_GATE_E2E_RECEIPT;
var preloadPath = process.env.VERA_VXS_PRELOAD_PATH;
function request(command, id) {
  return {
    schema: "vertex-vxs/vera-request-1",
    requestId: id,
    correlationId: `corr-${id}`,
    origin: {
      vera: "VERA04",
      session: "vera-04",
      window: "vera-04"
    },
    authority: "AUTO_SAFE",
    command,
    cwd: process.cwd()
  };
}
async function rendererInvoke(win, value) {
  return await win.webContents.executeJavaScript(
    `window.veraVxs.execute(${JSON.stringify(value)})`,
    true
  );
}
async function rendererReject(win, value) {
  return await win.webContents.executeJavaScript(
    `(async () => {
      try {
        await window.veraVxs.execute(${JSON.stringify(value)})
        return 'UNEXPECTED_ACCEPT'
      } catch (error) {
        return String(error && error.message ? error.message : error)
      }
    })()`,
    true
  );
}
async function main() {
  if (!receiptPath) throw new Error("VERA_VXS_GATE_E2E_RECEIPT_REQUIRED");
  if (!preloadPath) throw new Error("VERA_VXS_PRELOAD_PATH_REQUIRED");
  await import_electron5.app.whenReady();
  revokeVeraVxsHumanFullAccess();
  const service = new VertexShellService();
  registerVeraVxsProductionIpc(service);
  const win = new import_electron5.BrowserWindow({
    show: false,
    webPreferences: {
      preload: path16.resolve(preloadPath),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });
  await win.loadURL("data:text/html,<html><body>VERA VXS HUMAN GATE E2E</body></html>");
  const preloadReady = await win.webContents.executeJavaScript(
    `Boolean(window.veraVxs && typeof window.veraVxs.execute === 'function')`,
    true
  );
  if (!preloadReady) throw new Error("VERA_VXS_PRELOAD_API_NOT_EXPOSED");
  const lockedRequest = request("vxs --version", "gate-locked-before");
  const lockedBefore = await rendererReject(win, lockedRequest);
  if (!lockedBefore.includes("VERA_VXS_HUMAN_GATE_REQUIRED")) {
    throw new Error("LOCKED_GATE_DID_NOT_REJECT:" + lockedBefore);
  }
  grantVeraVxsHumanFullAccess();
  const versionResult = await rendererInvoke(
    win,
    request("vxs --version", "gate-full-vxs-version")
  );
  if (versionResult?.shellResult?.exitCode !== 0) {
    throw new Error("FULL_VXS_VERSION_FAILED");
  }
  const powershellResult = await rendererInvoke(
    win,
    request("Get-Process | Select-Object -First 1", "gate-full-powershell-read")
  );
  if (powershellResult?.shellResult?.exitCode !== 0) {
    throw new Error("FULL_POWERSHELL_READ_FAILED");
  }
  revokeVeraVxsHumanFullAccess();
  const lockedAfter = await rendererReject(
    win,
    request("vxs --version", "gate-locked-after")
  );
  if (!lockedAfter.includes("VERA_VXS_HUMAN_GATE_REQUIRED")) {
    throw new Error("REVOKED_GATE_DID_NOT_REJECT:" + lockedAfter);
  }
  const receipt = {
    schema: "vertex-vxs/human-full-access-e2e-receipt-1",
    origin: "VERA04/vera-04/vera-04",
    preload_api: "window.veraVxs.execute",
    ipc_channel: "vera-vxs:execute",
    locked_before: true,
    full_vxs_exit_code: versionResult.shellResult.exitCode,
    full_vxs_backend: String(versionResult.shellResult.backend ?? ""),
    full_powershell_exit_code: powershellResult.shellResult.exitCode,
    full_powershell_backend: String(powershellResult.shellResult.backend ?? ""),
    locked_after_revoke: true,
    process_scoped_authority: true,
    human_grant_simulated_in_test: true
  };
  fs15.mkdirSync(path16.dirname(receiptPath), { recursive: true });
  fs15.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2), "utf8");
  if (!win.isDestroyed()) win.destroy();
  import_electron5.app.quit();
}
main().catch((error2) => {
  console.error(error2 instanceof Error ? error2.stack ?? error2.message : String(error2));
  import_electron5.app.exit(91);
});
