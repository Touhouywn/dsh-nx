param(
    [string]$NxRoot = $env:NX2512_ROOT,
    [switch]$Clean,
    [switch]$ClientOnly,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginRoot = Split-Path -Parent $ScriptDir
. (Join-Path $ScriptDir "nx_env.ps1")
$NxEnv = Initialize-Nx2512Environment -NxRoot $NxRoot -Require @("Managed")

function Resolve-NxRoot {
    param([string]$RequestedRoot)

    Resolve-Nx2512Root -RequestedRoot $RequestedRoot -Require @("Managed")
}

function Resolve-Csc {
    $Candidates = @(
        (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe")
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path -LiteralPath $Candidate) {
            return $Candidate
        }
    }
    throw ".NET Framework csc.exe was not found."
}

$ResolvedRoot = $NxEnv.nxRoot
$ManagedDir = Join-Path $ResolvedRoot "NXBIN\managed"
$Csc = Resolve-Csc

$ServerSource = Join-Path $PluginRoot "scripts\dotnet_bridge\server\NXCodexLiveBridgeServer.cs"
$ClientSource = Join-Path $PluginRoot "scripts\dotnet_bridge\client\NXCodexLiveBridgeClient.cs"
$ServerOutDir = Join-Path $PluginRoot "nx_runtime\startup"
$ApplicationOutDir = Join-Path $PluginRoot "nx_runtime\application"
$ClientOutDir = Join-Path $PluginRoot "scripts\dotnet_bridge\bin"
$ServerDll = Join-Path $ServerOutDir "NXCodexLiveBridgeServer.dll"
$ApplicationServerDll = Join-Path $ApplicationOutDir "NXCodexLiveBridgeServer.dll"
$ClientExe = Join-Path $ClientOutDir "NXCodexLiveBridgeClient.exe"

function Get-NewestWriteTimeUtc {
    param([string[]]$Paths)

    $Newest = [datetime]::MinValue
    foreach ($Path in $Paths) {
        if (-not (Test-Path -LiteralPath $Path)) {
            return $null
        }
        $Item = Get-Item -LiteralPath $Path
        if ($Item.LastWriteTimeUtc -gt $Newest) {
            $Newest = $Item.LastWriteTimeUtc
        }
    }
    return $Newest
}

function Test-OutputsCurrent {
    param(
        [string[]]$Outputs,
        [string[]]$Inputs
    )

    $NewestInput = Get-NewestWriteTimeUtc -Paths $Inputs
    if ($null -eq $NewestInput) { return $false }

    foreach ($Output in $Outputs) {
        if (-not (Test-Path -LiteralPath $Output)) {
            return $false
        }
        if ((Get-Item -LiteralPath $Output).LastWriteTimeUtc -lt $NewestInput) {
            return $false
        }
    }
    return $true
}

$ServerInputs = @($ServerSource)
$ClientInputs = @($ClientSource)

if (-not $Force -and -not $Clean) {
    if ($ClientOnly) {
        if (Test-OutputsCurrent -Outputs @($ClientExe) -Inputs $ClientInputs) {
            [pscustomobject]@{
                skipped = $true
                reason = "client bridge is up to date"
                nxRoot = $ResolvedRoot
                clientExe = $ClientExe
            } | ConvertTo-Json -Depth 4
            return
        }
    }
    elseif ((Test-OutputsCurrent -Outputs @($ServerDll, $ApplicationServerDll) -Inputs $ServerInputs) -and
            (Test-OutputsCurrent -Outputs @($ClientExe) -Inputs $ClientInputs)) {
        [pscustomobject]@{
            skipped = $true
            reason = "live bridge is up to date"
            nxRoot = $ResolvedRoot
            serverDll = $ServerDll
            applicationServerDll = $ApplicationServerDll
            clientExe = $ClientExe
        } | ConvertTo-Json -Depth 4
        return
    }
}

if ($Clean -and -not $ClientOnly) {
    Remove-Item -LiteralPath $ServerDll -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ApplicationServerDll -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ClientExe -Force -ErrorAction SilentlyContinue
}
elseif ($Clean) {
    Remove-Item -LiteralPath $ClientExe -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Force -Path $ServerOutDir | Out-Null
New-Item -ItemType Directory -Force -Path $ApplicationOutDir | Out-Null
New-Item -ItemType Directory -Force -Path $ClientOutDir | Out-Null

$CommonReferences = @(
    (Join-Path $ManagedDir "NXOpen.dll"),
    (Join-Path $ManagedDir "NXOpen.UF.dll"),
    (Join-Path $ManagedDir "NXOpenUI.dll"),
    (Join-Path $ManagedDir "NXOpen.Utilities.dll"),
    "System.Runtime.Remoting.dll"
)

if (-not $ClientOnly) {
    $ServerArgs = @(
        "/nologo",
        "/target:library",
        "/platform:x64",
        "/out:$ServerDll"
    )
    $ServerArgs += $CommonReferences | ForEach-Object { "/reference:$_" }
    $ServerArgs += $ServerSource
    & $Csc @ServerArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to compile NXCodexLiveBridgeServer.dll. If NX is already running and has loaded the bridge, rerun with -ClientOnly or restart NX before a full rebuild."
    }
    Copy-Item -LiteralPath $ServerDll -Destination $ApplicationServerDll -Force
}

$ClientArgs = @(
    "/nologo",
    "/target:exe",
    "/platform:x64",
    "/out:$ClientExe",
    "/reference:System.Web.Extensions.dll"
)
$ClientArgs += $CommonReferences | ForEach-Object { "/reference:$_" }
$ClientArgs += $ClientSource
& $Csc @ClientArgs
if ($LASTEXITCODE -ne 0) {
    throw "Failed to compile NXCodexLiveBridgeClient.exe."
}

[pscustomobject]@{
    nxRoot = $ResolvedRoot
    csc = $Csc
    serverDll = $ServerDll
    applicationServerDll = $ApplicationServerDll
    clientExe = $ClientExe
} | ConvertTo-Json -Depth 4
