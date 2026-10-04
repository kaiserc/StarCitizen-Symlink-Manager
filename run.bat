@echo off
title Star Citizen Symlink Manager
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred. If python is not on PATH, please make sure Python 3.10+ is installed.
    pause
)
