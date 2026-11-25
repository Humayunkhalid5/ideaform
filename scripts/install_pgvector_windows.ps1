# Build and install pgvector for a local Windows PostgreSQL (needed for Phase 2 retrieval).
#
# Requirements: Visual Studio 2022 (or Build Tools) with "Desktop development with C++", git.
# Run from PowerShell opened *as Administrator* (copying into Program Files needs it):
#   powershell -ExecutionPolicy Bypass -File scripts\install_pgvector_windows.ps1
# Then: backend\.venv\Scripts\python scripts\enable_pgvector.py
#
# Source: the official repository https://github.com/pgvector/pgvector

param(
    [string]$PgRoot = "C:\Program Files\PostgreSQL\18",
    [string]$Version = "v0.8.1"
)

$ErrorActionPreference = "Stop"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw "Run this script from PowerShell opened as Administrator." }
if (-not (Test-Path "$PgRoot\include\server")) {
    throw "PostgreSQL headers not found under $PgRoot. Pass -PgRoot for your install."
}

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vcvars = & $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -find "VC\Auxiliary\Build\vcvars64.bat" | Select-Object -First 1
if (-not $vcvars) { throw "Visual Studio C++ build tools not found (vcvars64.bat)." }

$work = Join-Path $env:TEMP "pgvector-build"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
git clone --quiet --depth 1 --branch $Version https://github.com/pgvector/pgvector.git $work
if ($LASTEXITCODE -ne 0) { throw "git clone failed" }

cmd /c "`"$vcvars`" >nul && cd /d `"$work`" && set `"PGROOT=$PgRoot`" && nmake /NOLOGO /F Makefile.win && nmake /NOLOGO /F Makefile.win install"
if ($LASTEXITCODE -ne 0) { throw "pgvector build/install failed" }

Write-Host ""
Write-Host "pgvector $Version installed into $PgRoot (no restart needed)."
Write-Host "Next: backend\.venv\Scripts\python scripts\enable_pgvector.py"
