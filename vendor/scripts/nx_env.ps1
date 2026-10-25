param()

$Script:Nx2512PluginRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Script:Nx2512ProjectRoot = Join-Path $env:USERPROFILE "Documents\Codex\NX2512"
$Script:Nx2512InstallNames = @("NX 2512", "NX2512", "Siemens NX 2512", "NX")
$Script:Nx2512LivePort = 25121
$Script:Nx2512AutoLaunch = "true"
$Script:Nx2512AutoLaunchTimeout = "120"
$Script:Nx2512RequireOnline = "true"
$Script:Nx2512DeleteGeneratedScripts = "true"
$Script:CodexBundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

function Get-FixedDriveRoots {
    $Roots = @()
    try {
        $Roots += Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction Stop |
            ForEach-Object { "$($_.DeviceID)\" }
    }
    catch {
        $Roots += [System.IO.DriveInfo]::GetDrives() |
            Where-Object { $_.DriveType -eq [System.IO.DriveType]::Fixed -and $_.IsReady } |
            ForEach-Object { $_.RootDirectory.FullName }
    }
    $Roots | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -Unique
}

function Get-Nx2512RegistryCandidates {
    $Keys = @(
        "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
        "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*"
    )

    foreach ($Key in $Keys) {
        Get-ItemProperty -Path $Key -ErrorAction SilentlyContinue |
            Where-Object {
                ($_.DisplayName -and $_.DisplayName -match "(Siemens|UGS).*(NX|Designcenter)|NX\s*2512|Designcenter") -or
                ($_.InstallLocation -and $_.InstallLocation -match "\\Siemens\\.*NX")
            } |
            ForEach-Object {
                if ($_.InstallLocation) { $_.InstallLocation }
                if ($_.DisplayIcon) { Split-Path -Parent $_.DisplayIcon.Trim('"') }
            }
    }
}

function Get-Nx2512CommonCandidates {
    $Bases = @()
    foreach ($Name in @("UGII_BASE_DIR", "UGII_ROOT_DIR", "NX_ROOT", "NXBIN", "SIEMENS_NX_ROOT")) {
        $Value = [Environment]::GetEnvironmentVariable($Name)
        if ($Value) { $Bases += $Value }
    }
    foreach ($Name in @("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)")) {
        $Value = [Environment]::GetEnvironmentVariable($Name)
        if ($Value) { $Bases += (Join-Path $Value "Siemens") }
    }
    foreach ($Drive in Get-FixedDriveRoots) {
        $Bases += (Join-Path $Drive "Program Files\Siemens")
        $Bases += (Join-Path $Drive "Program Files (x86)\Siemens")
        $Bases += (Join-Path $Drive "Siemens")
    }

    $Candidates = @()
    $Candidates += Get-Nx2512RegistryCandidates
    foreach ($Base in $Bases | Select-Object -Unique) {
        if (-not $Base) { continue }
        $Candidates += $Base
        foreach ($InstallName in $Script:Nx2512InstallNames) {
            $Candidates += (Join-Path $Base $InstallName)
            $Candidates += (Join-Path (Join-Path $Base $InstallName) "NXBIN")
        }
        if (Test-Path -LiteralPath $Base) {
            $Candidates += Get-ChildItem -LiteralPath $Base -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match "^(NX|NX\s*\d+|Siemens NX|Designcenter)" } |
                ForEach-Object { $_.FullName }
        }
    }

    $Candidates | Where-Object { $_ } | Select-Object -Unique
}

function Find-Nx2512RootsByGlobalSearch {
    param([string[]]$Require = @("RunJournal"))

    if ($env:NX2512_SKIP_GLOBAL_SEARCH -match "^(1|true|yes|on)$") {
        return @()
    }

    $Results = @()
    foreach ($Drive in Get-FixedDriveRoots) {
        $NxBinDirs = Get-ChildItem -LiteralPath $Drive -Directory -Filter "NXBIN" -Recurse -Force -ErrorAction SilentlyContinue |
            Select-Object -First 20
        foreach ($Dir in $NxBinDirs) {
            $Root = Resolve-Nx2512CandidateRoot -Candidate $Dir.FullName
            if (-not $Root) { continue }

            $Checks = @()
            if ($Require.Count -eq 0 -or $Require -contains "Any") { $Checks += (Join-Path $Root "NXBIN") }
            if ($Require -contains "RunJournal") { $Checks += (Join-Path $Root "NXBIN\run_journal.exe") }
            if ($Require -contains "Managed") { $Checks += (Join-Path $Root "NXBIN\managed\NXOpen.dll") }
            if ($Require -contains "Ugraf") { $Checks += (Join-Path $Root "NXBIN\ugraf.exe") }
            if (-not ($Checks | Where-Object { -not (Test-Path -LiteralPath $_) })) {
                $Results += $Root
            }
        }
    }
    $Results | Select-Object -Unique
}

