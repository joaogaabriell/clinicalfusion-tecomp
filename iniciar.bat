@echo off
rem ClinicalFusion -- lancador para Windows (em Linux/macOS, use iniciar.sh).
rem
rem Use com DUPLO CLIQUE. A primeira execucao baixa as dependencias e precisa de
rem internet; as seguintes sobem em segundos.

setlocal
cd /d "%~dp0"

set "VENV=.venv"
if "%CLINICALFUSION_PORTA%"=="" set "CLINICALFUSION_PORTA=8501"
if not defined CLINICALFUSION_DEMO set "CLINICALFUSION_DEMO=1"

echo === ClinicalFusion ===
echo.

rem --- 1. Encontrar um Python compativel ------------------------------------
rem O projeto e testado em Python 3.10-3.12. Priorizamos 3.12 para nao escolher
rem automaticamente uma versao futura ainda nao validada (por exemplo, 3.14).
set "PY="
for %%v in (3.12 3.11 3.10) do (
  py -%%v -c "import sys" >nul 2>&1
  if not errorlevel 1 if not defined PY set "PY=py -%%v"
)

if not defined PY (
  python -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)

if not defined PY (
  echo [ERRO] Python 3.10, 3.11 ou 3.12 nao encontrado.
  echo.
  echo Instale o Python 3.12 e rode este arquivo de novo:
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

"%VENV_PY%" -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)" >nul 2>&1
if errorlevel 1 (
  echo [ERRO] A pasta .venv foi criada com um Python nao suportado ou foi copiada de outro computador.
  echo Apague a pasta .venv e rode este arquivo novamente.
  pause
  exit /b 1
)

rem Uma criacao interrompida pode deixar a pasta .venv sem pip. O ensurepip do
rem Python oficial para Windows consegue reparar esse estado automaticamente.
"%VENV_PY%" -m pip --version >nul 2>&1
if errorlevel 1 (
  echo Ambiente virtual sem pip; tentando reparar...
  "%VENV_PY%" -m ensurepip --upgrade >nul 2>&1
  if errorlevel 1 (
    echo [ERRO] O ambiente virtual esta sem pip e nao pode ser reparado.
    echo Apague a pasta .venv e rode este arquivo novamente.
    pause
    exit /b 1
  )
)

rem --- 3. Dependencias -----------------------------------------------------
rem A marca guarda o hash do requirements.txt: sem isso, cada abertura esperaria o pip.
set "MARCA=%VENV%\.dependencias-instaladas"
set "HASH_ATUAL="
rem VENV_PY e relativo e nao contem espacos. Sem as aspas externas, o cmd nao
rem remove a primeira aspa do subcomando do FOR /F (causa original do erro).
for /f "delims=" %%h in ('%VENV_PY% -c "import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())"') do set "HASH_ATUAL=%%h"

if not defined HASH_ATUAL (
  echo [ERRO] Nao consegui verificar o arquivo requirements.txt.
  pause
  exit /b 1
)

set "HASH_ANTERIOR="
if exist "%MARCA%" set /p HASH_ANTERIOR=<"%MARCA%"

set "DEPENDENCIAS_OK="
"%VENV_PY%" -c "import streamlit,pandas,numpy,PIL,matplotlib,fpdf,langchain_core,langchain_google_genai" >nul 2>&1
if not errorlevel 1 set "DEPENDENCIAS_OK=1"

set "INSTALAR="
if not "%HASH_ANTERIOR%"=="%HASH_ATUAL%" set "INSTALAR=1"
if not defined DEPENDENCIAS_OK set "INSTALAR=1"

if defined INSTALAR (
  echo Instalando dependencias ^(so na primeira vez; leva alguns minutos^)...
  "%VENV_PY%" -m pip install --upgrade pip --quiet
  if errorlevel 1 (
    echo [ERRO] Nao consegui preparar o instalador de dependencias ^(pip^).
    pause
    exit /b 1
  )
  "%VENV_PY%" -m pip install -r requirements.txt --quiet
  if errorlevel 1 (
    echo [ERRO] A instalacao das dependencias falhou.
    echo Confira a conexao com a internet e rode de novo.
    pause
    exit /b 1
  )
  "%VENV_PY%" -c "import streamlit,pandas,numpy,PIL,matplotlib,fpdf,langchain_core,langchain_google_genai" >nul 2>&1
  if errorlevel 1 (
    echo [ERRO] A instalacao terminou, mas uma dependencia obrigatoria ainda esta ausente.
    pause
    exit /b 1
  )
  >"%MARCA%" echo %HASH_ATUAL%
  echo Dependencias prontas.
) else (
  echo Dependencias ja instaladas.
)

if "%CLINICALFUSION_SOMENTE_PREPARAR%"=="1" (
  echo Ambiente preparado com sucesso.
  exit /b 0
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
