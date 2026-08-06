# 11 — Manual de uso

> **Para quem vai avaliar o projeto.** Este documento explica como executar o
> ClinicalFusion a partir do `.zip` recebido e o que fazer em cada tela. Não é
> necessário instalar Docker, nem digitar comandos, nem configurar nada.
>
> Se você só quer começar, leia a seção 2 e pare. O resto é referência.

---

## 1. O que é

O ClinicalFusion recebe as quatro modalidades de um caso clínico — **radiografia
de tórax, ECG, exames laboratoriais e dados clínicos da admissão** — e gera, com
um clique, um relatório integrado produzido por um modelo de linguagem
multimodal (Gemini).

Os dados vêm do **Symile-MIMIC 1.0.0** (PhysioNet, acesso credenciado). A
procedência de cada modalidade é declarada na própria interface: os exames
laboratoriais, a demografia, os dados da admissão e os achados do CheXpert são
**reais**; o ECG é **sintético** e parte das radiografias também, porque o
material disponibilizado veio incompleto (detalhes em
[`../data/README.md`](../data/README.md)).

> ⚠️ Ferramenta com finalidade **exclusivamente educacional**. Não realiza
> diagnóstico médico e não substitui avaliação profissional.

---

## 2. Como executar

### 2.1 Pré-requisito único: Python 3.10 ou superior

O lançador verifica e avisa se estiver faltando. Para instalar:

| Sistema | Como instalar |
|---|---|
| **Windows** | <https://www.python.org/downloads/> — na primeira tela do instalador, **marque "Add python.exe to PATH"** |
| **macOS** | <https://www.python.org/downloads/> ou `brew install python@3.12` |
| **Ubuntu/Debian** | `sudo apt install python3 python3-venv` |
| **Fedora** | `sudo dnf install python3` |

Não é preciso nada além disso. Nenhuma biblioteca precisa ser instalada à mão.

### 2.2 Windows — `iniciar.bat`

1. Descompacte o `.zip` numa pasta (a Área de Trabalho serve).
2. Abra a pasta `ClinicalFusion`.
3. **Duplo clique** em **`iniciar.bat`**.
4. Uma janela preta (terminal) abre e mostra o progresso. **Deixe-a aberta.**
5. O navegador abre sozinho no aplicativo.

> Se o Windows exibir um aviso do SmartScreen ou do antivírus, é porque o arquivo
> veio da internet. Escolha **Mais informações → Executar assim mesmo**. O `.bat`
> é um arquivo de texto — você pode abri-lo no Bloco de Notas e ler tudo o que ele
> faz antes de executar.

### 2.3 Linux ou macOS — `iniciar.sh`

1. Descompacte o `.zip` numa pasta.
2. Abra um Terminal nessa pasta e execute:
   ```bash
   ./iniciar.sh
   ```
   Se recusar por permissão, use:
   ```bash
   bash iniciar.sh
   ```
3. O navegador abre sozinho no aplicativo.

### 2.4 O que esperar na primeira execução

```
=== ClinicalFusion ===

Python encontrado: Python 3.12.3
Criando ambiente virtual...
Instalando dependencias (so na primeira vez; leva alguns minutos)...
Dependencias prontas.

Abrindo o ClinicalFusion em http://localhost:8501
(o navegador abre sozinho; para encerrar, feche esta janela)
```

**A primeira execução leva alguns minutos e precisa de internet:** o lançador
baixa as bibliotecas do Python (cerca de 150 MB) para uma pasta `.venv` **dentro
da própria pasta do projeto**. Nada é instalado no resto do computador, e apagar
a pasta do projeto remove tudo sem deixar resíduo.

**Da segunda execução em diante abre em poucos segundos** — o lançador detecta
que as dependências já estão instaladas e vai direto ao aplicativo.

### 2.5 Como encerrar

Feche a janela do terminal, ou pressione `Ctrl+C` nela. Fechar apenas a aba do
navegador não encerra o programa.

### 2.6 Para reabrir depois

