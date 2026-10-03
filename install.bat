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
set "RESOLVE_SCRIPTS=C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Scripts"

if not exist "%RESOLVE_SCRIPTS%" (
    echo  WARNING: DaVinci Resolve scripts folder not found at:
    echo  %RESOLVE_SCRIPTS%
    echo  Please copy scripts\aikaraoke_main.py manually to your Resolve Scripts folder.
) else (
    copy /Y "scripts\aikaraoke_main.py" "%RESOLVE_SCRIPTS%\AIKaraoke Resolve.py"
    echo  OK - Plugin installed to DaVinci Resolve.
    echo.
    echo  ================================================
    echo   INSTALLATION COMPLETE!
    echo  ================================================
    echo.
    echo  In DaVinci Resolve:
    echo    Workspace ^> Scripts ^> AIKaraoke Resolve
    echo.
)

pause
