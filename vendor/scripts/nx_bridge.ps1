param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("status", "run-journal", "create-part", "open-part")]
    [string]$Action,

    [string]$NxRoot = $env:NX2512_ROOT,
    [string]$JournalPath,
    [string]$PartPath,
    [string[]]$JournalArgs = @()
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PluginRoot = Split-Path -Parent $ScriptDir
$WorkDir = Join-Path $PluginRoot ".work"
. (Join-Path $ScriptDir "nx_env.ps1")
$NxEnv = Initialize-Nx2512Environment -NxRoot $NxRoot -Require @("RunJournal")

function Resolve-NxRoot {
    param([string]$RequestedRoot)

    Resolve-Nx2512Root -RequestedRoot $RequestedRoot -Require @("RunJournal")
}

function Get-NxPaths {
    param([string]$Root)

    $NxBin = Join-Path $Root "NXBIN"
    [pscustomobject]@{
        Root = $Root
        NxBin = $NxBin
        RunJournal = Join-Path $NxBin "run_journal.exe"
        Ugraf = Join-Path $NxBin "ugraf.exe"
        PythonModules = Join-Path $NxBin "python"
    }
}

function Get-NxStatus {
    param($Paths)

    $Processes = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -in @("ugraf", "nx", "run_journal")
    } | Select-Object ProcessName, Id, MainWindowTitle

    [pscustomobject]@{
        nxRoot = $Paths.Root
        runJournal = $Paths.RunJournal
        ugraf = $Paths.Ugraf
        pythonModules = $Paths.PythonModules
        nxProcessCount = @($Processes).Count
        nxProcesses = @($Processes)
    } | ConvertTo-Json -Depth 4
}

function Invoke-NxJournal {
    param(
        $Paths,
        [string]$Path,
        [string[]]$Args = @()
    )

    if (-not $Path) { throw "-JournalPath is required." }
    $ResolvedJournal = (Resolve-Path -LiteralPath $Path).Path
    $Env:UGII_BASE_DIR = $Paths.Root
    $Env:UGII_ROOT_DIR = $Paths.NxBin
    $Env:PATH = "$($Paths.NxBin);$Env:PATH"

    $CommandArgs = @("-nx", $ResolvedJournal)
    if ($Args.Count -gt 0) {
        $CommandArgs += "-args"
        $CommandArgs += $Args
    }

    & $Paths.RunJournal @CommandArgs
    $ExitCode = $LASTEXITCODE
    if ($ExitCode -ne 0) {
        throw "run_journal failed with exit code $ExitCode."
    }
}

function New-CreatePartJournal {
    param([string]$TargetPart)

    if (-not (Test-Path -LiteralPath $WorkDir)) {
        New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
    }

    $Journal = Join-Path $WorkDir "create_part.py"
    $EscapedPart = $TargetPart.Replace("\", "\\")
    @"
import NXOpen

def main():
    session = NXOpen.Session.GetSession()
    session.ApplicationSwitchImmediate("UG_APP_MODELING")
    part = session.Parts.NewDisplay(r"$EscapedPart", NXOpen.Part.Units.Millimeters)
    session.Parts.SetWork(part)
    session.Parts.SetDisplay(part, False, False)
    part.ModelingViews.WorkView.Fit()
    part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
    session.ListingWindow.Open()
    session.ListingWindow.WriteLine("Created part: $EscapedPart")

if __name__ == "__main__":
    main()
"@ | Set-Content -LiteralPath $Journal -Encoding UTF8

    return $Journal
}

function New-OpenPartJournal {
    param([string]$TargetPart)

    if (-not (Test-Path -LiteralPath $WorkDir)) {
        New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
    }

    $Journal = Join-Path $WorkDir "open_part.py"
    $EscapedPart = $TargetPart.Replace("\", "\\")
    @"
import NXOpen

def main():
    session = NXOpen.Session.GetSession()
    session.ApplicationSwitchImmediate("UG_APP_MODELING")
    part, load_status = session.Parts.OpenBaseDisplay(r"$EscapedPart")
    session.Parts.SetWork(part)
    session.Parts.SetDisplay(part, False, False)
    part.ModelingViews.WorkView.Fit()
    try:
        load_status.Dispose()
    except Exception:
        pass
    session.ListingWindow.Open()
    session.ListingWindow.WriteLine("Opened part: $EscapedPart")

if __name__ == "__main__":
    main()
"@ | Set-Content -LiteralPath $Journal -Encoding UTF8

    return $Journal
}

$Paths = [pscustomobject]@{
    Root = $NxEnv.nxRoot
    NxBin = $NxEnv.nxBin
    RunJournal = $NxEnv.runJournal
    Ugraf = $NxEnv.ugraf
    PythonModules = $NxEnv.pythonModules
}

switch ($Action) {
    "status" {
        Get-NxStatus -Paths $Paths
    }
    "run-journal" {
        Invoke-NxJournal -Paths $Paths -Path $JournalPath -Args $JournalArgs
    }
    "create-part" {
        if (-not $PartPath) { throw "-PartPath is required." }
        $FullPartPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($PartPath)
        $Journal = New-CreatePartJournal -TargetPart $FullPartPath
        Invoke-NxJournal -Paths $Paths -Path $Journal -Args @()
    }
    "open-part" {
        if (-not $PartPath) { throw "-PartPath is required." }
        $FullPartPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($PartPath)
        $Journal = New-OpenPartJournal -TargetPart $FullPartPath
        Invoke-NxJournal -Paths $Paths -Path $Journal -Args @()
    }
}
