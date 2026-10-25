param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "nx_env.ps1")
$Server = Join-Path $ScriptDir "nx_mcp_server.py"

function Test-Python {
    param([string]$Command, [string[]]$Args)
    try {
        $probe = & $Command @Args -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $probe) {
            return $true
        }
    }
    catch {
        return $false
    }
    return $false
}

$Candidates = @()
if ($env:CODEX_PYTHON) {
    $Candidates += @{ Command = $env:CODEX_PYTHON; Args = @() }
}
if ((Test-Path -LiteralPath $Script:CodexBundledPython) -and $env:CODEX_PYTHON -ne $Script:CodexBundledPython) {
    $Candidates += @{ Command = $Script:CodexBundledPython; Args = @() }
}
$Candidates += @{ Command = "python.exe"; Args = @() }
$Candidates += @{ Command = "py.exe"; Args = @("-3") }

foreach ($Candidate in $Candidates) {
    if (Test-Python -Command $Candidate.Command -Args $Candidate.Args) {
        & $Candidate.Command @($Candidate.Args + @($Server))
        exit $LASTEXITCODE
    }
}

Write-Error "No working Python runtime found. Set CODEX_PYTHON to python.exe and retry."
exit 1
