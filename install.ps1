# ILLIP AI - one-line installer for Windows
# Run: irm https://raw.githubusercontent.com/Yashwanth-pilli/ILLIP/main/install.ps1 | iex

param(
    [string]$RepoUrl  = "https://github.com/Yashwanth-pilli/ILLIP.git",
    [string]$InstallDir = ".\illip_ai"
)

$ErrorActionPreference = "Stop"

Write-Host "=== ILLIP AI Installer ===" -ForegroundColor Cyan
Write-Host "This installer will:"
Write-Host "  1) Download ILLIP source code from GitHub (or update an existing install)"
Write-Host "  2) Hand off to guided setup, which explains and ASKS before each piece:"
Write-Host "     - Python 3.12          -> runs ILLIP itself"
Write-Host "     - Python packages      -> web app, memory, agents"
Write-Host "     - Ollama + local model -> free private AI chat, works offline (sized to your hardware)"
Write-Host "     - Playwright (optional)-> lets ILLIP browse websites for you"
Write-Host "     - OmniRoute (optional) -> free big cloud models via /cloud, zero load on your PC"
Write-Host "  Nothing big downloads without your yes."
Write-Host ""

# Check Python
try {
    $pyVer = python --version 2>&1
    Write-Host "$pyVer found."
} catch {
    Write-Host "ERROR: python not found. Install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}

# Check git
try {
    git --version | Out-Null
} catch {
    Write-Host "ERROR: git not found. Install git from git-scm.com" -ForegroundColor Red
    exit 1
}

# Clone or pull
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "Directory $InstallDir exists - pulling latest code from $RepoUrl ..."
    git -C $InstallDir pull --ff-only origin main
} elseif (Test-Path $InstallDir) {
    Write-Host "ERROR: $InstallDir already exists but is not a git repository." -ForegroundColor Red
    Write-Host "Please remove it or pass a different -InstallDir."
    exit 1
} else {
    Write-Host "Downloading ILLIP source code from $RepoUrl ..."
    git clone --depth=1 $RepoUrl $InstallDir
}

Set-Location $InstallDir

# Hand off to guided setup - it creates the venv, installs dependencies,
# and explains + asks before every optional download (Ollama model,
# Playwright browser, OmniRoute cloud). Duplicating that here would rot.
# -ExecutionPolicy Bypass: fresh Windows defaults to Restricted, which would
# block running setup.ps1 as a file even though 'irm | iex' itself worked.
Write-Host ""
Write-Host "Code downloaded. Starting guided setup..." -ForegroundColor Green
Write-Host ""
& powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
