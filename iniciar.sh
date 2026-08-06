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

VENV=".venv"
PYTHON_MINIMO="3.10"
PORTA="${CLINICALFUSION_PORTA:-8501}"

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
for candidato in python3.13 python3.12 python3.11 python3.10 python3 python; do
  if command -v "$candidato" >/dev/null 2>&1; then
    if "$candidato" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
      PY="$candidato"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  erro "Python $PYTHON_MINIMO ou superior nao encontrado."
  erro ""
  erro "Instale o Python e rode este script de novo:"
  erro "  macOS:          brew install python@3.12   (ou https://www.python.org/downloads/)"
  erro "  Ubuntu/Debian:  sudo apt install python3 python3-venv"
  erro "  Fedora:         sudo dnf install python3"
  exit 1
fi

echo "Python encontrado: $("$PY" --version)"

# --- 2. Ambiente virtual ----------------------------------------------------
# Dentro da pasta do projeto, para nao mexer no Python do sistema.
if [ ! -d "$VENV" ]; then
  azul "Criando ambiente virtual..."
  if ! "$PY" -m venv "$VENV" 2>/dev/null; then
    erro "Nao consegui criar o ambiente virtual."
    erro "No Ubuntu/Debian isso costuma ser o pacote venv faltando:"
    erro "  sudo apt install python3-venv"
    exit 1
  fi
fi

VENV_PY="$VENV/bin/python"

# --- 3. Dependencias --------------------------------------------------------
# A marca guarda o hash do requirements.txt: sem isso, cada abertura esperaria o pip.
MARCA="$VENV/.dependencias-instaladas"
HASH_ATUAL="$("$VENV_PY" - <<'PY'
import hashlib, pathlib
print(hashlib.sha256(pathlib.Path("requirements.txt").read_bytes()).hexdigest())
PY
)"

if [ ! -f "$MARCA" ] || [ "$(cat "$MARCA")" != "$HASH_ATUAL" ]; then
  azul "Instalando dependencias (so na primeira vez; leva alguns minutos)..."
  "$VENV_PY" -m pip install --upgrade pip --quiet
  "$VENV_PY" -m pip install -r requirements.txt --quiet
  printf '%s' "$HASH_ATUAL" > "$MARCA"
  echo "Dependencias prontas."
else
  echo "Dependencias ja instaladas."
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
