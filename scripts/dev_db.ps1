# Local PostgreSQL for IdeaForm (Windows, no Docker).
#
# Creates a private cluster in .pgdata\ the first time (user/password ideaform/ideaform,
# database "ideaform"), then starts it on localhost:5434. It uses the binaries of an
# installed PostgreSQL but never touches that install's own server or data.
#
#   powershell -ExecutionPolicy Bypass -File scripts\dev_db.ps1          # start (creates if needed)
#   powershell -ExecutionPolicy Bypass -File scripts\dev_db.ps1 -Stop    # stop
param(
    [int]$Port = 5434,
    [switch]$Stop
)
# Native tools write notices to stderr; failures are checked through $LASTEXITCODE.
$ErrorActionPreference = "Continue"

$root = Split-Path $PSScriptRoot -Parent
$data = Join-Path $root ".pgdata"
$log = Join-Path $root ".pgdata.log"
$user = "ideaform"
$password = "ideaform"
$database = "ideaform"

function Find-PgBin {
    param([string]$Major)
    $installs = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\pg_ctl.exe" -ErrorAction SilentlyContinue |
        ForEach-Object { $_.Directory } |
        Sort-Object { [int]($_.Parent.Name -replace '\D.*$', '') } -Descending
    if ($Major) { $installs = $installs | Where-Object { $_.Parent.Name -eq $Major } }
    $hit = $installs | Select-Object -First 1
    if (-not $hit) {
        $want = if ($Major) { "PostgreSQL $Major" } else { "PostgreSQL" }
        throw "$want is not installed under C:\Program Files\PostgreSQL. Install it from https://www.postgresql.org/download/windows/"
    }
    return $hit.FullName
}

# A cluster only runs on the major version that created it.
$major = if (Test-Path (Join-Path $data "PG_VERSION")) { (Get-Content (Join-Path $data "PG_VERSION")).Trim() } else { $null }
$bin = Find-PgBin $major
$pgCtl = Join-Path $bin "pg_ctl.exe"

& $pgCtl status -D $data *> $null
$running = $LASTEXITCODE -eq 0

if ($Stop) {
    if ($running) { & $pgCtl stop -D $data -m fast } else { Write-Host "IdeaForm database is not running." }
    exit 0
}

if (-not (Test-Path (Join-Path $data "PG_VERSION"))) {
    Write-Host "Creating IdeaForm database cluster in $data ..."
    $pwFile = New-TemporaryFile
    try {
        Set-Content -Path $pwFile -Value $password -NoNewline -Encoding ascii
        & (Join-Path $bin "initdb.exe") -D $data -U $user --pwfile=$pwFile --auth=scram-sha-256 --encoding=UTF8 --locale=C | Out-Host
        if ($LASTEXITCODE -ne 0) { throw "initdb failed" }
    } finally {
        Remove-Item $pwFile -Force
    }
}

if (-not $running) {
    # Own hidden console: the server outlives this terminal, and its handles are not
    # tied to a pipe of ours (that would never close).
    $proc = Start-Process -FilePath $pgCtl -WindowStyle Hidden -PassThru -ArgumentList @(
        "start", "-D", "`"$data`"", "-l", "`"$log`"", "-w", "-o", "`"-p $Port -c listen_addresses=localhost`""
    )
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0) { throw "PostgreSQL did not start; see $log" }
}

$env:PGPASSWORD = $password
$exists = & (Join-Path $bin "psql.exe") -h localhost -p $Port -U $user -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$database'"
if ($exists -ne "1") {
    & (Join-Path $bin "createdb.exe") -h localhost -p $Port -U $user $database
    if ($LASTEXITCODE -ne 0) { throw "createdb failed" }
    Write-Host "Created database '$database'."
}
Write-Host "IdeaForm database ready: postgresql+psycopg://${user}:${password}@localhost:$Port/$database"
