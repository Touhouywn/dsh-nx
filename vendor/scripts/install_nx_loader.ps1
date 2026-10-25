param(
    [string]$NxRoot = $env:NX2512_ROOT
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "nx_env.ps1")
$NxEnv = Initialize-Nx2512Environment -NxRoot $NxRoot -Require @("RunJournal") -PersistUser

if (-not (Test-Path -LiteralPath $NxEnv.customDirectoryFile)) {
    throw "Missing custom directory file: $($NxEnv.customDirectoryFile)"
}

Write-Output "NX2512_ROOT=$($NxEnv.nxRoot)"
Write-Output "DC2512_ROOT=$($NxEnv.nxRoot)"
Write-Output "DC2512_BIN=$($NxEnv.nxBin)"
Write-Output "UGII_BASE_DIR=$($NxEnv.nxRoot)"
Write-Output "UGII_ROOT_DIR=$($NxEnv.nxBin)"
Write-Output "UGII_CUSTOM_DIRECTORY_FILE=$($NxEnv.customDirectoryFile)"
Write-Output "NX2512_PLUGIN_ROOT=$($NxEnv.pluginRoot)"
Write-Output "NX2512_PROJECT_ROOT=$($NxEnv.projectRoot)"
Write-Output "DC2512_PROJECT_ROOT=$($NxEnv.projectRoot)"
Write-Output "NX2512_LIVE_PORT=$($NxEnv.livePort)"
Write-Output "NX2512_AUTO_LAUNCH=$($NxEnv.autoLaunch)"
Write-Output "NX2512_AUTO_LAUNCH_TIMEOUT=$($NxEnv.autoLaunchTimeout)"
Write-Output "NX2512_REQUIRE_ONLINE=$($NxEnv.requireOnline)"
Write-Output "NX2512_DELETE_GENERATED_SCRIPTS=$($NxEnv.deleteGeneratedScripts)"
Write-Output "NX2512_GENERATED_SCRIPT_ROOT=$($NxEnv.generatedScriptRoot)"
if ($NxEnv.codexPython) {
    Write-Output "CODEX_PYTHON=$($NxEnv.codexPython)"
}
Write-Output "Restart NX 2512 to load the NX2512 Control menu and auto-start the live bridge."
