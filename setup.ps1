# ILLIP AI Environment Setup Script
# Automates local virtualenv configuration and dependency installs

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "      Starting ILLIP AI Setup Engine      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Verify Python
try {
    $pythonVersion = & python --version 2>&1
    if ($lastExitCode -ne 0 -or $pythonVersion -like "*not recognized*") {
        Write-Host "[!] Error: Python is not installed or not on System PATH." -ForegroundColor Red
        Write-Host "    Please install Python 3.10+ before continuing." -ForegroundColor Yellow
        Exit 1
    }
} catch {
    Write-Host "[!] Error: Python is not installed." -ForegroundColor Red
    Exit 1
}

# 2. Virtual Environment Configuration
$venvPath = Join-Path $PSScriptRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "[*] Creating Python Virtual Environment (.venv)..." -ForegroundColor Cyan
    try {
        & python -m venv .venv
        Write-Host "[+] Virtual Environment created successfully." -ForegroundColor Green
    } catch {
        Write-Host "[!] Error creating virtual environment: $_" -ForegroundColor Red
        Exit 1
    }
} else {
    Write-Host "[+] Existing Virtual Environment (.venv) detected. Skipping creation." -ForegroundColor Green
}

# 3. Upgrade pip and Install Requirements
Write-Host ""
Write-Host "[*] Upgrading pip..." -ForegroundColor Cyan
$pipPath = Join-Path $venvPath "Scripts\pip.exe"
$pythonExec = Join-Path $venvPath "Scripts\python.exe"

try {
    & $pythonExec -m pip install --upgrade pip --quiet
    Write-Host "[+] pip upgraded successfully." -ForegroundColor Green
} catch {
    Write-Host "[~] Warning: Failed to upgrade pip. Continuing with install." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[*] Installing dependencies from requirements.txt..." -ForegroundColor Cyan
$reqsFile = Join-Path $PSScriptRoot "requirements.txt"
if (Test-Path $reqsFile) {
    try {
        & $pipPath install -r $reqsFile
        Write-Host "[+] All dependencies installed successfully." -ForegroundColor Green
    } catch {
        Write-Host "[!] Error installing requirements: $_" -ForegroundColor Red
        Exit 1
    }
} else {
    Write-Host "[!] Error: requirements.txt is missing from root folder." -ForegroundColor Red
    Exit 1
}

# 4. Environment Template Configuration
Write-Host ""
Write-Host "[*] Configuring .env file..." -ForegroundColor Cyan
$envPath = Join-Path $PSScriptRoot ".env"
$examplePath = Join-Path $PSScriptRoot ".env.example"

if (-not (Test-Path $envPath)) {
    if (Test-Path $examplePath) {
        Copy-Item $examplePath $envPath
        Write-Host "[+] Created .env file from .env.example." -ForegroundColor Green
    } else {
        Write-Host "[~] Warning: .env.example is missing. Creating empty .env file." -ForegroundColor Yellow
        New-Item $envPath -ItemType File -Value "MODEL_PROVIDER=ollama`nOLLAMA_MODEL=qwen2.5:3b`n" | Out-Null
    }
} else {
    Write-Host "[+] .env file already exists. Skipping copy." -ForegroundColor Green
}

# 5. Directory Layer Checks
Write-Host ""
Write-Host "[*] Ensuring all local directory layers exist..." -ForegroundColor Cyan
$folders = @("data", "data/workspaces", "data/tasks", "data/logs", "data/memory", "data/snapshots")
foreach ($folder in $folders) {
    $path = Join-Path $PSScriptRoot $folder
    if (-not (Test-Path $path)) {
        New-Item $path -ItemType Directory | Out-Null
        Write-Host "[+] Created folder: ./$folder" -ForegroundColor Gray
    }
}

# 6. Execute Diagnostic Checks
Write-Host ""
Write-Host "[*] Launching system diagnostic checks..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "check_system.ps1")
