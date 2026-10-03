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
set "APPDATA_SCRIPTS=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"
set "PROGRAMDATA_SCRIPTS=C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts"

:: Create directories
mkdir "%APPDATA_SCRIPTS%\Edit" 2>nul
mkdir "%APPDATA_SCRIPTS%\Utility" 2>nul
mkdir "%APPDATA_SCRIPTS%\Comp" 2>nul
mkdir "%PROGRAMDATA_SCRIPTS%\Edit" 2>nul
mkdir "%PROGRAMDATA_SCRIPTS%\Utility" 2>nul

:: Copy scripts to User AppData
copy /Y "scripts\*" "%APPDATA_SCRIPTS%\" >nul
copy /Y "scripts\*" "%APPDATA_SCRIPTS%\Edit\" >nul
copy /Y "scripts\*" "%APPDATA_SCRIPTS%\Utility\" >nul
copy /Y "scripts\*" "%APPDATA_SCRIPTS%\Comp\" >nul

:: Copy scripts to ProgramData
copy /Y "scripts\*" "%PROGRAMDATA_SCRIPTS%\Edit\" >nul
copy /Y "scripts\*" "%PROGRAMDATA_SCRIPTS%\Utility\" >nul

echo  OK - Plugin instalado correctamente en DaVinci Resolve.
echo.
echo  ================================================
echo   INSTALACION COMPLETA!
echo  ================================================
echo.
echo  En DaVinci Resolve abre:
echo    Espacio de trabajo (Area de trabajo) ^> Scripts ^> AIKaraoke Resolve
echo    o
echo    Espacio de trabajo ^> Scripts ^> Edit ^> AIKaraoke Resolve
echo.

pause
