@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
title Montador - vozes

if not exist ".venv\Scripts\python.exe" (
    echo O montador ainda nao foi instalado. De dois cliques no instalar.bat primeiro.
    pause
    exit /b 1
)

echo Motores: edge (gratuito), azure, elevenlabs
set "MOTOR="
set /p "MOTOR=Qual motor? (Enter = edge): "
if not defined MOTOR set "MOTOR=edge"
set "IDIOMA="
set /p "IDIOMA=Filtrar por idioma? ex.: pt-BR, en-US (Enter = todos): "

if defined IDIOMA (
    ".venv\Scripts\python.exe" -m montador vozes %MOTOR% --idioma %IDIOMA%
) else (
    ".venv\Scripts\python.exe" -m montador vozes %MOTOR%
)
echo.
pause
