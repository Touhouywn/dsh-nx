param(
    [Parameter(Mandatory = $true)]
    [string]$Command,

    [hashtable]$Params = @{},
    [string]$HostName = "127.0.0.1",
    [int]$Port = 25121,
    [int]$TimeoutMs = 10000
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "nx_env.ps1")
$NxEnv = Initialize-Nx2512Environment -NxRoot $env:NX2512_ROOT -Require @("Managed")
if (-not $PSBoundParameters.ContainsKey("Port")) {
    $Port = $NxEnv.livePort
}
$LiveCli = Join-Path $ScriptDir "nx_live_cli.ps1"

if ($HostName -ne "127.0.0.1" -and $HostName -ne "localhost") {
    throw "The .NET live bridge only supports localhost connections."
}

$CommandMap = @{
    "create_modeling_part" = "create-modeling-part"
    "create_block" = "create-block"
    "run_script_file" = "run-python"
    "run_python" = "run-python"
    "module_list" = "module-list"
}

$LiveCommand = $Command
if ($CommandMap.ContainsKey($Command)) {
    $LiveCommand = $CommandMap[$Command]
}

$ParamsJson = $Params | ConvertTo-Json -Depth 20 -Compress
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $LiveCli -Command $LiveCommand -ParamsJson $ParamsJson -Port $Port