function Resolve-Nx2512CandidateRoot {
    param([string]$Candidate)

    if (-not $Candidate) { return $null }

    $Resolved = Resolve-Path -LiteralPath $Candidate -ErrorAction SilentlyContinue
    if (-not $Resolved) { return $null }

    $Path = $Resolved.Path
    $Item = Get-Item -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $Item) { return $null }

    if ($Item.PSIsContainer) {
        $Leaf = Split-Path -Leaf $Path
        if ([string]::Equals($Leaf, "NXBIN", [System.StringComparison]::OrdinalIgnoreCase)) {
            return (Resolve-Path -LiteralPath (Split-Path -Parent $Path)).Path
        }
        if ((Test-Path -LiteralPath (Join-Path $Path "run_journal.exe")) -or
            (Test-Path -LiteralPath (Join-Path $Path "ugraf.exe")) -or
            (Test-Path -LiteralPath (Join-Path $Path "managed\NXOpen.dll"))) {
            return (Resolve-Path -LiteralPath (Split-Path -Parent $Path)).Path
        }
        return $Path
    }

    if ($Item.Name -in @("run_journal.exe", "ugraf.exe", "NXOpen.dll")) {
        $Parent = Split-Path -Parent $Path
        if ([string]::Equals((Split-Path -Leaf $Parent), "managed", [System.StringComparison]::OrdinalIgnoreCase)) {
            $Parent = Split-Path -Parent $Parent
        }
        if ([string]::Equals((Split-Path -Leaf $Parent), "NXBIN", [System.StringComparison]::OrdinalIgnoreCase)) {
            return (Resolve-Path -LiteralPath (Split-Path -Parent $Parent)).Path
        }
    }

    return $null
}

function Resolve-Nx2512Root {
    param(
        [string]$RequestedRoot,
        [string[]]$Require = @("RunJournal")
    )

    $Candidates = @()
    if ($RequestedRoot) { $Candidates += $RequestedRoot }
    if ($env:DC2512_ROOT) { $Candidates += $env:DC2512_ROOT }
    if ($env:DC2512_BIN) { $Candidates += $env:DC2512_BIN }
    if ($env:NX2512_ROOT) { $Candidates += $env:NX2512_ROOT }
    if ($env:UGII_BASE_DIR) { $Candidates += $env:UGII_BASE_DIR }
    if ($env:UGII_ROOT_DIR) { $Candidates += $env:UGII_ROOT_DIR }
    $Candidates += Get-Nx2512CommonCandidates

    foreach ($Candidate in $Candidates | Select-Object -Unique) {
        $Root = Resolve-Nx2512CandidateRoot -Candidate $Candidate
        if (-not $Root) { continue }
        $Checks = @()
        if ($Require.Count -eq 0 -or $Require -contains "Any") {
            $Checks += (Join-Path $Root "NXBIN")
        }
        if ($Require -contains "RunJournal") {
            $Checks += (Join-Path $Root "NXBIN\run_journal.exe")
        }
        if ($Require -contains "Managed") {
            $Checks += (Join-Path $Root "NXBIN\managed\NXOpen.dll")
        }
        if ($Require -contains "Ugraf") {
            $Checks += (Join-Path $Root "NXBIN\ugraf.exe")
        }

        $Missing = $Checks | Where-Object { -not (Test-Path -LiteralPath $_) }
        if (-not $Missing) {
            return $Root
        }
    }

    foreach ($Root in Find-Nx2512RootsByGlobalSearch -Require $Require) {
        return $Root
    }

    throw "NX/DC 2512 root not found. Set DC2512_BIN, DC2512_ROOT, NX2512_ROOT, UGII_BASE_DIR, UGII_ROOT_DIR, or pass -NxRoot. The resolver checked environment variables, registry install locations, common Siemens folders on fixed drives, and global NXBIN search."
}

