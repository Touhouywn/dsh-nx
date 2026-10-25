param(
    [string]$NxRoot = $env:NX2512_ROOT,
    [switch]$ForceBuild
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "nx_env.ps1")
$NxEnv = Initialize-Nx2512Environment -NxRoot $NxRoot -Require @("Ugraf", "Managed")
$PluginRoot = $NxEnv.pluginRoot

$BuildScript = Join-Path $PluginRoot "scripts\build_dotnet_bridge.ps1"
$ServerSource = Join-Path $PluginRoot "scripts\dotnet_bridge\server\NXCodexLiveBridgeServer.cs"
$ClientSource = Join-Path $PluginRoot "scripts\dotnet_bridge\client\NXCodexLiveBridgeClient.cs"
$ServerDll = Join-Path $PluginRoot "nx_runtime\startup\NXCodexLiveBridgeServer.dll"
$ApplicationServerDll = Join-Path $PluginRoot "nx_runtime\application\NXCodexLiveBridgeServer.dll"
$ClientExe = Join-Path $PluginRoot "scripts\dotnet_bridge\bin\NXCodexLiveBridgeClient.exe"

function Test-BridgeOutputCurrent {
    param(
        [string[]]$Outputs,
        [string[]]$Inputs
    )

    foreach ($Output in $Outputs) {
        if (-not (Test-Path -LiteralPath $Output)) {
            return $false
        }
    }

    $NewestInput = ($Inputs | ForEach-Object { (Get-Item -LiteralPath $_).LastWriteTimeUtc } | Sort-Object -Descending | Select-Object -First 1)
    foreach ($Output in $Outputs) {
        if ((Get-Item -LiteralPath $Output).LastWriteTimeUtc -lt $NewestInput) {
            return $false
        }
    }
    return $true
}

$NeedBuild = $ForceBuild -or
    -not (Test-BridgeOutputCurrent -Outputs @($ServerDll, $ApplicationServerDll) -Inputs @($ServerSource)) -or
    -not (Test-BridgeOutputCurrent -Outputs @($ClientExe) -Inputs @($ClientSource))

if ($NeedBuild) {
    $BuildArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $BuildScript, "-NxRoot", $NxEnv.nxRoot)
    if ($ForceBuild) {
        $BuildArgs += "-Force"
    }

    try {
        & powershell.exe @BuildArgs | Out-Null
    }
    catch {
        if (Test-Path -LiteralPath $ServerDll) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $BuildScript -NxRoot $NxEnv.nxRoot -ClientOnly -Force | Out-Null
        }
        else {
            throw
        }
    }
}

Start-Process -FilePath $NxEnv.ugraf -WorkingDirectory (Split-Path -Parent $NxEnv.ugraf)
