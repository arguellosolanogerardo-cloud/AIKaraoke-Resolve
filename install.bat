@echo off
title AIKaraoke Resolve - Installer
color 0A
echo.
echo  ================================================
echo   AIKaraoke Resolve - Windows Installer
echo  ================================================
echo.

:: Check Python
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python not found.
    echo  Please install Python 3.8+ from https://python.org
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
python --version
echo  OK - Python found.
echo.

:: Check ffmpeg
echo [2/4] Checking ffmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo  WARNING: ffmpeg not found in PATH.
    echo  Download from https://ffmpeg.org/download.html
    echo  and add it to your system PATH.
    echo  The plugin will NOT work without ffmpeg.
    echo.
) else (
    echo  OK - ffmpeg found.
    echo.
)

:: Install Python dependencies
echo [3/4] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo  ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo  OK - Dependencies installed.
echo.

:: Copy script to DaVinci Resolve Scripts folder
echo [4/4] Installing plugin to DaVinci Resolve...
set "RESOLVE_SCRIPTS_EDIT=C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Edit"
set "RESOLVE_SCRIPTS_UTIL=C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"

if not exist "%RESOLVE_SCRIPTS_EDIT%" (
    mkdir "%RESOLVE_SCRIPTS_EDIT%" 2>nul
)
if not exist "%RESOLVE_SCRIPTS_UTIL%" (
    mkdir "%RESOLVE_SCRIPTS_UTIL%" 2>nul
)

copy /Y "scripts\aikaraoke_main.py" "%RESOLVE_SCRIPTS_EDIT%\AIKaraoke Resolve.py" >nul
copy /Y "scripts\aikaraoke_main.py" "%RESOLVE_SCRIPTS_UTIL%\AIKaraoke Resolve.py" >nul

echo  OK - Plugin instalado correctamente en DaVinci Resolve.
echo.
echo  ================================================
echo   INSTALACION COMPLETA!
echo  ================================================
echo.
echo  En DaVinci Resolve abre:
echo    Workspace ^> Scripts ^> Edit ^> AIKaraoke Resolve
echo    o
echo    Workspace ^> Scripts ^> Utility ^> AIKaraoke Resolve
echo.

pause
