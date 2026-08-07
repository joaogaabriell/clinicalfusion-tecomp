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
├── docs/                     # documentação
│   ├── 01-estudo-dataset-symile-mimic.md
│   ├── 02-organizacao-modalidades.md
│   ├── 03-leitura-visualizacao.md
│   ├── 04-arquitetura-solucao.md
│   ├── 05-analise-tecnologias.md
│   ├── 06-benchmark-llm-multimodal.md   # ambiente de benchmark (Semana 2/3)
│   ├── 07-relatorio-tecnico.md          # relatório técnico (entregável)
│   ├── 08-apresentacao.md               # roteiro de slides
│   ├── 09-integracao-n8n.md             # automação (desafio extra)
│   ├── 10-roteiro-video.md              # roteiro do vídeo demonstrativo (entregável)
│   ├── 11-manual-de-uso.md              # execução e uso da interface
│   └── 12-drive-automatico.md            # configuração opcional por avaliador
├── data/                     # dados (reais ficam locais/ignorados; ver data/README.md)
├── src/                      # código-fonte da aplicação
│   ├── config.py             # caminhos, specs das modalidades, metadados do MIMIC
│   ├── symile_source.py      # leitura do Symile-MIMIC bruto (credenciado)
│   ├── mock.py               # geradores sintéticos (ECG e placeholder de radiografia)
│   ├── build_subset.py       # monta o subconjunto uma-pasta-por-paciente
│   ├── loaders.py            # leitura do subconjunto (usado pela interface)
│   ├── augmentation.py       # augmentation das radiografias reais (preserva CheXpert)
│   ├── export_pdf.py         # exportação do relatório em PDF (extra)
│   ├── gerar_relatorio.py    # CLI: gera o relatório de um caso em JSON (n8n/cron)
│   ├── llm/                  # orquestração LangChain: prompt, relatório, provedores, custo
│   └── benchmark/            # benchmark ancorado no CheXpert (F1, latência, custo)
├── app/                      # interface em Streamlit
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

| Semana | Objetivo | Status |
|--------|----------|--------|
| **1** | Conhecer o dataset, selecionar os casos, organizar as modalidades, definir a arquitetura | ✅ |
| **2** | Leitura das imagens, ECGs e exames laboratoriais; interface inicial | ✅ |
| **3** | Integrar o LLM multimodal, desenvolver prompts, gerar relatórios, validar respostas | ✅ |
| 4 | Testes finais, refinamento, documentação, apresentação e vídeo | ✅ |

**Requisitos:** RF01–RF10 implementados. **Extras (+20%):** comparação de LLMs
(benchmark), painel de métricas (tempo/custo), tradução para o paciente, PDF,
comparação de 2 casos, histórico e ponto de entrada para n8n. Detalhes no
[relatório técnico](docs/07-relatorio-tecnico.md).

---

## 📋 Status — Entrega da Semana 1

- [x] 1. Estudo do dataset Symile-MIMIC — [`docs/01-...`](docs/01-estudo-dataset-symile-mimic.md) + [`data/README.md`](data/README.md)
- [x] 2. Organização das modalidades de dados — [`docs/02-...`](docs/02-organizacao-modalidades.md) + `src/build_subset.py`
- [x] 3. Leitura e visualização dos dados — [`docs/03-...`](docs/03-leitura-visualizacao.md), 4 modalidades carregando (`src/loaders.py`, `app/`)
- [x] 4. Definição da arquitetura da solução — [`docs/04-...`](docs/04-arquitetura-solucao.md)
- [x] 5. Análise das tecnologias — [`docs/05-...`](docs/05-analise-tecnologias.md)
- [x] 6. Organização do GitHub — este repositório
- [x] 7. Protótipo inicial da interface (Streamlit) — `app/`

> ⚠️ **Achado que afeta a entrega:** o material do Symile-MIMIC disponibilizado veio **incompleto** — os sinais de ECG não vieram e o tensor de radiografias está truncado (46 imagens íntegras de $4.640$). Laboratório e dados clínicos são reais; ECG é mock e a radiografia é real só nos 46 primeiros casos. Detalhes e a pendência a levar à professora em [`data/README.md`](data/README.md).

---

## 🚀 Como executar

> 📖 **Primeira vez no projeto?** Siga o [**`SETUP.md`**](SETUP.md) — passo a passo para **Windows** e **Linux/macOS**, incluindo a configuração do `.env` e os erros mais comuns.

```bash
# 1. ambiente (Windows: .venv\Scripts\Activate.ps1)
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

### Arquivamento automático no Google Drive

O projeto não inclui conta nem credencial do Google Drive. Por padrão, o
relatório aparece na tela e pode ser baixado em PDF. Para arquivar cada relatório
automaticamente no Drive da própria pessoa que está testando, siga a seção de
configuração em [`docs/12-drive-automatico.md`](docs/12-drive-automatico.md).

Esse recurso usa o n8n para gravar em uma pasta local e o Google Drive para
computador para sincronizá-la. Não exige Google Cloud, Client ID, Client Secret
ou service account.

> 🔒 O passo 2 exige **credenciamento no PhysioNet** — cada integrante baixa a própria cópia. A licença do dataset **proíbe compartilhar os dados**, inclusive entre a equipe e em repositório privado. Ver [`SETUP.md`](SETUP.md) e [`data/README.md`](data/README.md).

**Modo demonstração (sem chave de API):**

Quando as chaves não estão disponíveis (sem crédito, projeto bloqueado, sem rede), a interface pode rodar com um relatório **simulado**, para apresentar o fluxo completo:

```bash
# Windows (PowerShell)
$env:CLINICALFUSION_DEMO = "1"
python -m streamlit run app/streamlit_app.py
```

Isso adiciona o modelo `demo` ao seletor. O conteúdo é um texto fixo do [`src/llm/demo_client.py`](src/llm/demo_client.py), marcado com `[SIMULADO]` em todos os campos — **nenhum modelo é consultado** e os achados radiológicos não correspondem à imagem. Sem a variável, o modo não aparece em lugar nenhum; ele também fica fora do benchmark, que não deve comparar um texto fixo com modelos reais.

**Testes:**

```bash
python -m pytest tests
```

**Integração contínua:** todo push em `main`, `develop` e `feature/*` (e todo PR para `main`/`develop`) dispara o workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml), que roda a suíte em Python 3.10 e 3.12, passa o `ruff` nos erros que quebram execução, valida o `docker-compose.yml` e confere que **nenhum dado do Symile-MIMIC nem chave de API** foi versionado. O CI não consome cota da API: sem `GOOGLE_API_KEY`, os testes usam clientes falsos.

---

## 🔀 Fluxo de trabalho (branches)

Este repositório segue um fluxo baseado em **git-flow**: `main` ← `develop` ← `feature/*`.
Detalhes em [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

