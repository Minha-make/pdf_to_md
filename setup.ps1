# OmniPDF2MD — One-Touch Windows Setup Script
# Requires: Python 3.12+, Node.js 18+ (optional for Web UI build)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  OmniPDF2MD — Local Setup (Windows)    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Blue

# 1. Check Python 3.12
$pythonCmd = $null
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $ver = & py -3.12 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pythonCmd = "py -3.12"
    }
}

if (-not $pythonCmd) {
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        $ver = & python --version 2>&1
        if ($ver -match "3\.12") {
            $pythonCmd = "python"
        }
    }
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] Python 3.12 is required but not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.12 from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/4] Found Python: $ver" -ForegroundColor Green

# 2. Virtual Environment Setup
$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"
$omnipdfExe = Join-Path $venvDir "Scripts\omnipdf.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[2/4] Creating virtual environment at .venv..." -ForegroundColor Cyan
    Invoke-Expression "$pythonCmd -m venv `"$venvDir`""
} else {
    Write-Host "[2/4] Virtual environment already exists at .venv." -ForegroundColor Green
}

# 3. Install Python Dependencies
Write-Host "[3/4] Installing Python packages and OmniPDF CLI..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip --quiet
& $venvPip install -e ".[deep,api,dev]"

# 4. Build Web Studio Frontend (if npm is available)
$webDir = Join-Path $PSScriptRoot "web"
$webDist = Join-Path $webDir "dist"

if (Get-Command "npm" -ErrorAction SilentlyContinue) {
    Write-Host "[4/4] Building Web Studio UI (React + Tailwind)..." -ForegroundColor Cyan
    Push-Location $webDir
    try {
        & npm install --silent
        & npm run build
        Write-Host "Web Studio build complete: $webDist" -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[4/4] [NOTICE] npm not found in PATH. Pre-built or development web UI will be skipped." -ForegroundColor Yellow
}

# 5. Doctor Health Check
Write-Host ""
Write-Host "Running OmniPDF Doctor Diagnostic..." -ForegroundColor Cyan
& $omnipdfExe doctor

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Setup Complete! OmniPDF2MD is ready to use.             " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Quick Start Commands:" -ForegroundColor White
Write-Host "  • Start Web Studio:    .venv\Scripts\omnipdf serve" -ForegroundColor Cyan
Write-Host "  • Convert via CLI:     .venv\Scripts\omnipdf convert document.pdf -o output" -ForegroundColor Cyan
Write-Host "  • Check System Health: .venv\Scripts\omnipdf doctor" -ForegroundColor Cyan
Write-Host ""
