<#
.SYNOPSIS
  Format C++ and Python sources in this repository.

.PARAMETER SkipCpp
  Do not run clang-format.

.PARAMETER SkipPython
  Do not run ruff on the Python SDK.

.PARAMETER Check
  Use clang-format --dry-run --Werror and ruff format --check

.EXAMPLE
  .\format.ps1
  .\format.ps1 -Check
#>
param(
    [switch] $SkipCpp,
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

function Get-CppFormatFiles {
    param([string] $RepoRoot)

    $roots = @(
        (Join-Path $RepoRoot 'plugin\src'),
        (Join-Path $RepoRoot 'plugin\tests')
    )
    $files = @()
    foreach ($r in $roots) {
        if (-not (Test-Path -LiteralPath $r)) { continue }
        $files += Get-ChildItem -Path $r -Recurse -File -Include '*.cpp', '*.h', '*.hpp' -ErrorAction SilentlyContinue
    }
    return ($files | Sort-Object FullName -Unique)
}

try {
    $RepoRoot = $PSScriptRoot

    if (-not $SkipCpp) {
        $clangFormat = Get-Command clang-format -ErrorAction SilentlyContinue
        if (-not $clangFormat) {
            Write-Host "clang-format not on PATH; skipping C++ (install LLVM or use -SkipCpp)." -ForegroundColor Yellow
        }
        else {
            $cppFiles = Get-CppFormatFiles -RepoRoot $RepoRoot
            if ($cppFiles.Count -eq 0) {
                Write-Host "No C++ sources found under plugin/src or plugin/tests."
            }
            else {
                Write-Host "`n==> clang-format ($($cppFiles.Count) files)"
                if ($Check) {
                    Invoke-Checked -Exe $clangFormat.Source -Arguments (@('--dry-run', '--Werror') + $cppFiles.FullName)
                }
                else {
                    Invoke-Checked -Exe $clangFormat.Source -Arguments (@('-i') + $cppFiles.FullName)
                }
            }
        }
    }

    if (-not $SkipPython) {
        $pyRoot = Join-Path $RepoRoot 'sdk\py'
        if (-not (Test-Path -LiteralPath $pyRoot)) {
            Write-Host "Python SDK path not found: $pyRoot"
        }
        else {
            $ruff = Get-Command ruff -ErrorAction SilentlyContinue
            if (-not $ruff) {
                Write-Host "ruff not on PATH; install dev deps in sdk/py (e.g. pip install -e `".[dev]`") or use -SkipPython." -ForegroundColor Yellow
            }
            else {
                Write-Host "`n==> ruff format (sdk/py)"
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
