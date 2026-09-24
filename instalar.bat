@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Montador - instalacao

echo ============================================================
echo  MONTADOR - instalacao
echo ============================================================
echo.

rem --- 1. Procura o Python 3.9 ou mais novo ---------------------------
set "PY="
where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY goto sem_python

echo [1/4] Python encontrado:
%PY% --version
echo.

rem --- 2. Cria o ambiente virtual ------------------------------------
if exist ".venv\Scripts\python.exe" (
    echo [2/4] Ambiente virtual ja existe, reaproveitando.
) else (
    echo [2/4] Criando o ambiente virtual .venv ...
    %PY% -m venv .venv
    if errorlevel 1 goto erro
)
echo.

rem --- 3. Instala as dependencias ------------------------------------
echo [3/4] Instalando as dependencias (precisa de internet)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q --upgrade pip
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto erro
if not exist ".env" (
    copy /y ".env.exemplo" ".env" >nul
    echo Arquivo .env criado. So precisa preencher se for usar Azure ou ElevenLabs.
)
echo.

rem --- 4. Confere o ffmpeg -------------------------------------------
echo [4/4] Procurando o ffmpeg...
where ffmpeg >nul 2>nul
if errorlevel 1 (
    if exist "ffmpeg\bin\ffmpeg.exe" (
        echo ffmpeg encontrado na pasta do projeto.
    ) else (
        echo ATENCAO: ffmpeg nao encontrado.
        echo O montador funciona sem ele, mas NAO gera a narracao_completa.mp3.
        echo Veja no README.md a secao "Instalar o ffmpeg".
    )
) else (
    echo ffmpeg encontrado.
)

echo.
echo ============================================================
echo  Instalacao concluida!
echo  Agora arraste o arquivo .md do roteiro sobre o montar.bat
echo ============================================================
echo.
pause
exit /b 0

:sem_python
echo Python 3.9 ou mais novo NAO foi encontrado neste computador.
echo.
echo Como instalar:
echo   1. Acesse https://www.python.org/downloads/
echo   2. Clique em "Download Python" e abra o instalador.
echo   3. Na primeira tela, MARQUE a opcao "Add python.exe to PATH".
echo   4. Clique em "Install Now" e aguarde terminar.
echo   5. Feche esta janela e de dois cliques no instalar.bat de novo.
echo.
echo Abrindo a pagina de download...
start "" "https://www.python.org/downloads/"
echo.
pause
exit /b 1

:erro
echo.
echo ERRO durante a instalacao. Confira sua conexao com a internet e
echo tente de novo. Se o erro continuar, apague a pasta .venv e rode
echo o instalar.bat outra vez.
echo.
pause
exit /b 1
