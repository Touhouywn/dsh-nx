param(
    [string]$NxRoot = $env:NX2512_ROOT,
    [int]$TimeoutSeconds = 20
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "nx_env.ps1")
$NxEnv = Initialize-Nx2512Environment -NxRoot $NxRoot -Require @("Managed")
$PluginRoot = $NxEnv.pluginRoot

$BuildScript = Join-Path $PluginRoot "scripts\build_dotnet_bridge.ps1"
$BuildArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $BuildScript, "-NxRoot", $NxEnv.nxRoot)
$ServerDll = Join-Path $PluginRoot "nx_runtime\startup\NXCodexLiveBridgeServer.dll"
try {
    & powershell.exe @BuildArgs | Out-Null
}
catch {
    if (Test-Path -LiteralPath $ServerDll) {
        $ClientBuildArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $BuildScript, "-ClientOnly")
        $ClientBuildArgs += @("-NxRoot", $NxEnv.nxRoot)
        & powershell.exe @ClientBuildArgs | Out-Null
    }
    else {
        throw
    }
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NativeWindowTools {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$Process = Get-Process -Name ugraf -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1

if (-not $Process) {
    throw "No visible NX ugraf window was found."
}

[NativeWindowTools]::ShowWindow($Process.MainWindowHandle, 9) | Out-Null
[NativeWindowTools]::SetForegroundWindow($Process.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 500

[System.Windows.Forms.SendKeys]::SendWait("^%+B")

$LiveCli = Join-Path $PluginRoot "scripts\nx_live_cli.ps1"
$Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 1
    try {
        $PingArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $LiveCli, "-Command", "ping", "-NoBuild", "-NxRoot", $NxEnv.nxRoot, "-Port", $NxEnv.livePort)
        $Response = & powershell.exe @PingArgs
        if ($LASTEXITCODE -eq 0 -and $Response) {
            $Response
            exit 0
        }
    }
    catch {
    }
} while ((Get-Date) -lt $Deadline)

throw "Timed out waiting for Codex NX live bridge. In NX, use NX2512 Control > Start Codex Live Bridge and retry."
