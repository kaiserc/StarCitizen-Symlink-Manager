<#
.SYNOPSIS
    Star Citizen Symlink Manager Launcher for PowerShell
#>
$Host.UI.RawUI.WindowTitle = "Star Citizen Symlink Manager"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "        STAR CITIZEN SYMLINK MANAGER (POWERSHELL)      " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 1. Verify Python availability
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python was not found on your PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10 or newer from https://www.python.org/"
    Write-Host "Make sure to check the box: 'Add Python to PATH' during installation.`n"
    Pause
    exit 1
}

# 2. Check and install dependencies
Write-Host "[INIT] Checking dependencies..." -ForegroundColor Gray
python -m pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] Could not automatically install requirements. Attempting to start anyway..." -ForegroundColor Yellow
}

# 3. Launch application
python main.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[ERROR] Application exited with an error code ($LASTEXITCODE)." -ForegroundColor Red
    Pause
}
