# ClinicalFusion

**Assistente Inteligente Multimodal para Análise Integrada de Casos Clínicos utilizando LLMs Multimodais**


## 📌 Sobre o projeto

O ClinicalFusion integra diferentes modalidades de dados clínicos de um mesmo paciente — **radiografia de tórax**, **eletrocardiograma (ECG)**, **exames laboratoriais** e **informações clínicas básicas** — para gerar um **relatório clínico estruturado** com o apoio de um **Large Language Model (LLM) multimodal**.

O sistema analisa conjuntamente as modalidades, produz um resumo do caso, destaca os principais achados, apresenta hipóteses clínicas educacionais (sem caráter diagnóstico) e justifica suas conclusões com base nas evidências dos dados.

Conceitos aplicados: **LLMs Multimodais**, **Vision-Language Models**, **Prompt Engineering**, **Engenharia de Software** e **IA Generativa** aplicada à saúde.

---

## 🗄️ Base de dados

**Symile-MIMIC** — <https://physionet.org/content/symile-mimic/1.0.0/>

Dataset multimodal com radiografias de tórax, ECGs, exames laboratoriais e dados demográficos/clínicos sincronizados por paciente. O projeto utiliza um subconjunto de **100 a 500 casos**.

> 🔒 **Acesso credenciado.** O Symile-MIMIC exige conta PhysioNet credenciada, treinamento CITI e assinatura da *Data Use Agreement (DUA)*. **Os dados reais NÃO podem ser versionados neste repositório** (a DUA proíbe redistribuição). Veja [`data/README.md`](data/README.md) para a estrutura esperada e as instruções de download.

---

## 📂 Estrutura do repositório

```
Clinical-Fusion---TECOMP/
├── README.md                 # este arquivo
├── CONTRIBUTING.md           # fluxo de trabalho, branches e padrão de commits
├── requirements.txt          # dependências (stack a ser confirmada pela equipe)
├── .gitignore                # protege dados credenciados de irem ao GitHub
├── docs/                     # documentação da Semana 1 (itens da entrega)
│   ├── 01-estudo-dataset-symile-mimic.md
│   ├── 02-organizacao-modalidades.md
│   ├── 03-leitura-visualizacao.md
│   ├── 04-arquitetura-solucao.md
│   └── 05-analise-tecnologias.md
├── data/                     # dados (reais ficam locais/ignorados; ver data/README.md)
├── src/                      # código-fonte da aplicação
│   ├── config.py             # caminhos, specs das modalidades, metadados do MIMIC
│   ├── symile_source.py      # leitura do Symile-MIMIC bruto (credenciado)
│   ├── mock.py               # geradores sintéticos (ECG e placeholder de radiografia)
│   ├── build_subset.py       # monta o subconjunto uma-pasta-por-paciente
│   └── loaders.py            # leitura do subconjunto (usado pela interface)
├── app/                      # protótipo da interface em Streamlit
├── notebooks/                # notebooks de exploração e validação dos dados
├── tests/                    # testes automatizados
└── .env.example              # modelo do .env (caminho dos dados credenciados)
```

---

## ✅ Requisitos funcionais (visão geral)

| ID | Descrição |
|------|-----------|
| RF01 | Carregar um caso clínico do dataset Symile-MIMIC |
| RF02 | Exibir os dados demográficos e clínicos do paciente |
| RF03 | Exibir a radiografia de tórax |
| RF04 | Exibir os exames laboratoriais |
| RF05 | Exibir o ECG do paciente |
| RF06 | Receber perguntas em linguagem natural |
| RF07 | Integrar todas as modalidades em um único prompt multimodal |
| RF08 | Gerar um relatório estruturado utilizando um LLM multimodal |
| RF09 | Apresentar resumo, achados, hipóteses, justificativa, exames sugeridos e aviso |
| RF10 | Permitir visualizar simultaneamente os exames usados para gerar a resposta |

---

## 🗓️ Cronograma (1 mês)

| Semana | Objetivo |
|--------|----------|
| **1** | Conhecer o dataset, selecionar os casos, organizar as modalidades, definir a arquitetura |
| 2 | Leitura das imagens, ECGs e exames laboratoriais; interface inicial |
| 3 | Integrar o LLM multimodal, desenvolver prompts, gerar relatórios, validar respostas |
| 4 | Testes finais, refinamento, documentação, apresentação e vídeo |

---

## 📋 Status — Entrega da Semana 1

- [ ] 1. Estudo do dataset Symile-MIMIC — levantamento dos dados em [`data/README.md`](data/README.md); falta redigir `docs/01-...`
- [x] 2. Organização das modalidades de dados — [`docs/02-...`](docs/02-organizacao-modalidades.md) + `src/build_subset.py`
- [ ] 3. Leitura e visualização dos dados — as 4 modalidades já carregam (`src/loaders.py`, `app/`); falta redigir `docs/03-...`
- [ ] 4. Definição da arquitetura da solução — `docs/04-...`
- [ ] 5. Análise das tecnologias — `docs/05-...`
- [x] 6. Organização do GitHub — este repositório
- [x] 7. Protótipo inicial da interface (Streamlit) — `app/`

> ⚠️ **Achado que afeta a entrega:** o material do Symile-MIMIC disponibilizado veio **incompleto** — os sinais de ECG não vieram e o tensor de radiografias está truncado (46 imagens íntegras de $4.640$). Laboratório e dados clínicos são reais; ECG é mock e a radiografia é real só nos 46 primeiros casos. Detalhes e a pendência a levar à professora em [`data/README.md`](data/README.md).

---

## 🚀 Como executar

```bash
# 1. ambiente (use python3 aqui — em algumas máquinas `python` não existe)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. apontar para os dados credenciados do Symile-MIMIC
cp .env.example .env               # e ajuste SYMILE_MIMIC_DIR

# 3. gerar o subconjunto local (150 casos, ~13 s)
python -m src.build_subset

# 4. subir a interface
python -m streamlit run app/streamlit_app.py
```

O protótipo abre em <http://localhost:8501>. Detalhes em [`app/README.md`](app/README.md).

> 🔒 O passo 2 exige **credenciamento no PhysioNet** — os dados não acompanham o repositório. Ver [`data/README.md`](data/README.md).

**Testes:**

```bash
python -m pytest tests
```

---

## 🔀 Fluxo de trabalho (branches)

Este repositório segue um fluxo baseado em **git-flow**: `main` ← `develop` ← `feature/*`.
Detalhes em [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

