# Build and install pgvector for a local Windows PostgreSQL (needed from Phase 2).
#
# Requirements: Visual Studio 2022 with "Desktop development with C++", git.
# Run from an *Administrator* "x64 Native Tools Command Prompt for VS 2022" ->
#   powershell -ExecutionPolicy Bypass -File scripts\install_pgvector_windows.ps1
# Then: backend\.venv\Scripts\python scripts\enable_pgvector.py
#
# Source: the official repository https://github.com/pgvector/pgvector

param(
    [string]$PgRoot = "C:\Program Files\PostgreSQL\18",
    [string]$Version = "v0.8.1"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command nmake -ErrorAction SilentlyContinue)) {
    throw "nmake not found. Open the 'x64 Native Tools Command Prompt for VS 2022' as Administrator first."
}
if (-not (Test-Path "$PgRoot\include\server")) {
    throw "PostgreSQL headers not found under $PgRoot. Pass -PgRoot for your install."
}

$work = Join-Path $env:TEMP "pgvector-build"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
git clone --depth 1 --branch $Version https://github.com/pgvector/pgvector.git $work

Push-Location $work
try {
    $env:PGROOT = $PgRoot
    nmake /NOLOGO /F Makefile.win
    nmake /NOLOGO /F Makefile.win install
} finally {
    Pop-Location
}

Write-Host "pgvector $Version installed into $PgRoot. Restart is not required."
Write-Host "Next: backend\.venv\Scripts\python scripts\enable_pgvector.py"
