<#
.SYNOPSIS
  Build the Margrete RPC Rust plugin (cdylib).

.PARAMETER Configuration
  Debug or Release (maps to Cargo's dev / release profiles).

.PARAMETER SkipVcVars
  Skip vcvars64 import when you already opened a "x64 Native Tools" or VS dev shell.

.PARAMETER Test
  Run `cargo test` after a successful build.

.PARAMETER Publish
  Copy margrete_rpc.dll and margrete_rpc.ini into repo-root publish/ for manual install.

.PARAMETER InitSubmodules
  Run `git submodule update --init --recursive` before the build (Margrete SDK headers).

.EXAMPLE
  .\build.ps1
  .\build.ps1 -Configuration Debug -Test
  .\build.ps1 -Publish
#>
param(
    [ValidateSet('Debug', 'Release')]
    [string] $Configuration = 'Release',

    [switch] $SkipVcVars,
    [switch] $Test,
    [switch] $Publish,
    [switch] $InitSubmodules
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

function Import-VcVars64 {
    Write-Host "`n==> Importing vcvars64 environment ..."

    $vswhere = Join-Path "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer" 'vswhere.exe'
    if (-not (Test-Path $vswhere)) {
        Write-Host "    vswhere.exe not found - install Visual Studio or open a VS dev shell and use -SkipVcVars."
        return
    }

    $vsPath = & $vswhere -latest -products * -property installationPath -nologo
    if (-not $vsPath) {
        Write-Host "    Visual Studio installation not found."
        return
    }

    $vcvars = Join-Path $vsPath 'VC\Auxiliary\Build\vcvars64.bat'
    if (-not (Test-Path $vcvars)) {
        Write-Host "    vcvars64.bat not found in $vsPath."
        return
    }

    try {
        $output = cmd /c "`"$vcvars`" 2>&1 && set" | Out-String
        $output -split "`r`n" | ForEach-Object {
            if ($_ -match '^([^=]+)=(.*)') {
                [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
            }
        }
        Write-Host "    VCVARS64 environment loaded."
    }
    catch {
        Write-Host "Failed to load VCVARS64: $_" -ForegroundColor Red
    }
}

try {
    if (-not $SkipVcVars) {
        Import-VcVars64
    }

    $RepoRoot = $PSScriptRoot
    $PluginDir = Join-Path $RepoRoot 'plugin'
    $CargoProfile = if ($Configuration -eq 'Release') { 'release' } else { 'debug' }
    $TargetDir = Join-Path $PluginDir "target\$CargoProfile"

    if (-not (Test-Path -LiteralPath $PluginDir)) {
        throw "Plugin directory not found: $PluginDir"
    }

    if ($InitSubmodules) {
        Write-Host "`n==> git submodule update --init --recursive"
        Invoke-Checked -Exe 'git' -Arguments @('-C', $RepoRoot, 'submodule', 'update', '--init', '--recursive')
    }

    Push-Location -LiteralPath $PluginDir
    try {
        if ($Test) {
            Write-Host "`n==> cargo test"
            Invoke-Checked -Exe 'cargo' -Arguments @('test')
        }

        Write-Host "`n==> cargo build --$CargoProfile"
        if ($CargoProfile -eq 'release') {
            Invoke-Checked -Exe 'cargo' -Arguments @('build', '--release')
        }
        else {
            Invoke-Checked -Exe 'cargo' -Arguments @('build')
        }
    }
    finally {
        Pop-Location
    }

    if ($Publish) {
        $dll = Join-Path $TargetDir 'margrete_rpc.dll'
        $ini = Join-Path $TargetDir 'margrete_rpc.ini'
        $installReadme = Join-Path $PluginDir 'config\README-install.txt'
        if (-not (Test-Path -LiteralPath $dll)) { throw "Could not find $dll" }
        if (-not (Test-Path -LiteralPath $ini)) { throw "Could not find $ini" }
        if (-not (Test-Path -LiteralPath $installReadme)) {
            throw "Install README not found: $installReadme"
        }

        $PublishDir = Join-Path $RepoRoot 'publish'
        Write-Host "`n==> Publishing to $PublishDir"
        Remove-Item $PublishDir -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Path $PublishDir | Out-Null
        Copy-Item -LiteralPath $dll -Destination (Join-Path $PublishDir 'margrete_rpc.dll')
        Copy-Item -LiteralPath $ini -Destination (Join-Path $PublishDir 'margrete_rpc.ini')
        Copy-Item -LiteralPath $installReadme -Destination (Join-Path $PublishDir 'README-install.txt')
        Write-Host "    Copied DLL, INI, and install README."
    }

    Write-Host "`n==> Done."
}
catch {
    throw
}
