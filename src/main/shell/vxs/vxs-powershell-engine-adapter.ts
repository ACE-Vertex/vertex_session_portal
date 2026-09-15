// VXS_POWERSHELL_ENGINE_PROVIDER_000067V3
import { Buffer } from 'node:buffer'

export type VxsPowerShellEngineAction =
  | 'engine'
  | 'commands'
  | 'describe'
  | 'providers'
  | 'modules'
  | 'plan'
  | 'invoke'

export interface VxsPowerShellEngineRequest {
  action: VxsPowerShellEngineAction
  pattern?: string
  command?: string
  script?: string
}

export interface VxsPowerShellEnginePlan {
  executionCommand: string
  capability: string
  routeSummary: string
}

const ENGINE_SCHEMA = 'vxs-powershell-engine/1' as const

function encodeRequest(request: VxsPowerShellEngineRequest): string {
  return Buffer.from(
    JSON.stringify({ schema: ENGINE_SCHEMA, ...request }),
    'utf8'
  ).toString('base64')
}

// This script runs inside the existing pwsh compatibility process, but does not
// treat PowerShell as an opaque text shell. It uses System.Management.Automation
// Parser/AST, CommandInfo/CommandMetadata, Provider metadata and engine state as
// structured VXS capability inputs.
const ENGINE_CORE = String.raw`
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
`

export function buildVxsPowerShellEnginePlan(
  request: VxsPowerShellEngineRequest
): VxsPowerShellEnginePlan {
  const payload = encodeRequest(request)
  const body = ENGINE_CORE.replace('__VXS_PAYLOAD__', payload)

  return {
    executionCommand: `& {${body}}`,
    capability: `POWERSHELL_ENGINE_${request.action.toUpperCase()}`,
    routeSummary:
      `VXS PowerShell Engine Provider: ${request.action} via System.Management.Automation metadata/AST`
  }
}
