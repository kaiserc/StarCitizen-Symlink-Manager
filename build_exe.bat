@echo off
title Build Star Citizen Symlink Manager Executable
cd /d "%~dp0"
echo =======================================================
echo Building Standalone Star Citizen Symlink Manager EXE...
echo =======================================================

pyinstaller --noconfirm StarCitizen-Symlink-Manager.spec

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo =======================================================
echo Build complete! Executable is at:
echo dist\StarCitizen-Symlink-Manager\StarCitizen-Symlink-Manager.exe
echo =======================================================
pause
