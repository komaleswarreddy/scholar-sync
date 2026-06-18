# Start ScholarSync backend (FastAPI) and frontend (Next.js) in separate terminals.
# Usage: .\scripts\start-dev.ps1
# Or from repo root: pnpm dev:stack

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"
$WebDir = Join-Path $Root "apps\web"

if (-not (Test-Path $Python)) {
    Write-Error "Python venv not found at $Python. Run: pip install -r requirements.txt (from repo root with venv active)."
    exit 1
}

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Error "pnpm is not installed or not on PATH."
    exit 1
}

Write-Host "Starting ScholarSync dev stack..."
Write-Host "  Backend:  http://localhost:8000"
Write-Host "  Frontend: http://localhost:3000"
Write-Host ""

$backendCmd = @"
Set-Location '$Root'
`$Host.UI.RawUI.WindowTitle = 'ScholarSync API (8000)'
Write-Host 'ScholarSync API — http://localhost:8000' -ForegroundColor Green
& '$Python' -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
"@

$frontendCmd = @"
Set-Location '$WebDir'
`$Host.UI.RawUI.WindowTitle = 'ScholarSync Web (3000)'
`$env:WATCHPACK_POLLING = 'true'
Write-Host 'ScholarSync Web — http://localhost:3000' -ForegroundColor Green
pnpm exec next dev
"@

Start-Process powershell -ArgumentList "-NoExit", "-NoLogo", "-Command", $backendCmd
Start-Sleep -Seconds 1
Start-Process powershell -ArgumentList "-NoExit", "-NoLogo", "-Command", $frontendCmd

Write-Host "Launched API and Web in new terminal windows." -ForegroundColor Cyan
