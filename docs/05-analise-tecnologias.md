# 05 — Análise das Tecnologias

> **Objetivo do item:** analisar criticamente as tecnologias sugeridas no enunciado — vão funcionar? há alternativas melhores? — justificando as escolhas da equipe.

---

## 1. Tecnologias sugeridas no enunciado

| Camada | Tecnologia sugerida |
|--------|---------------------|
| Linguagem | Python |
| Interface | Streamlit |
| Manipulação de dados | Pandas |
| Processamento de imagens | Pillow / OpenCV |
| Visualização | Matplotlib |
| LLM multimodal | GPT-4o, Gemini 2.5 Flash, Qwen2.5-VL ou Llama 3.2 Vision |
| Framework | LangChain (opcional) |
| Versionamento | GitHub |

## 2. Análise crítica

- **Python** — linguagem certa para o projeto: ecossistema maduro de dados
  (pandas/numpy) e SDKs oficiais de todos os provedores de LLM relevantes.
  Sem alternativa razoável dado o resto da stack.
- **Streamlit** — adequado para prototipagem rápida de uma interface de
  dados com abas, tabelas e upload/seleção de casos, sem exigir
  front-end separado. Limitação conhecida: reexecuta o script a cada
  interação, o que pesa em runs de LLM — mitigado com `st.cache_data` na
  leitura dos casos e histórico em `st.session_state`.
- **Pandas** — direto: tabelas de laboratório, ECG e o índice do
  subconjunto são naturalmente tabulares.
- **Pillow vs. OpenCV** — o enunciado sugere os dois. Pillow ganhou: as
  operações necessárias (abrir PNG, converter para base64, rotação leve,
  ajuste de brilho/contraste/ruído no *augmentation*) não precisam do
  processamento de visão computacional mais pesado do OpenCV, e evitam a
  dependência binária adicional.
- **Matplotlib** — suficiente e apropriado para plotar o ECG sobre uma
  grade estilo "papel milimetrado", sem necessidade de interatividade.
- **LLM multimodal (GPT-4o / Gemini / Qwen2.5-VL / Llama 3.2 Vision)** — dos
  quatro sugeridos, só GPT-4o e Gemini têm APIs multimodais de primeira
  parte estáveis e bem documentadas para uso direto via LangChain; Qwen2.5-VL
  e Llama 3.2 Vision exigiriam um agregador de terceiros (ex.: OpenRouter)
  ou hospedagem própria. A equipe testou os quatro num script exploratório
  de comparação (ver `docs/07 §8` e a seção Resultados do relatório
  técnico) e confirmou na prática essa diferença de maturidade: GPT-4o e
  Llama 3.2 Vision falharam por limitação de crédito/endpoint do agregador,
  enquanto Gemini e Qwen2.5-VL responderam de forma consistente.
- **LangChain** — o enunciado marca como opcional; a equipe optou por usá-lo
  porque um único `chat.invoke` cobre a montagem da mensagem multimodal
  (system + texto + imagem) de forma uniforme, o que paga o custo da
  dependência extra mesmo usando um só provedor: se o projeto voltar a
  suportar múltiplos provedores, a orquestração já está pronta.
- **GitHub** — sem alternativa considerada; o fluxo segue git-flow
  (`main ← develop ← feature/*`), documentado em `CONTRIBUTING.md`.

## 3. Decisão da equipe

| Camada | Escolha da equipe | Justificativa |
|--------|-------------------|---------------|
| Linguagem | Python 3.10+ | Ecossistema de dados e SDKs dos provedores |
| Interface | Streamlit | Prototipagem rápida de app de dados, abas nativas |
| Dados | Pandas | Tabelas de laboratório, ECG e índice do subconjunto |
| Imagem | **Pillow** (não OpenCV) | Suficiente para carregar/augmentar CXR, sem a dependência pesada do OpenCV |
| Visualização | Matplotlib | Traçado do ECG sobre papel milimetrado |
| LLM multimodal | **Gemini** (`gemini-3.5-flash`, `-flash-lite`, `-pro`) via LangChain | Único provedor mantido no catálogo de produção — API estável, custo-benefício da família Flash e evita manter 3 caminhos de provedor sem cobertura de teste ao vivo (GPT-4o/Claude foram avaliados e descartados do catálogo por essa razão; ver `src/llm/catalogo.py`) |
| Framework | LangChain | Orquestração uniforme; interface (`ClienteLLM.gerar`) já preparada para reativar outros provedores |
| Versionamento | GitHub + git-flow | `main ← develop ← feature/*` |

## 4. Riscos e pontos de atenção

- **Custo/limite de API** — contas do Gemini em free-tier ou sem créditos
  esgotam cota (429) ou ficam indisponíveis (503); `com_retry`
  (`src/llm/base.py`) repete erros transitórios com backoff, mas falha
  rápido em erros permanentes de conta (quota/billing esgotados) para não
  travar a interface.
- **Acesso credenciado ao dataset** — cada integrante precisa da própria
  conta PhysioNet aprovada + DUA assinada; o subconjunto gerado localmente
  não pode ser compartilhado (ver `data/README.md`).
- **Tamanho e integridade das imagens** — só 46 radiografias reais vieram
  íntegras; o `augmentation.py` estende esse conjunto preservando os
  rótulos do CheXpert (ver `docs/06`).
- **ECG sintético** — por não haver sinal real disponibilizado, o ECG é
  sempre mock; o prompt marca isso explicitamente para o LLM não produzir
  laudo eletrocardiográfico com base em sinal falso.
- **Concentração em um único provedor de LLM** — reduz a superfície de
  manutenção, mas cria dependência de um só fornecedor; a arquitetura
  (`ClienteLLM` abstrato) mitiga o risco ao manter a reativação de outro
  provedor como uma mudança localizada, não estrutural.
