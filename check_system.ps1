# ILLIP AI System Diagnostic Checker
# Verifies installation prereqs and active local configurations

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "     ILLIP AI System Diagnostic Check     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$allPassed = $true

# 1. Verify Python
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Cyan
try {
    $pythonVersion = & python --version 2>&1
    if ($lastExitCode -ne 0 -or $pythonVersion -like "*not recognized*") {
        Write-Host "[-] Python is NOT installed or not on System PATH." -ForegroundColor Red
        $allPassed = $false
    } else {
        Write-Host "[+] Python version found: $pythonVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "[-] Python is NOT installed." -ForegroundColor Red
    $allPassed = $false
}

# 2. Verify .env file
Write-Host ""
Write-Host "[2/5] Checking .env configuration file..." -ForegroundColor Cyan
$envPath = Join-Path $PSScriptRoot ".env"
$targetModel = "qwen2.5:3b" # default fallback
if (Test-Path $envPath) {
    Write-Host "[+] .env file detected." -ForegroundColor Green
    
    # Parse env file for model name
    $envContent = Get-Content $envPath
    foreach ($line in $envContent) {
        if ($line -match "^OLLAMA_MODEL\s*=\s*`"?(.*?)`"?$") {
            $targetModel = $Matches[1].Trim()
        }
    }
    Write-Host "[+] Active model configuration from env: $targetModel" -ForegroundColor Gray
} else {
    Write-Host "[-] .env configuration file is missing!" -ForegroundColor Yellow
    Write-Host "    (Run setup.bat to copy it from .env.example)" -ForegroundColor Yellow
    $allPassed = $false
}

# 3. Verify Ollama Connection
Write-Host ""
Write-Host "[3/5] Checking Ollama service..." -ForegroundColor Cyan
$ollamaRunning = $false
try {
    # Fetch local tags endpoint
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
    Write-Host "[+] Ollama server is running and responding." -ForegroundColor Green
    $ollamaRunning = $true
} catch {
    Write-Host "[-] Ollama server is NOT running or unreachable on port 11434." -ForegroundColor Yellow
    Write-Host "    Make sure Ollama is installed and running locally." -ForegroundColor Yellow
    $allPassed = $false
}

# 4. Verify Model Availability
Write-Host ""
Write-Host "[4/5] Checking local Ollama model availability..." -ForegroundColor Cyan
if ($ollamaRunning) {
    $modelFound = $false
    foreach ($model in $response.models) {
        if ($model.name -eq $targetModel -or $model.name -like "$targetModel*") {
            $modelFound = $true
            break
        }
    }
    
    if ($modelFound) {
        Write-Host "[+] Target model '$targetModel' is available in Ollama." -ForegroundColor Green
    } else {
        Write-Host "[-] Target model '$targetModel' is NOT downloaded in Ollama!" -ForegroundColor Yellow
        Write-Host "    Run: 'ollama pull $targetModel' in your terminal." -ForegroundColor Yellow
        $allPassed = $false
    }
} else {
    Write-Host "[-] Skipped model check because Ollama service is unreachable." -ForegroundColor Yellow
}

# 5. Verify Workspace Directory Structure
Write-Host ""
Write-Host "[5/5] Checking workspace directories..." -ForegroundColor Cyan
$folders = @("data", "data/workspaces", "data/tasks", "data/logs", "data/memory", "data/snapshots")
$missingFolders = 0

foreach ($folder in $folders) {
    $path = Join-Path $PSScriptRoot $folder
    if (Test-Path $path) {
        Write-Host "[+] Folder exists: ./$folder" -ForegroundColor Gray
    } else {
        Write-Host "[-] Folder missing: ./$folder" -ForegroundColor Yellow
        $missingFolders++
    }
}

if ($missingFolders -eq 0) {
    Write-Host "[+] All workspace directory layers are present." -ForegroundColor Green
} else {
    Write-Host "[-] Some folder layers are missing (Will be auto-created on application launch)." -ForegroundColor Gray
}

# Final Assessment
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "    STATUS: SYSTEM FULLY READY FOR RUN    " -ForegroundColor Green -BackgroundColor Black
} else {
    Write-Host "    STATUS: DEGRADED (Check warnings above)   " -ForegroundColor Yellow -BackgroundColor Black
}
Write-Host "==========================================" -ForegroundColor Cyan
