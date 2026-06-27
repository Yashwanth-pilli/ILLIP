# PowerShell Script to Start Both Backend and Frontend
# Run as: .\scripts\dev_start.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ILLIP AI - Development Server (Full Stack)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "ERROR: Virtual environment not found." -ForegroundColor Red
    Write-Host "Run .\scripts\setup.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

if (-not $?) {
    Write-Host "ERROR: Failed to activate virtual environment" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Backend..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "API: http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host ""

# Start backend in a new window
$backendJob = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000" `
    -WindowStyle Normal `
    -PassThru

Write-Host "✓ Backend started (PID: $($backendJob.Id))" -ForegroundColor Green

# Wait for backend to start
Write-Host "Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Frontend..." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:8080" -ForegroundColor Green
Write-Host ""

# Start frontend in a new window
$frontendJob = Start-Process -FilePath "python" `
    -ArgumentList "-m", "http.server", "8080", "--directory", ".\frontend\" `
    -WindowStyle Normal `
    -PassThru

Write-Host "✓ Frontend started (PID: $($frontendJob.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Both servers running!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services:" -ForegroundColor Yellow
Write-Host "  Backend (API):  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  API Docs:       http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  Frontend (UI):  http://localhost:8080" -ForegroundColor White
Write-Host ""
Write-Host "To stop servers, close these windows or press Ctrl+C" -ForegroundColor Gray
Write-Host ""

# Wait for any key to exit
Write-Host "Press any key to stop both servers..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host ""
Write-Host "Stopping servers..." -ForegroundColor Yellow

try {
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Backend stopped" -ForegroundColor Green
} catch { }

try {
    Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Frontend stopped" -ForegroundColor Green
} catch { }

Write-Host "Done!" -ForegroundColor Cyan