function Add-ProcessPathPrefix {
    param([string]$PathToAdd)

    if (-not $PathToAdd -or -not (Test-Path -LiteralPath $PathToAdd)) {
        return
    }

    $Existing = @()
    if ($env:PATH) {
        $Existing = $env:PATH -split ";"
    }

    $AlreadyPresent = $false
    foreach ($Entry in $Existing) {
        if ($Entry -and ([string]::Equals($Entry.TrimEnd("\"), $PathToAdd.TrimEnd("\"), [System.StringComparison]::OrdinalIgnoreCase))) {
            $AlreadyPresent = $true
            break
        }
    }

    if (-not $AlreadyPresent) {
        $env:PATH = "$PathToAdd;$env:PATH"
    }
}

function Set-UserEnvironmentValue {
    param(
        [string]$Name,
        [string]$Value
    )

    [Environment]::SetEnvironmentVariable($Name, $Value, "User")
}

function Get-Nx2512GeneratedConfigRoot {
    $Base = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE "AppData\Local" }
    Join-Path $Base "Codex\NX2512"
}

function Update-Nx2512CustomDirectoryFile {
    param(
        [string]$CustomDirectoryFile,
        [string]$RuntimeRoot
    )

    $Parent = Split-Path -Parent $CustomDirectoryFile
    if (-not (Test-Path -LiteralPath $Parent)) {
        New-Item -ItemType Directory -Force -Path $Parent | Out-Null
    }

    $Content = @(
        "# Generated by Codex NX plugin. Do not edit by hand.",
        "# Points Siemens NX to the installed plugin runtime directory.",
        $RuntimeRoot
    )
    Set-Content -LiteralPath $CustomDirectoryFile -Value $Content -Encoding ASCII
}

function Initialize-Nx2512Environment {
    param(
        [string]$NxRoot,
        [string[]]$Require = @("RunJournal"),
        [switch]$PersistUser
    )

    $ResolvedRoot = Resolve-Nx2512Root -RequestedRoot $NxRoot -Require $Require
    $NxBin = Join-Path $ResolvedRoot "NXBIN"
    $RuntimeRoot = Join-Path $Script:Nx2512PluginRoot "nx_runtime"
    $CustomDirectoryFile = Join-Path (Get-Nx2512GeneratedConfigRoot) "custom_dirs.dat"
    $GeneratedScriptRoot = Join-Path $Script:Nx2512PluginRoot "scripts\generated"
    $ProjectRoot = if ($env:NX2512_PROJECT_ROOT) { $env:NX2512_PROJECT_ROOT } elseif ($env:DC2512_PROJECT_ROOT) { $env:DC2512_PROJECT_ROOT } else { $Script:Nx2512ProjectRoot }
    $LivePort = if ($env:NX2512_LIVE_PORT) { [int]$env:NX2512_LIVE_PORT } else { $Script:Nx2512LivePort }
    $AutoLaunch = if ($env:NX2512_AUTO_LAUNCH) { $env:NX2512_AUTO_LAUNCH } else { $Script:Nx2512AutoLaunch }
    $AutoLaunchTimeout = if ($env:NX2512_AUTO_LAUNCH_TIMEOUT) { $env:NX2512_AUTO_LAUNCH_TIMEOUT } else { $Script:Nx2512AutoLaunchTimeout }
    $RequireOnline = if ($env:NX2512_REQUIRE_ONLINE) { $env:NX2512_REQUIRE_ONLINE } else { $Script:Nx2512RequireOnline }
    $DeleteGeneratedScripts = if ($env:NX2512_DELETE_GENERATED_SCRIPTS) { $env:NX2512_DELETE_GENERATED_SCRIPTS } else { $Script:Nx2512DeleteGeneratedScripts }
    $CodexPython = if (Test-Path -LiteralPath $Script:CodexBundledPython) { $Script:CodexBundledPython } else { $env:CODEX_PYTHON }

    $env:NX2512_ROOT = $ResolvedRoot
    $env:DC2512_ROOT = $ResolvedRoot
    $env:DC2512_BIN = $NxBin
    $env:UGII_BASE_DIR = $ResolvedRoot
    $env:UGII_ROOT_DIR = $NxBin
    $env:UGII_CUSTOM_DIRECTORY_FILE = $CustomDirectoryFile
    $env:NX2512_PLUGIN_ROOT = $Script:Nx2512PluginRoot
    $env:NX2512_PROJECT_ROOT = $ProjectRoot
    $env:DC2512_PROJECT_ROOT = $ProjectRoot
    $env:NX2512_LIVE_PORT = [string]$LivePort
    $env:NX2512_AUTO_LAUNCH = $AutoLaunch
    $env:NX2512_AUTO_LAUNCH_TIMEOUT = $AutoLaunchTimeout
    $env:NX2512_REQUIRE_ONLINE = $RequireOnline
    $env:NX2512_DELETE_GENERATED_SCRIPTS = $DeleteGeneratedScripts
    $env:NX2512_GENERATED_SCRIPT_ROOT = $GeneratedScriptRoot
    if ($CodexPython) {
        $env:CODEX_PYTHON = $CodexPython
    }
    Update-Nx2512CustomDirectoryFile -CustomDirectoryFile $CustomDirectoryFile -RuntimeRoot $RuntimeRoot
    Add-ProcessPathPrefix -PathToAdd $NxBin

    if ($PersistUser) {
        Set-UserEnvironmentValue -Name "NX2512_ROOT" -Value $ResolvedRoot
        Set-UserEnvironmentValue -Name "DC2512_ROOT" -Value $ResolvedRoot
        Set-UserEnvironmentValue -Name "DC2512_BIN" -Value $NxBin
        Set-UserEnvironmentValue -Name "UGII_BASE_DIR" -Value $ResolvedRoot
        Set-UserEnvironmentValue -Name "UGII_ROOT_DIR" -Value $NxBin
        Set-UserEnvironmentValue -Name "UGII_CUSTOM_DIRECTORY_FILE" -Value $CustomDirectoryFile
        Set-UserEnvironmentValue -Name "NX2512_PLUGIN_ROOT" -Value $Script:Nx2512PluginRoot
        Set-UserEnvironmentValue -Name "NX2512_PROJECT_ROOT" -Value $ProjectRoot
        Set-UserEnvironmentValue -Name "DC2512_PROJECT_ROOT" -Value $ProjectRoot
        Set-UserEnvironmentValue -Name "NX2512_LIVE_PORT" -Value ([string]$LivePort)
        Set-UserEnvironmentValue -Name "NX2512_AUTO_LAUNCH" -Value $AutoLaunch
        Set-UserEnvironmentValue -Name "NX2512_AUTO_LAUNCH_TIMEOUT" -Value $AutoLaunchTimeout
        Set-UserEnvironmentValue -Name "NX2512_REQUIRE_ONLINE" -Value $RequireOnline
        Set-UserEnvironmentValue -Name "NX2512_DELETE_GENERATED_SCRIPTS" -Value $DeleteGeneratedScripts
        Set-UserEnvironmentValue -Name "NX2512_GENERATED_SCRIPT_ROOT" -Value $GeneratedScriptRoot
        if ($CodexPython) {
            Set-UserEnvironmentValue -Name "CODEX_PYTHON" -Value $CodexPython
        }
    }

    [pscustomobject]@{
        nxRoot = $ResolvedRoot
        nxBin = $NxBin
        runJournal = Join-Path $NxBin "run_journal.exe"
        ugraf = Join-Path $NxBin "ugraf.exe"
        managed = Join-Path $NxBin "managed"
        pythonModules = Join-Path $NxBin "python"
        pluginRoot = $Script:Nx2512PluginRoot
        projectRoot = $ProjectRoot
        runtimeRoot = $RuntimeRoot
        customDirectoryFile = $CustomDirectoryFile
        generatedScriptRoot = $GeneratedScriptRoot
        livePort = $LivePort
        autoLaunch = $AutoLaunch
        autoLaunchTimeout = $AutoLaunchTimeout
        requireOnline = $RequireOnline
        deleteGeneratedScripts = $DeleteGeneratedScripts
        codexPython = $CodexPython
    }
}
