param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "nx_env.ps1")

$Expected = @{
    UGII_CUSTOM_DIRECTORY_FILE = (Join-Path (Join-Path $Script:Nx2512PluginRoot "nx_runtime") "custom_dirs.dat")
    NX2512_PLUGIN_ROOT = $Script:Nx2512PluginRoot
    NX2512_PROJECT_ROOT = $Script:Nx2512ProjectRoot
    DC2512_PROJECT_ROOT = $Script:Nx2512ProjectRoot
    NX2512_LIVE_PORT = [string]$Script:Nx2512LivePort
    NX2512_AUTO_LAUNCH = $Script:Nx2512AutoLaunch
    NX2512_AUTO_LAUNCH_TIMEOUT = $Script:Nx2512AutoLaunchTimeout
    NX2512_REQUIRE_ONLINE = $Script:Nx2512RequireOnline
    NX2512_DELETE_GENERATED_SCRIPTS = $Script:Nx2512DeleteGeneratedScripts
    NX2512_GENERATED_SCRIPT_ROOT = (Join-Path $Script:Nx2512PluginRoot "scripts\generated")
    CODEX_PYTHON = $Script:CodexBundledPython
}

try {
    $ResolvedRoot = Resolve-Nx2512Root -RequestedRoot $env:NX2512_ROOT -Require @("Any")
    $ResolvedBin = Join-Path $ResolvedRoot "NXBIN"
    $Expected.NX2512_ROOT = $ResolvedRoot
    $Expected.DC2512_ROOT = $ResolvedRoot
    $Expected.DC2512_BIN = $ResolvedBin
    $Expected.UGII_BASE_DIR = $ResolvedRoot
    $Expected.UGII_ROOT_DIR = $ResolvedBin
}
catch {
    Write-Output "NX root was not resolved; root-related user variables will be left untouched."
}

foreach ($Name in $Expected.Keys) {
    $Current = [Environment]::GetEnvironmentVariable($Name, "User")
    if ($Current -and [string]::Equals($Current, $Expected[$Name], [System.StringComparison]::OrdinalIgnoreCase)) {
        [Environment]::SetEnvironmentVariable($Name, $null, "User")
        Remove-Item "Env:\$Name" -ErrorAction SilentlyContinue
        Write-Output "Removed user $Name."
    }
    elseif ($Current) {
        Write-Output "User $Name was not owned by NX2512 Control: $Current"
    }
}
