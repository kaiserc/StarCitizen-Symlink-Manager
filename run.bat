@echo off
title Star Citizen Symlink Manager
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on your PATH.
    echo Please install Python 3.10 or newer from https://www.python.org/
    echo Make sure to check the box: "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo Checking dependencies...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo [WARNING] Could not automatically install requirements. Attempting to start anyway...
)

python main.py
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
