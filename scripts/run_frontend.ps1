# PowerShell Script to Run Frontend
# Run as: .\scripts\run_frontend.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ILLIP AI - Frontend Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python exists
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

Write-Host "Starting frontend server..." -ForegroundColor Yellow
Write-Host "Frontend will be available at: http://localhost:8080" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Start Python's built-in HTTP server
Push-Location frontend
python -m http.server 8080 --directory .

# Alternative: use PowerShell's built-in web server if available
# $port = 8080
# $address = "127.0.0.1"
# $listener = New-Object System.Net.HttpListener
# $listener.Prefixes.Add("http://$address`:$port/")
# $listener.Start()
# Write-Host "Listening on http://$address`:$port" -ForegroundColor Cyan
