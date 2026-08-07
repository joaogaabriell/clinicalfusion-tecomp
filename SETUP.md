# Setup do ambiente — ClinicalFusion

Guia para colocar o protótipo rodando na sua máquina, do zero. Cobre **Windows (PowerShell)** e **Linux/macOS (bash)**.

Se algo falhar, veja [Problemas comuns](#-problemas-comuns) no fim.

---

## ⚠️ Antes de começar: os dados não vêm no repositório

O Symile-MIMIC é de **acesso credenciado**. A licença que acompanha o dataset — *PhysioNet Credentialed Health Data License 1.5.0* — diz, na cláusula 3:

> *The LICENSEE will not share access to PhysioNet restricted data with anyone else.*

Ou seja: **cada integrante baixa a própria cópia com o próprio credenciamento**. Não vale subir o `.zip` no repositório, mandar por Drive/WhatsApp, nem passar um `.npy` para o colega — mesmo em repositório privado, mesmo entre a equipe. Quem compartilha responde pessoalmente, porque o credenciamento é nominal.

Isso **não atrapalha o trabalho em equipe**: o `src/build_subset.py` é determinístico. Todo mundo que rodar com o mesmo `--n-casos` gera exatamente os mesmos casos, com os mesmos `case_id`. Vocês trabalham sobre dados idênticos sem nunca versionar um byte de paciente.

> **Sem credenciamento ainda?** Dá para trabalhar na interface assim mesmo: pule a Parte 2 e rode o app. A tela inicial detecta a ausência do subconjunto e explica o que falta, em vez de quebrar.

---

## 📋 Pré-requisitos

- **Python 3.10, 3.11 ou 3.12** (`python --version`) — 3.13 ainda não foi validado
- **Git**
- **~1 GB de disco livre** — o dataset baixado (~690 MB) e o subconjunto gerado (~80 MB)
- Credenciamento no PhysioNet aprovado — só para a Parte 2

---

## Parte 1 — Ambiente

Na raiz do repositório.

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o PowerShell recusar o `Activate.ps1` com erro de *execution policy*, rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Linux / macOS (bash)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Confira que deu certo — deve imprimir um caminho terminado em `.venv`:

```bash
python -c "import sys; print(sys.prefix)"
```

---

## Parte 2 — Dados credenciados

### 2.1 Baixar do PhysioNet

Requer credenciamento aprovado + treinamento CITI + DUA assinada na [página do dataset](https://physionet.org/content/symile-mimic/1.0.0/). Detalhes em [`data/README.md`](data/README.md).

```bash
wget -r -N -c -np --user SEU_USUARIO --ask-password \
  https://physionet.org/files/symile-mimic/1.0.0/
```

### 2.2 Guardar **fora** do repositório

Extraia o dataset em qualquer lugar **fora da pasta do projeto**. Isso evita que os dados entrem no git por acidente e, no Windows, que o OneDrive sincronize centenas de MB de dado credenciado para a nuvem.

Sugestões:

| SO | Local sugerido |
|----|----------------|
| Windows | `C:\Users\<voce>\datasets\` |
| Linux / macOS | `~/datasets/` |

O que importa é chegar na pasta `1.0.0`, aquela que contém `symile_mimic_data.csv`, `test.csv` e `data_npy/`.

### 2.3 Apontar o `.env` para ela

O `.env` é **pessoal e ignorado pelo git** — é exatamente o mecanismo que faz o projeto funcionar em Windows e Linux ao mesmo tempo, sem ninguém pisar no caminho do outro. Cada um tem o seu, com o caminho da própria máquina; ninguém commita isso.

```bash
cp .env.example .env      # Windows (PowerShell): copy .env.example .env
```

Edite o `.env` e ajuste `SYMILE_MIMIC_DIR`:

```ini
# Windows — use barras normais (/), não invertidas
SYMILE_MIMIC_DIR=C:/Users/Joao/datasets/physionet.org/files/symile-mimic/1.0.0

# Linux / macOS
SYMILE_MIMIC_DIR=/home/madu/datasets/physionet.org/files/symile-mimic/1.0.0
```

> **Windows:** prefira `/` no lugar de `\`. O `Path` do Python entende `/` no Windows sem problema, e a barra invertida vira escape em vários contextos. `~` também funciona: `~/datasets/...`.

Confira que o caminho está certo:

```bash
python -c "from src import config; print('fonte:', config.diretorio_fonte())"
```

Isso imprime a pasta encontrada, ou avisa que o caminho não existe.

### 2.4 Gerar o subconjunto

```bash
python -m src.build_subset --n-casos 150 --limpar
```

Leva ~13 s e ocupa ~80 MB em `data/symile-mimic/` — pasta já bloqueada pelo `.gitignore`. Saída esperada:

```
150 casos gerados em .../data/symile-mimic
  radiografia real: 46 | placeholder: 104
  ECG: 0 reais | 150 mock
  labs presentes por caso (mediana): 34 de 50
```

Os números acima são o **comportamento correto**, não um erro seu: o `cxr_test.npy` que a turma recebeu veio truncado (só 46 das 4640 imagens) e os `ecg_*.npy` não vieram. A procedência de cada modalidade aparece na própria tela do app. Contexto em [`data/README.md`](data/README.md).

---

## Parte 3 — Rodar

```bash
python -m streamlit run app/streamlit_app.py
```

Abre em <http://localhost:8501>.

**Testes:**

```bash
python -m pytest tests
```

---

## 🔍 Problemas comuns

| Sintoma | Causa provável | Solução |
|---------|----------------|---------|
| `Defina SYMILE_MIMIC_DIR apontando para a pasta '1.0.0'` | Sem `.env`, ou sem a variável | Passo 2.3 |
| `SYMILE_MIMIC_DIR aponta para um caminho inexistente` | Caminho errado, ou parou antes da pasta `1.0.0` | Confira com o comando do 2.3. O caminho deve terminar em `1.0.0` |
| `Activate.ps1 ... não pode ser carregado` | Execution policy do PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: streamlit` | venv não ativado | Reative (Parte 1); confira com `python -c "import sys; print(sys.prefix)"` |
| `Port 8501 is already in use` | App já rodando | Use `--server.port 8502`, ou encerre o processo anterior |
| App abre, mas sem pacientes | Subconjunto não gerado | Passo 2.4 |
| `git status` mostra dados ou `.zip` | Arquivo fora das pastas ignoradas | **Não commite.** Mova para fora do repositório (2.2) |

---

## ✅ Antes de commitar

O `.gitignore` já cobre `.env`, `.venv/`, `data/symile-mimic/` e as pastas de dados. Ainda assim, vale o hábito:

```bash
git status
```

Se aparecer **qualquer** arquivo de dado do PhysioNet (`.zip`, `.npy`, `.csv` do dataset), pare e mova para fora do repositório. Nunca use `git add -f` para forçar. Uma vez no histórico, remover exige reescrevê-lo para todo o time — e quem já clonou continua com a cópia.