Basta dar duplo clique em `iniciar.bat` (ou rodar `./iniciar.sh`) outra vez.

---

## 3. Usando o aplicativo

### 3.1 Tela inicial

Apresenta as quatro modalidades e o fluxo da solução. Para começar, **escolha um
caso no seletor da barra lateral esquerda**.

> Se a barra lateral estiver recolhida, aproxime o mouse da borda esquerda da
> tela ou clique no ícone `»` no canto superior esquerdo.

### 3.2 Tela do caso — sete abas

Escolhido o paciente, aparecem as métricas do caso e sete abas:

| Aba | O que mostra |
|---|---|
| **Dados clínicos** | Demografia, dados da admissão, desfecho e achados do CheXpert |
| **Radiografia** | A imagem de tórax, com a posição (PA/AP/lateral) e um selo indicando se é **real** ou **placeholder** |
| **ECG** | Traçado de 12 derivações; escolha a derivação no seletor (padrão: II) |
| **Laboratório** | Os 50 exames, com valor e percentil. Exames não medidos aparecem explicitamente como ausentes |
| **Chat** | Perguntas livres sobre o caso, respondidas pelo modelo |
| **Relatório (LLM)** | **O principal — veja 3.3** |
| **Comparar 2 casos** | Análise comparativa entre dois pacientes |

### 3.3 Gerando o relatório — o fluxo principal

1. Abra a aba **Relatório (LLM)**.
2. Em **Modelo**, escolha um dos disponíveis:

   | Modelo | Quando usar |
   |---|---|
   | **`gemini-flash-lite`** | Mais rápido e mais barato. **Recomendado para começar** |
   | **`gemini-flash`** | Mais capaz, um pouco mais lento |
   | **`gemini-pro`** | Topo de linha do Google; mais lento e mais caro |
   | **`demo`** | **Relatório simulado**, sem chamar API nenhuma — todo o texto vem marcado com `[SIMULADO]`. Rede de segurança: se a chave de API estiver sem cota, permite percorrer o fluxo completo mesmo assim |

   Comparar dois modelos no mesmo caso é uma boa forma de ver a diferença de
   qualidade, latência e custo — o painel de métricas mostra os três.
3. Clique em **Gerar relatório**.
4. Aguarde. Aparece um painel de progresso descrevendo cada etapa (integração das
   modalidades, montagem do prompt multimodal, consulta ao modelo). Leva algo
   entre **5 e 30 segundos**.

O relatório traz **resumo, achados radiológicos, hipóteses diagnósticas,
justificativa e exames sugeridos**, além de um painel com **latência, tokens
consumidos e custo estimado** da inferência.

> O custo exibido é uma **estimativa calculada localmente** pelo próprio
> aplicativo (tokens × tabela de preços em `src/llm/catalogo.py`), não uma consulta
> à fatura do provedor.

### 3.4 Recursos adicionais na aba do relatório

- **Explicar para o paciente** — reescreve o relatório em linguagem simples.
- **Baixar PDF** — exporta o relatório completo.
- **Histórico** — na barra lateral, guarda os relatórios gerados na sessão.

---

## 4. De onde vêm os dados exibidos

O aplicativo escolhe a fonte automaticamente, nesta ordem:

| Situação | O que aparece |
|---|---|
| Existe `data/symile-mimic/` na pasta do projeto | Os **casos reais** do subconjunto Symile-MIMIC |
| Não existe | **Modo demonstração**: casos **fictícios**, gerados pelo próprio aplicativo na primeira abertura |

O modo demonstração existe porque o Symile-MIMIC é de acesso credenciado e sua
*Data Use Agreement* proíbe redistribuição — o aplicativo não depende de receber
dado credenciado para funcionar. Quando está ativo, um **aviso permanente aparece
na barra lateral** e cada caso se declara fictício na procedência.

### 4.1 Para usar a sua própria cópia do Symile-MIMIC

Se você tem a pasta `1.0.0` do dataset credenciado e quer gerar o subconjunto a
partir dela:

