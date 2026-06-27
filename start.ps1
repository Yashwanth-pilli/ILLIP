# ILLIP AI Application Launcher
# Verifies environment and activates virtualenv before booting FastAPI uvicorn

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       Launching ILLIP AI Server...       " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$venvPath = Join-Path $PSScriptRoot ".venv"
$envPath = Join-Path $PSScriptRoot ".env"

# 1. Verify environment configuration has been built
if (-not (Test-Path $venvPath)) {
    Write-Host "[!] Error: Virtual environment (.venv) not found!" -ForegroundColor Red
    Write-Host "    Please run setup.bat first to build the environment." -ForegroundColor Yellow
    Exit 1
}

if (-not (Test-Path $envPath)) {
    Write-Host "[!] Error: .env configuration file not found!" -ForegroundColor Red
    Write-Host "    Please run setup.bat first to configure settings." -ForegroundColor Yellow
    Exit 1
}

# 2. Start Application Server
Write-Host "[*] Activating virtual environment..." -ForegroundColor Cyan
$pythonExec = Join-Path $venvPath "Scripts\python.exe"

Write-Host "[*] Starting FastAPI uvicorn web server..." -ForegroundColor Cyan
$localIP = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias "*" | Where-Object { $_.IPAddress -notmatch "^(127|169)" } | Select-Object -First 1).IPAddress
Write-Host "[+] Local URL:   http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "[+] Network URL: http://${localIP}:8000  (other devices on same WiFi)" -ForegroundColor Green
Write-Host "[+] API Docs:    http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "[*] Press Ctrl+C to terminate the server." -ForegroundColor Yellow
Write-Host ""

# Run uvicorn — 0.0.0.0 makes it accessible from other devices on the network
& $pythonExec -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
