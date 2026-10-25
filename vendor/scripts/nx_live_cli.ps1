param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("ping", "status", "module-list", "create-modeling-part", "create-block", "prepare-session", "run-python")]
    [string]$Command,

    [string]$ParamsJson = "{}",
    [string]$NxRoot = $env:NX2512_ROOT,
    [int]$Port = 25121,
    [switch]$NoBuild,
    [switch]$NoAutoLaunch,
    [int]$LaunchTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginRoot = Split-Path -Parent $ScriptDir
$ClientExe = Join-Path $PluginRoot "scripts\dotnet_bridge\bin\NXCodexLiveBridgeClient.exe"
. (Join-Path $ScriptDir "nx_env.ps1")
$NxEnv = Initialize-Nx2512Environment -NxRoot $NxRoot -Require @("Managed")
if (-not $PSBoundParameters.ContainsKey("Port")) {
    $Port = $NxEnv.livePort
}

function Resolve-NxRoot {
    param([string]$RequestedRoot)

    Resolve-Nx2512Root -RequestedRoot $RequestedRoot -Require @("RunJournal")
}

function Get-ModuleList {
    param([string]$ResolvedRoot)

    $StubsDir = Join-Path $ResolvedRoot "UGOPEN\pythonStubs\NXOpen"
    $PythonDir = Join-Path $ResolvedRoot "NXBIN\python"
    $ManagedDir = Join-Path $ResolvedRoot "NXBIN\managed"

    $StubModules = @()
    if (Test-Path -LiteralPath $StubsDir) {
        $StubModules = Get-ChildItem -LiteralPath $StubsDir -Directory -Force |
            ForEach-Object { "NXOpen.$($_.Name)" } |
            Sort-Object
    }

    $PythonModules = @()
    if (Test-Path -LiteralPath $PythonDir) {
        $PythonModules = Get-ChildItem -LiteralPath $PythonDir -Filter "NXOpen_*.pyd" -File -Force |
            ForEach-Object { "NXOpen." + ($_.BaseName -replace "^NXOpen_", "") } |
            Sort-Object
    }

    $ManagedAssemblies = @()
    if (Test-Path -LiteralPath $ManagedDir) {
        $ManagedAssemblies = Get-ChildItem -LiteralPath $ManagedDir -Filter "*.dll" -File -Force |
            Where-Object { $_.BaseName -match "Open|NXOpen|Snap" } |
            Select-Object -ExpandProperty Name |
            Sort-Object
    }

    $All = @("NXOpen")
    $All += $StubModules
    $All += $PythonModules
    $All = $All | Select-Object -Unique | Sort-Object

    $Required = [ordered]@{}
    foreach ($Name in @("NXOpen.Features", "NXOpen.Assemblies", "NXOpen.Drawings", "NXOpen.CAM", "NXOpen.CAE", "NXOpen.UF")) {
        $Required[$Name] = [bool]($All -contains $Name -or ($Name -eq "NXOpen.UF" -and (Test-Path -LiteralPath (Join-Path $PythonDir "NXOpen_UF.pyd"))))
    }

    [pscustomobject]@{
        ok = $true
        result = [pscustomobject]@{
            nxRoot = $ResolvedRoot
            moduleCount = @($All).Count
            modules = $All
            required = $Required
            sources = [pscustomobject]@{
                pythonStubs = $StubsDir
                pythonPyd = $PythonDir
                managed = $ManagedDir
            }
            managedAssemblies = $ManagedAssemblies
        }
    } | ConvertTo-Json -Depth 8
}

function Get-NxGuiProcess {
    @(Get-Process -Name ugraf,nx -ErrorAction SilentlyContinue)
}

function Test-LiveBridge {
    param(
        [string]$ResolvedRoot,
        [int]$LivePort
    )

    if (-not (Test-Path -LiteralPath $ClientExe)) {
        return $false
    }

    $EmptyParams = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes("{}"))
    try {
        $Response = & $ClientExe -Command ping -ParamsJsonBase64 $EmptyParams -NxRoot $ResolvedRoot -Port $LivePort 2>$null
        return ($LASTEXITCODE -eq 0 -and $Response)
    }
    catch {
        return $false
    }
}

function Ensure-NxProcessForLiveCommand {
    param(
        [string]$ResolvedRoot,
        [int]$LivePort,
        [int]$TimeoutSeconds
    )

    if ($NoAutoLaunch -or $Command -eq "module-list") {
        return
    }
    if ($env:NX2512_AUTO_LAUNCH -and $env:NX2512_AUTO_LAUNCH -match "^(0|false|no|off)$") {
        return
    }
    if (@(Get-NxGuiProcess).Count -gt 0) {
        return
    }

    $LaunchScript = Join-Path $PluginRoot "scripts\launch_nx_with_plugin.ps1"
    if (-not (Test-Path -LiteralPath $LaunchScript)) {
        throw "NX is not running and launch script is missing: $LaunchScript"
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $LaunchScript -NxRoot $ResolvedRoot | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to auto-launch NX."
    }

    $Deadline = (Get-Date).AddSeconds([Math]::Max(10, $TimeoutSeconds))
    do {
        Start-Sleep -Seconds 3
        if (Test-LiveBridge -ResolvedRoot $ResolvedRoot -LivePort $LivePort) {
            return
        }
    } while ((Get-Date) -lt $Deadline)

    throw "NX was auto-launched, but the live bridge did not respond on port $LivePort within $TimeoutSeconds seconds."
}

$ResolvedRoot = $NxEnv.nxRoot

if ($Command -eq "module-list") {
    Get-ModuleList -ResolvedRoot $ResolvedRoot
    exit 0
}

if (-not (Test-Path -LiteralPath $ClientExe)) {
    if ($NoBuild) {
        throw "Missing live bridge client: $ClientExe"
    }
    $BuildScript = Join-Path $PluginRoot "scripts\build_dotnet_bridge.ps1"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BuildScript -NxRoot $ResolvedRoot | Out-Null
}

Ensure-NxProcessForLiveCommand -ResolvedRoot $ResolvedRoot -LivePort $Port -TimeoutSeconds $LaunchTimeoutSeconds

$ParamsJsonBase64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($ParamsJson))
& $ClientExe -Command $Command -ParamsJsonBase64 $ParamsJsonBase64 -NxRoot $ResolvedRoot -Port $Port
$ExitCode = $LASTEXITCODE
if ($ExitCode -ne 0) {
    exit $ExitCode
}
