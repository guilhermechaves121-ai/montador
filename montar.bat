@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
title Montador

if not exist ".venv\Scripts\python.exe" (
    echo O montador ainda nao foi instalado.
    echo De dois cliques no instalar.bat primeiro.
    echo.
    pause
    exit /b 1
)

if "%~1"=="" (
    echo Como usar: arraste o arquivo .md do roteiro e solte em cima do montar.bat
    echo.
    pause
    exit /b 1
)

rem Aceita varios roteiros arrastados de uma vez.
:proximo
if "%~1"=="" goto fim
echo.
echo Roteiro: %~nx1
".venv\Scripts\python.exe" -m montador montar "%~1"
shift
goto proximo

:fim
echo.
pause
