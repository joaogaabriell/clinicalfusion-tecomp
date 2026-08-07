#!/usr/bin/env bash
#
# ClinicalFusion — lancador para Linux e macOS (no Windows, use iniciar.bat).
#
#     ./iniciar.sh        ou:  bash iniciar.sh
#
# Prepara o ambiente e abre o app no navegador. A primeira execucao baixa as
# dependencias e precisa de internet; as seguintes sobem em segundos.

set -euo pipefail

cd "$(dirname "$0")"

SISTEMA="$(uname -s)"
if [ "$SISTEMA" = "Darwin" ]; then
  VENV=".venv-macos"
elif grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null; then
  # Instalar milhares de arquivos em /mnt/c e muito lento. No WSL, a venv fica
  # no filesystem Linux e recebe um identificador por pasta do projeto.
  ID_PROJETO="$(printf '%s' "$PWD" | sha256sum | cut -c1-12)"
  CACHE_CLINICALFUSION="${XDG_CACHE_HOME:-$HOME/.cache}/clinicalfusion"
  VENV="$CACHE_CLINICALFUSION/$ID_PROJETO/venv"
else
  VENV=".venv-linux"
fi
PORTA="${CLINICALFUSION_PORTA:-8501}"
export CLINICALFUSION_DEMO="${CLINICALFUSION_DEMO:-1}"

azul() { printf '\033[1;34m%s\033[0m\n' "$1"; }
erro() { printf '\033[1;31m%s\033[0m\n' "$1" >&2; }

# Sem isto, quem abriu por duplo clique nao veria a mensagem de erro: o terminal
# fecharia junto.
travar_e_sair() {
  erro ""
  erro "A inicializacao falhou. A mensagem acima diz o motivo."
  if [ -t 0 ]; then
    read -r -p "Pressione Enter para fechar."
  fi
  exit 1
}
trap travar_e_sair ERR

azul "=== ClinicalFusion ==="
echo

# --- 1. Encontrar um Python compativel -------------------------------------
# Por nome, porque `python` pode ser 2.x e nem toda distribuicao instala o mesmo alias.
PY=""
for candidato in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$candidato" >/dev/null 2>&1; then
    if "$candidato" -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)" 2>/dev/null; then
      PY="$candidato"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  erro "Python 3.10, 3.11 ou 3.12 nao encontrado."
  erro ""
  erro "Instale o Python e rode este script de novo:"
  erro "  macOS:          brew install python@3.12   (ou https://www.python.org/downloads/)"
  erro "  Ubuntu/Debian:  sudo apt install python3 python3-venv"
  erro "  Fedora:         sudo dnf install python3"
  exit 1
fi

echo "Python encontrado: $("$PY" --version)"
if [ "${VENV#/}" != "$VENV" ]; then
  echo "Ambiente virtual WSL: $VENV"
fi
VERSAO_PY="$($PY -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PACOTE_VENV="python${VERSAO_PY}-venv"

# --- 2. Ambiente virtual ----------------------------------------------------
# Dentro da pasta do projeto, para nao mexer no Python do sistema.
if [ ! -d "$VENV" ]; then
  azul "Criando ambiente virtual..."
  mkdir -p "$(dirname "$VENV")"
  if ! "$PY" -m venv "$VENV" 2>/dev/null; then
    erro "Nao consegui criar o ambiente virtual."
    erro "No Ubuntu/Debian isso costuma ser o pacote venv faltando:"
    erro "  sudo apt install $PACOTE_VENV"
    exit 1
  fi
fi

VENV_PY="$VENV/bin/python"

if ! "$VENV_PY" -c "import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 13) else 1)" 2>/dev/null; then
  erro "A pasta $VENV foi criada com um Python nao suportado ou veio de outro computador."
  erro "Apague a pasta $VENV e rode este arquivo novamente."
  exit 1
fi

# Uma tentativa anterior sem o pacote pythonX.Y-venv pode deixar a pasta criada,
# mas sem pip. Repara quando ensurepip existe; caso contrario, mostra a solucao.
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  azul "Ambiente virtual sem pip; tentando reparar..."
  if ! "$VENV_PY" -m ensurepip --upgrade >/dev/null 2>&1; then
    erro "O Python $VERSAO_PY do sistema esta sem suporte completo a venv/pip."
    erro "No Ubuntu/Debian, instale o pacote e execute este arquivo novamente:"
    erro "  sudo apt install $PACOTE_VENV"
    erro "Nao e necessario apagar a pasta $VENV; o proximo inicio tentara repara-la."
    exit 1
  fi
fi

# --- 3. Dependencias --------------------------------------------------------
# A marca guarda o hash do requirements.txt: sem isso, cada abertura esperaria o pip.
MARCA="$VENV/.dependencias-instaladas"
HASH_ATUAL="$("$VENV_PY" - <<'PY'
import hashlib, pathlib
print(hashlib.sha256(pathlib.Path("requirements.txt").read_bytes()).hexdigest())
PY
)"

DEPENDENCIAS_OK=0
if "$VENV_PY" -c "import streamlit,pandas,numpy,PIL,matplotlib,fpdf,langchain_core,langchain_google_genai" >/dev/null 2>&1; then
  DEPENDENCIAS_OK=1
fi

if [ ! -f "$MARCA" ] || [ "$(cat "$MARCA")" != "$HASH_ATUAL" ] || [ "$DEPENDENCIAS_OK" -ne 1 ]; then
  azul "Instalando dependencias (so na primeira vez; leva alguns minutos)..."
  "$VENV_PY" -m pip install --upgrade pip --quiet
  "$VENV_PY" -m pip install -r requirements.txt --quiet
  "$VENV_PY" -c "import streamlit,pandas,numpy,PIL,matplotlib,fpdf,langchain_core,langchain_google_genai"
  printf '%s' "$HASH_ATUAL" > "$MARCA"
  echo "Dependencias prontas."
else
  echo "Dependencias ja instaladas."
fi

if [ "${CLINICALFUSION_SOMENTE_PREPARAR:-0}" = "1" ]; then
  echo "Ambiente preparado com sucesso."
  exit 0
fi

# --- 4. Subir o app --------------------------------------------------------
echo
azul "Abrindo o ClinicalFusion em http://localhost:$PORTA"
echo "(o navegador abre sozinho; para encerrar, feche esta janela ou pressione Ctrl+C)"
echo

# Daqui em diante, Ctrl+C e encerramento normal, nao falha de inicializacao.
trap - ERR

# Em headless o Streamlit nao abre o navegador; fora de headless ele trava
# pedindo um e-mail no terminal. Por isso abrimos por fora.
"$VENV_PY" abrir_navegador.py "$PORTA" &

exec "$VENV_PY" -m streamlit run app/streamlit_app.py \
  --server.port "$PORTA" \
  --server.headless true \
  --browser.gatherUsageStats false
