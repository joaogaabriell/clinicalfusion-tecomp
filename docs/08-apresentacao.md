# Apresentação — ClinicalFusion (roteiro de slides, 10–15 min)

> Roteiro slide a slide. Cada bloco `---` é um slide. Os "🎙️" são notas de fala.
> Pode ser exportado para slides (ex.: Marp, Slides.com) ou apresentado direto.

---

## 1. Capa

**ClinicalFusion**
Assistente Inteligente Multimodal para Análise Integrada de Casos Clínicos com LLMs Multimodais

Equipe · Disciplina de Tópicos Especiais

🎙️ Apresentar o time e a proposta em uma frase: integrar 4 modalidades de um paciente e gerar um relatório clínico estruturado com um LLM multimodal — uso **educacional**.

---

## 2. Problema e objetivo

- Dados clínicos de um paciente vêm **fragmentados**: imagem, sinal, tabelas, texto.
- Objetivo: **integrar** radiografia + ECG + laboratório + dados clínicos, gerar um **relatório estruturado** com um clique e permitir que o médico **converse** com o modelo sobre o caso.
- Finalidade **exclusivamente educacional** — não diagnostica, não substitui o médico.

🎙️ Enfatizar o caráter educacional e o aviso de segurança presente em toda a saída.

---

## 3. Base de dados — Symile-MIMIC

- Dataset público **credenciado** (PhysioNet + CITI + DUA) — não pode ser redistribuído.
- Modalidades sincronizadas por paciente; usamos **150 casos**.
- ⚠️ **Material veio incompleto:** só 46 radiografias íntegras; ECG ausente.
  - Laboratório e clínica: **reais**. Radiografia: real em 46. ECG: **sempre mock**.
- A **procedência** de cada modalidade aparece na tela.

🎙️ Ser transparente: esse achado moldou decisões de honestidade do sistema.

---

## 4. Arquitetura (visão em camadas)

`Dados → Prompt multimodal → Orquestração LangChain → Relatório JSON → Interface / Benchmark`

- Fronteira estável: `ClienteLLM.gerar → RelatorioClinico`.
- Trocar de modelo = trocar a fábrica do chat model. Nada mais muda.

🎙️ Mostrar o diagrama Mermaid do relatório técnico (§5).

---

## 5. Dataset augmentation

- Só 46 CXR reais → geramos **variações label-preserving** (rotação, brilho, contraste, zoom, ruído).
- **Sem flip horizontal** (inverteria a lateralidade e quebraria rótulos).
- Determinístico → reprodutível. 46 → **230 imagens** avaliáveis.

🎙️ Justificar por que não inventamos imagem médica falsa nem espelhamos.

---

## 6. Integração multimodal e prompt

- As **4 modalidades** entram no prompt (ECG marcado como **sintético**).
- Saída **sempre JSON**; 14 achados CheXpert + relatório do RF09.
- **Português** em todo o texto (traduz termos do dataset em inglês); chaves CheXpert ficam em inglês (são identificadores de score).

🎙️ Mostrar o system prompt resumido e um JSON de exemplo.

---

## 7. Orquestração com LangChain

- Um cliente (`ClienteLangChain`) fala com `ChatGoogleGenerativeAI`; o catálogo de produção concentra-se no Gemini, decisão da equipe (ver discussão no relatório).
- Mesma mensagem multimodal, mesma invocação — reativar OpenAI/Anthropic é uma mudança localizada, não uma reescrita.
- Robustez: retry em erros transitórios (503/rate-limit) com `max_retries=1` interno para não multiplicar com o retry externo; falha rápido em quota/billing.

🎙️ Mencionar aprendizados: alguns modelos Gemini recusam `thinking_budget=0` na chamada (não na construção) — a lista de exceções em `langchain_client.py` foi validada com chamada real.

---

## 8. Demonstração (ao vivo)

1. Selecionar um caso (`patient_0001`, com RX real).
2. Ver as abas: clínica, radiografia, ECG, laboratório.
3. Aba **Relatório**: escolher modelo e clicar em **Gerar relatório** (sem digitar nada).
4. Ver o relatório + **painel de evidências** (RF10) + métricas (latência/tokens/custo).
5. Botões: **Explicar para o paciente**, **Baixar PDF**.
6. Aba **Chat**: perguntar algo específico sobre o caso e mostrar que o modelo mantém o fio da conversa.
7. Aba **Comparar 2 casos**.

🎙️ Ter um caso pré-testado; ter plano B (screenshots) caso a quota do provedor falhe.

---

## 9. Validação — benchmark ancorado no CheXpert

- Métrica principal: **F1** dos achados CheXpert (classe *positivo*).
- Também: acurácia, completude, **latência**, **tokens** e **custo**.
- Compara os modelos disponíveis; decide por **F1 × latência × custo**.

🎙️ Mostrar `benchmark_resultados/relatorio.md` (tabela comparativa).

---

## 10. Requisitos e extras

- **RF01–RF10**: todos implementados.
- Extras entregues: comparação de LLMs, painel de métricas (tempo/custo), tradução para o paciente, PDF, comparação de 2 casos, histórico, integração com n8n (arquivamento automático do PDF via webhook).
- Não implementado: explicação visual dos achados na radiografia (bounding boxes).

🎙️ Destacar que a comparação de LLMs (benchmark + comparação manual) já garante parte do +20%.

---

## 11. Tecnologias

Python · Streamlit · Pandas · Pillow · Matplotlib · **LangChain** · Google Gemini · GitHub (git-flow) · fpdf2.

🎙️ Justificar Pillow (em vez de OpenCV) e a decisão de concentrar o catálogo de produção só no Gemini.

---

## 12. Limitações e próximos passos

- Ground-truth **parcial** (só cobre casos com radiografia real); ECG **mock**; quota/custo de API.
- Próximos: rubrica humana da qualidade textual e explicação visual dos achados. A automação via n8n já está implementada; para sincronizar com o Drive, cada avaliador configura a própria pasta local conforme `docs/12-drive-automatico.md`.

🎙️ Ser honesto sobre limites — é um projeto educacional.

---

## 13. Encerramento

- ClinicalFusion: 4 modalidades → relatório estruturado educacional, com validação objetiva.
- 89 testes automatizados, com integração contínua no GitHub Actions; arquitetura extensível.
- Obrigado! Perguntas?

🎙️ Fechar reforçando o aviso educacional.
