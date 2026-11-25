# Dump the Ideaform database to backups\ideaform_<timestamp>.dump (custom format).
# Restore with: pg_restore -h localhost -U postgres -d <db> --clean backups\<file>.dump
#
#   powershell -ExecutionPolicy Bypass -File scripts\backup_db.ps1 -Database " ideaform"

param(
    [string]$Database = "ideaform",
    [string]$User = "postgres",
    [string]$DbHost = "localhost",
    [int]$Port = 5432,
    [string]$PgBin = "C:\Program Files\PostgreSQL\18\bin"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force $outDir | Out-Null
$file = Join-Path $outDir ("ideaform_{0}.dump" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

# pg_dump asks for the password, or reads PGPASSWORD / %APPDATA%\postgresql\pgpass.conf
& "$PgBin\pg_dump.exe" -h $DbHost -p $Port -U $User -F c -f $file $Database
Write-Host "Saved $file"
