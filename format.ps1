<#
.SYNOPSIS
  Format Rust plugin and Python client sources in this repository.

.PARAMETER SkipRust
  Do not run cargo fmt.

.PARAMETER SkipPython
  Do not run ruff on the Python client.

.PARAMETER Check
  Use cargo fmt --check and ruff format --check

.EXAMPLE
  .\format.ps1
  .\format.ps1 -Check
#>
param(
    [switch] $SkipRust,
    [switch] $SkipPython,
    [switch] $Check
)

$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param(
        [Parameter(Mandatory)]
        [string] $Exe,

        [string[]] $Arguments
    )

    $line = "$Exe $($Arguments -join ' ')"
    Write-Host "-> $line"
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command FAILED (exit $LASTEXITCODE): $line"
    }
}

try {
    $RepoRoot = $PSScriptRoot
    $PluginDir = Join-Path $RepoRoot 'plugin'

    if (-not $SkipRust) {
        $cargo = Get-Command cargo -ErrorAction SilentlyContinue
        if (-not $cargo) {
            Write-Host "cargo not on PATH; skipping Rust (install rustup or use -SkipRust)." -ForegroundColor Yellow
        }
        elseif (-not (Test-Path -LiteralPath $PluginDir)) {
            Write-Host "Plugin directory not found: $PluginDir"
        }
        else {
            Write-Host "`n==> cargo fmt"
            Push-Location -LiteralPath $PluginDir
            try {
                $fmtArgs = @('fmt')
                if ($Check) {
                    $fmtArgs += @('--', '--check')
                }
                Invoke-Checked -Exe $cargo.Source -Arguments $fmtArgs
            }
            finally {
                Pop-Location
            }
        }
    }

    if (-not $SkipPython) {
        $pyRoot = Join-Path $RepoRoot 'python'
        if (-not (Test-Path -LiteralPath $pyRoot)) {
            Write-Host "Python package path not found: $pyRoot"
        }
        else {
            $ruff = Get-Command ruff -ErrorAction SilentlyContinue
            if (-not $ruff) {
                Write-Host "ruff not on PATH; install dev deps (e.g. uv sync --extra dev) or use -SkipPython." -ForegroundColor Yellow
            }
            else {
                Write-Host "`n==> ruff format"
                if ($Check) {
                    Invoke-Checked -Exe $ruff.Source -Arguments @('format', '--check', $pyRoot)
                    Invoke-Checked -Exe $ruff.Source -Arguments @('check', $pyRoot)
                }
                else {
                    Invoke-Checked -Exe $ruff.Source -Arguments @('format', $pyRoot)
                    Invoke-Checked -Exe $ruff.Source -Arguments @('check', '--fix', $pyRoot)
                }
            }
        }
    }

    Write-Host "`n==> Done."
}
catch {
    throw
}
