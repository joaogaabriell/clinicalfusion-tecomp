@echo off
rem ClinicalFusion -- lancador para Windows (em Linux/macOS, use iniciar.sh).
rem
rem Use com DUPLO CLIQUE. A primeira execucao baixa as dependencias e precisa de
rem internet; as seguintes sobem em segundos.

setlocal
cd /d "%~dp0"

set "VENV=.venv"
if "%CLINICALFUSION_PORTA%"=="" set "CLINICALFUSION_PORTA=8501"

echo === ClinicalFusion ===
echo.

rem --- 1. Encontrar um Python compativel ------------------------------------
rem `py` e o recomendado no Windows; `python` fica como reserva. O teste de versao
rem evita falhar depois, no meio do pip, com erro incompreensivel.
set "PY="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=py -3"

if not defined PY (
  python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)

if not defined PY (
  echo [ERRO] Python 3.10 ou superior nao encontrado.
  echo.
  echo Instale o Python e rode este arquivo de novo:
  echo   https://www.python.org/downloads/
  echo.
  echo IMPORTANTE: na tela do instalador, marque "Add python.exe to PATH".
  echo.
  pause
  exit /b 1
)

for /f "delims=" %%v in ('%PY% --version 2^>^&1') do echo Python encontrado: %%v

rem --- 2. Ambiente virtual --------------------------------------------------
if not exist "%VENV%" (
  echo Criando ambiente virtual...
  %PY% -m venv "%VENV%"
  if errorlevel 1 (
    echo [ERRO] Nao consegui criar o ambiente virtual.
    pause
    exit /b 1
  )
)

set "VENV_PY=%VENV%\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [ERRO] Ambiente virtual incompleto. Apague a pasta .venv e rode de novo.
  pause
  exit /b 1
)

rem --- 3. Dependencias -----------------------------------------------------
rem A marca guarda o hash do requirements.txt: sem isso, cada abertura esperaria o pip.
set "MARCA=%VENV%\.dependencias-instaladas"
for /f "delims=" %%h in ('"%VENV_PY%" -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())"') do set "HASH_ATUAL=%%h"

set "HASH_ANTERIOR="
if exist "%MARCA%" set /p HASH_ANTERIOR=<"%MARCA%"

if not "%HASH_ANTERIOR%"=="%HASH_ATUAL%" (
  echo Instalando dependencias ^(so na primeira vez; leva alguns minutos^)...
  "%VENV_PY%" -m pip install --upgrade pip --quiet
  "%VENV_PY%" -m pip install -r requirements.txt --quiet
  if errorlevel 1 (
    echo [ERRO] A instalacao das dependencias falhou.
    echo Confira a conexao com a internet e rode de novo.
    pause
    exit /b 1
  )
  >"%MARCA%" echo %HASH_ATUAL%
  echo Dependencias prontas.
) else (
  echo Dependencias ja instaladas.
)

rem --- 4. Subir o app ------------------------------------------------------
echo.
echo Abrindo o ClinicalFusion em http://localhost:%CLINICALFUSION_PORTA%
echo (o navegador abre sozinho; para encerrar, feche esta janela)
echo.

rem Em headless o Streamlit nao abre o navegador; fora de headless ele trava
rem pedindo um e-mail no terminal. Por isso abrimos por fora.
start "" /b "%VENV_PY%" abrir_navegador.py %CLINICALFUSION_PORTA%

"%VENV_PY%" -m streamlit run app/streamlit_app.py --server.port %CLINICALFUSION_PORTA% --server.headless true --browser.gatherUsageStats false

rem Janela aberta para a mensagem ser lida se o Streamlit sair sozinho.
echo.
echo O ClinicalFusion foi encerrado.
pause