1. Crie (ou edite) um arquivo `.env` na pasta do projeto com a linha:
   ```
   SYMILE_MIMIC_DIR=C:\caminho\para\physionet.org\files\symile-mimic\1.0.0
   ```
2. Gere o subconjunto:
   ```bash
   # Windows
   .venv\Scripts\python -m src.build_subset --n-casos 150

   # Linux / macOS
   .venv/bin/python -m src.build_subset --n-casos 150
   ```
3. Reinicie o aplicativo. Os casos reais passam a ter precedência.

---

## 5. Se algo der errado

A janela do terminal **permanece aberta** com a mensagem do erro. Os casos mais
comuns:

| Mensagem no terminal | O que significa | O que fazer |
|---|---|---|
| `Python 3.10 ou superior nao encontrado` | Python ausente ou fora do PATH | Instale pelo link da seção 2.1. No Windows, marque "Add python.exe to PATH" |
| `Nao consegui criar o ambiente virtual` | Falta o módulo `venv` | Ubuntu/Debian: `sudo apt install python3-venv` |
| `A instalacao das dependencias falhou` | Sem internet, ou rede bloqueando o PyPI | Confira a conexão e execute de novo |
| `Port 8501 is already in use` | Outro programa ocupa a porta | Veja 5.1 |
| O navegador não abriu | Só a abertura automática falhou | Abra manualmente <http://localhost:8501> — o aplicativo está rodando |
| `Nenhum modelo de LLM disponível` | Chave de API ausente | Veja 5.2 |

### 5.1 Trocar a porta

**Windows** — no terminal, dentro da pasta do projeto:
```
set CLINICALFUSION_PORTA=8600
iniciar.bat
```

**Linux / macOS**:
```bash
CLINICALFUSION_PORTA=8600 ./iniciar.sh
```

Depois abra `http://localhost:8600`.

### 5.2 Chave de API

A geração de relatório com os modelos Gemini exige uma chave no arquivo `.env`,
na pasta do projeto:

```
GOOGLE_API_KEY=sua-chave
```

Obtida em <https://aistudio.google.com/apikey>. **Sem chave**, o aplicativo
continua funcionando para navegar os casos, visualizar radiografia, ECG e
laboratório — e o modelo **`demo`** ainda gera um relatório simulado, permitindo
percorrer o fluxo inteiro.

### 5.3 Começar do zero

Apague a pasta `.venv` de dentro do projeto e execute o lançador outra vez. Ele
reconstrói o ambiente. Nada fora da pasta do projeto é afetado.

---

## 6. Para quem quiser olhar por dentro

| Assunto | Onde |
|---|---|
| Visão geral e estrutura do repositório | [`../README.md`](../README.md) |
| Relatório técnico (entregável) | [`07-relatorio-tecnico.md`](07-relatorio-tecnico.md) |
| Arquitetura da solução | [`04-arquitetura-solucao.md`](04-arquitetura-solucao.md) |
| Benchmark dos modelos | [`06-benchmark-llm-multimodal.md`](06-benchmark-llm-multimodal.md) |
| Automação com n8n (desafio extra) | [`09-integracao-n8n.md`](09-integracao-n8n.md) |
| Situação dos dados e o que é real vs. sintético | [`../data/README.md`](../data/README.md) |
| Execução alternativa via Docker | [`../SETUP.md`](../SETUP.md) |

Os testes automatizados podem ser executados com:

```bash
# Windows
.venv\Scripts\python -m pytest -q

# Linux / macOS
.venv/bin/python -m pytest -q
```

### Arquivos do lançador

| Arquivo | Função |
|---|---|
| `iniciar.bat` | Lançador do Windows |
| `iniciar.sh` | Lançador de Linux e macOS |
| `abrir_navegador.py` | Abre o navegador quando o servidor começa a responder |
| `COMO-EXECUTAR.md` | Início rápido, na raiz do projeto |

Os três primeiros são arquivos de texto legíveis, e cada passo está comentado.
