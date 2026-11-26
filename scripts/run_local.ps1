# Run IdeaForm locally on Windows without Docker.
#
#   powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1            # first run sets everything up
#   powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1 -Stop      # stop the database
#
# What it does, skipping any step that is already done:
#   1. creates .venv and installs backend requirements (CPU-only PyTorch)
#   2. installs frontend packages
#   3. starts the IdeaForm PostgreSQL on localhost:5434 (scripts\dev_db.ps1)
#   4. applies database migrations
#   5. opens two windows: API on http://localhost:8000 and web app on http://localhost:3000
#
# .env must hold DATABASE_URL=postgresql+psycopg://ideaform:ideaform@localhost:5434/ideaform,
# JOBS_INLINE=true, a JWT_SECRET of 32+ characters and GROQ_API_KEY.
param([switch]$Stop)
$ErrorActionPreference = "Continue"

$root = Split-Path $PSScriptRoot -Parent
$python = Join-Path $root ".venv\Scripts\python.exe"
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if ($Stop) {
    & (Join-Path $PSScriptRoot "dev_db.ps1") -Stop
    Write-Host "Close the 'IdeaForm API' and 'IdeaForm web' windows to stop those."
    exit 0
}

function Assert-Ok([string]$What) {
    if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: $What" -ForegroundColor Red; exit 1 }
}

if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Host "No .env found. Copy .env.example to .env and fill it in (see the header of this script)." -ForegroundColor Red
    exit 1
}

# 1. Python environment
if (-not (Test-Path $python)) {
    Write-Host "Creating Python virtual environment (.venv) ..."
    py -3.11 -m venv (Join-Path $root ".venv"); Assert-Ok "create .venv (needs Python 3.11: py -3.11)"
}
& $python -c "import fastapi, sentence_transformers" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing backend requirements (first run downloads CPU PyTorch, ~130 MB) ..."
    & $python -m pip install --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple torch
    Assert-Ok "install torch"
    & $python -m pip install -r (Join-Path $backend "requirements.txt"); Assert-Ok "install requirements"
}

# 2. Frontend packages
if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Installing frontend packages ..."
    Push-Location $frontend; npm install; $code = $LASTEXITCODE; Pop-Location
    if ($code -ne 0) { Write-Host "FAILED: npm install" -ForegroundColor Red; exit 1 }
}

# 3. Database
& (Join-Path $PSScriptRoot "dev_db.ps1"); Assert-Ok "start database"

# 4. Migrations
Push-Location $backend
& (Join-Path $root ".venv\Scripts\alembic.exe") upgrade head; $code = $LASTEXITCODE
Pop-Location
if ($code -ne 0) { Write-Host "FAILED: alembic upgrade head" -ForegroundColor Red; exit 1 }

# 5. API and web app, each in its own window
foreach ($port in 8000, 3000) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "Port $port is already in use; close whatever runs there first (Get-NetTCPConnection -LocalPort $port)." -ForegroundColor Yellow
    }
}
Start-Process powershell -WorkingDirectory $backend -ArgumentList @(
    "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'IdeaForm API'; & '$python' -m uvicorn app.main:app --reload --port 8000"
)
Start-Process powershell -WorkingDirectory $frontend -ArgumentList @(
    "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'IdeaForm web'; npm run dev"
)

Write-Host ""
Write-Host "IdeaForm is starting:" -ForegroundColor Green
Write-Host "  Web app  http://localhost:3000"
Write-Host "  API      http://localhost:8000/docs   (health: /health/ready)"
