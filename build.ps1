<#
.SYNOPSIS
  Configure and build the Margrete RPC C++ plugin.

.PARAMETER Configuration
  Debug or Release (passed to cmake --build / ctest).

.PARAMETER SkipVcVars
  Skip vcvars64 import when you already opened a "x64 Native Tools" or VS dev shell.

.PARAMETER Test
  Run plugin_tests via ctest after a successful build.

.PARAMETER Publish
  Copy margrete-rpc.dll and margrete-rpc.ini into repo-root publish/ for manual install.

.PARAMETER VcpkgRoot
  vcpkg installation root. Defaults to $env:VCPKG_ROOT.

.PARAMETER InitSubmodules
  Run `git submodule update --init --recursive` before CMake configure.

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
    [string] $VcpkgRoot = $env:VCPKG_ROOT,
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

function Find-BuiltDll {
    param([string] $BuildDir)

    $candidates = @(
        (Join-Path $BuildDir 'margrete-rpc.dll'),
        (Join-Path $BuildDir "$Configuration\margrete-rpc.dll")
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return (Resolve-Path -LiteralPath $p).Path }
    }

    $found = Get-ChildItem -Path $BuildDir -Recurse -Filter 'margrete-rpc.dll' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    return $null
}

function Find-BuiltIni {
    param([string] $BuildDir)

    $candidates = @(
        (Join-Path $BuildDir 'margrete-rpc.ini'),
        (Join-Path $BuildDir "$Configuration\margrete-rpc.ini")
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return (Resolve-Path -LiteralPath $p).Path }
    }

    $found = Get-ChildItem -Path $BuildDir -Recurse -Filter 'margrete-rpc.ini' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    return $null
}

try {
    if (-not $SkipVcVars) {
        Import-VcVars64
    }

    $RepoRoot = $PSScriptRoot
    $PluginDir = Join-Path $RepoRoot 'plugin'
    $BuildDir = Join-Path $PluginDir 'build'

    if (-not (Test-Path -LiteralPath $PluginDir)) {
        throw "Plugin directory not found: $PluginDir"
    }

    if ([string]::IsNullOrWhiteSpace($VcpkgRoot)) {
        throw "vcpkg root not set. Set VCPKG_ROOT or pass -VcpkgRoot 'D:\path\to\vcpkg'."
    }

    $toolchain = Join-Path $VcpkgRoot 'scripts\buildsystems\vcpkg.cmake'
    if (-not (Test-Path -LiteralPath $toolchain)) {
        throw "vcpkg toolchain file not found: $toolchain"
    }

    if ($InitSubmodules) {
        Write-Host "`n==> git submodule update --init --recursive"
        Invoke-Checked -Exe 'git' -Arguments @('-C', $RepoRoot, 'submodule', 'update', '--init', '--recursive')
    }

    Write-Host "`n==> CMake configure ($Configuration)"
    Invoke-Checked -Exe 'cmake' -Arguments @(
        '-B', $BuildDir,
        '-S', $PluginDir,
        "-DCMAKE_TOOLCHAIN_FILE=$toolchain"
    )

    Write-Host "`n==> CMake build ($Configuration)"
    Invoke-Checked -Exe 'cmake' -Arguments @('--build', $BuildDir, '--config', $Configuration)

    if ($Test) {
        Write-Host "`n==> ctest ($Configuration)"
        Invoke-Checked -Exe 'ctest' -Arguments @('--test-dir', $BuildDir, '-C', $Configuration, '--output-on-failure')
    }

    if ($Publish) {
        $dll = Find-BuiltDll -BuildDir $BuildDir
        $ini = Find-BuiltIni -BuildDir $BuildDir
        if (-not $dll) { throw "Could not find margrete-rpc.dll under $BuildDir" }
        if (-not $ini) { throw "Could not find margrete-rpc.ini under $BuildDir" }

        $PublishDir = Join-Path $RepoRoot 'publish'
        Write-Host "`n==> Publishing to $PublishDir"
        Remove-Item $PublishDir -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Path $PublishDir | Out-Null
        Copy-Item -LiteralPath $dll -Destination (Join-Path $PublishDir 'margrete-rpc.dll')
        Copy-Item -LiteralPath $ini -Destination (Join-Path $PublishDir 'margrete-rpc.ini')
        Write-Host "    Copied DLL and INI."
    }

    Write-Host "`n==> Done."
}
catch {
    throw
}
