param()

$ErrorActionPreference = 'Stop'

function As-String {
    param($Value)
    if ($null -eq $Value) { return $null }
    return [string]$Value
}

$psVersion = [string]$PSVersionTable.PSVersion
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$reportDir = Join-Path $projectRoot 'runtime\vxs\predation'
$reportPath = Join-Path $reportDir ("powershell-{0}-capability-census.json" -f $psVersion)

$dock = [ordered]@{
    schema = 'vertex-vxs/predation-dock-probe-1'
    state = 'DOCKED'
    ps_version = $psVersion
    ps_edition = [string]$PSVersionTable.PSEdition
    os = [string]$PSVersionTable.OS
    platform = [string]$PSVersionTable.Platform
}
Write-Output ("VXS_PREDATION_DOCK=" + ($dock | ConvertTo-Json -Compress))

$providers = @(
    Get-PSProvider |
    Sort-Object -Property Name |
    ForEach-Object {
        [ordered]@{
            name = [string]$_.Name
            implementing_type = if ($null -ne $_.ImplementingType) { [string]$_.ImplementingType.FullName } else { $null }
            capabilities = [string]$_.Capabilities
            drives = @($_.Drives | ForEach-Object { [string]$_.Name })
        }
    }
)

$modules = @(
    Get-Module -ListAvailable |
    Sort-Object -Property Name, Version |
    ForEach-Object {
        [ordered]@{
            name = [string]$_.Name
            version = [string]$_.Version
            module_type = [string]$_.ModuleType
            path = [string]$_.Path
            compatible_ps_editions = @($_.CompatiblePSEditions | ForEach-Object { [string]$_ })
        }
    }
)

$commands = @(
    Get-Command -All |
    Sort-Object -Property Name, CommandType, ModuleName |
    ForEach-Object {
        $verb = $null
        $noun = $null

        if ($_.PSObject.Properties.Match('Verb').Count -gt 0) { $verb = [string]$_.Verb }
        if ($_.PSObject.Properties.Match('Noun').Count -gt 0) { $noun = [string]$_.Noun }

        $supportsShouldProcess = $false
        $confirmImpact = $null

        if ($_.CommandType -eq [System.Management.Automation.CommandTypes]::Cmdlet) {
            try {
                $attr = $_.ImplementingType.GetCustomAttributes(
                    [System.Management.Automation.CmdletAttribute],
                    $true
                ) | Select-Object -First 1

                if ($null -ne $attr) {
                    $supportsShouldProcess = [bool]$attr.SupportsShouldProcess
                    $confirmImpact = [string]$attr.ConfirmImpact
                }
            } catch {
            }
        }

        $safeVerbs = @('Get','Test','Find','Measure','Compare','Resolve')
        $autoSafe = ($null -ne $verb) -and ($safeVerbs -contains $verb) -and (-not $supportsShouldProcess)

        $parameterSets = @()
        try {
            $parameterSets = @(
                foreach ($set in @($_.ParameterSets)) {
                    [ordered]@{
                        name = [string]$set.Name
                        is_default = [bool]$set.IsDefault
                        parameters = @(
                            foreach ($p in @($set.Parameters)) {
                                [ordered]@{
                                    name = [string]$p.Name
                                    type = if ($null -ne $p.ParameterType) { [string]$p.ParameterType.FullName } else { $null }
                                    is_mandatory = [bool]$p.IsMandatory
                                    position = [int]$p.Position
                                    value_from_pipeline = [bool]$p.ValueFromPipeline
                                    value_from_pipeline_by_property_name = [bool]$p.ValueFromPipelineByPropertyName
                                }
                            }
                        )
                    }
                }
            )
        } catch {
            $parameterSets = @()
        }

        [ordered]@{
            name = [string]$_.Name
            command_type = [string]$_.CommandType
            module_name = [string]$_.ModuleName
            source = [string]$_.Source
            version = if ($null -ne $_.Version) { [string]$_.Version } else { $null }
            verb = $verb
            noun = $noun
            supports_should_process = $supportsShouldProcess
            confirm_impact = $confirmImpact
            authority_candidate = if ($autoSafe) { 'AUTO_SAFE' } else { 'HUMAN_APPLY' }
            parameter_sets = $parameterSets
        }
    }
)

$aliases = @(
    Get-Alias |
    Sort-Object -Property Name |
    ForEach-Object {
        [ordered]@{
            name = [string]$_.Name
            definition = [string]$_.Definition
            options = [string]$_.Options
        }
    }
)

$verbGroups = @(
    $commands |
    Where-Object { $_.verb } |
    Group-Object -Property verb |
    Sort-Object -Property `
        @{ Expression = 'Count'; Descending = $true }, `
        @{ Expression = 'Name'; Ascending = $true } |
    ForEach-Object {
        [ordered]@{
            verb = [string]$_.Name
            count = [int]$_.Count
        }
    }
)

$moduleGroups = @(
    $commands |
    Group-Object -Property module_name |
    Sort-Object -Property `
        @{ Expression = 'Count'; Descending = $true }, `
        @{ Expression = 'Name'; Ascending = $true } |
    ForEach-Object {
        [ordered]@{
            module = [string]$_.Name
            count = [int]$_.Count
        }
    }
)

$report = [ordered]@{
    schema = 'vertex-vxs/powershell-capability-census-1'
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    runtime = [ordered]@{
        ps_version = $psVersion
        ps_edition = [string]$PSVersionTable.PSEdition
        git_commit_id = As-String $PSVersionTable.GitCommitId
        os = As-String $PSVersionTable.OS
        platform = As-String $PSVersionTable.Platform
    }
    summary = [ordered]@{
        command_count = [int]$commands.Count
        module_count = [int]$modules.Count
        provider_count = [int]$providers.Count
        alias_count = [int]$aliases.Count
        supports_should_process_count = [int]@($commands | Where-Object { $_.supports_should_process }).Count
        auto_safe_candidate_count = [int]@($commands | Where-Object { $_.authority_candidate -eq 'AUTO_SAFE' }).Count
        human_apply_candidate_count = [int]@($commands | Where-Object { $_.authority_candidate -eq 'HUMAN_APPLY' }).Count
    }
    providers = $providers
    modules = $modules
    aliases = $aliases
    verb_groups = $verbGroups
    module_groups = $moduleGroups
    commands = $commands
}

New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding utf8NoBOM

$reportHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $reportPath).Hash.ToLowerInvariant()
$reportBytes = (Get-Item -LiteralPath $reportPath).Length

$result = [ordered]@{
    probe = 'VXS_POWERSHELL_766_PREDATION'
    state = 'PASS'
    runtime_version = $psVersion
    command_count = [int]$commands.Count
    module_count = [int]$modules.Count
    provider_count = [int]$providers.Count
    alias_count = [int]$aliases.Count
    report_path = $reportPath
    report_bytes = [int64]$reportBytes
    report_sha256 = $reportHash
}

Write-Output ("VXS_PREDATION_RESULT=" + ($result | ConvertTo-Json -Compress))
exit 0
