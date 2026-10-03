@echo off
title AIKaraoke Resolve
color 0B
echo.
echo ========================================================
echo   AIKaraoke Resolve - Generador de Bola de Karaoke
echo ========================================================
echo.
echo Asegurate de tener DaVinci Resolve abierto con tu proyecto.
echo.

cd /d "%~dp0"
python scripts\aikaraoke_main.py

echo.
pause
