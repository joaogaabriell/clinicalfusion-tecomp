# 03 — Leitura e Visualização dos Dados

> **Objetivo do item:** demonstrar que cada modalidade pode ser carregada corretamente, com pelo menos um exemplo de cada, antes da integração multimodal.

---

A fronteira de leitura do subconjunto é o módulo `src/loaders.py`: a partir
dele, o formato de cada modalidade é sempre o mesmo — quatro arquivos por
paciente —, independentemente de o dado ser real ou mock (ver
[`04-arquitetura-solucao.md`](04-arquitetura-solucao.md)). A interface
(`app/streamlit_app.py`, via `app/dados.py`) consome exclusivamente essa
camada; nenhuma leitura de arquivo acontece diretamente na UI.

## 1. Radiografia de tórax

Lida com **Pillow** (`PIL.Image.open`) em `loaders.carregar_radiografia`,
retornando um objeto `Image` já pronto para exibição. A interface mostra a
imagem com `st.image(caso.radiografia, width="stretch")` na aba
**Radiografia**, ao lado dos achados do CheXpert (tabela achado → positivo/
negativo) e de um aviso indicando se aquela radiografia é **real** ou
**placeholder** — a procedência vem de `clinical_data.json["_proveniencia"]`.

## 2. ECG

Lido com **pandas** (`pd.read_csv`) em `loaders.carregar_ecg`: um
`DataFrame` de 5000 linhas com a coluna `tempo_s` e as 12 derivações
(`I, II, III, aVR, aVL, aVF, V1`–`V6`). A visualização usa **Matplotlib**
(`app/streamlit_app.py:figura_ecg`) para traçar a derivação escolhida sobre
um fundo em grade tipo "papel de ECG" (via `MultipleLocator`), renderizado
com `st.pyplot`. Um aviso fixo informa que o sinal é **sintético** (mock),
já que o material disponibilizado não trouxe ECGs reais.

## 3. Exames laboratoriais

Lidos com **pandas** em `loaders.carregar_laboratorio`: sempre as mesmas 50
linhas (`itemid`, `exame`, `valor`, `percentil`, `ausente`), incluindo os
exames não medidos na admissão. A interface exibe a tabela com
`st.dataframe`, com um alternador "Só os medidos" (usa
`loaders.exames_presentes`) e destaque para os exames em **percentil
extremo**.

## 4. Dados demográficos e clínicos

Lidos com o módulo `json` da biblioteca padrão em
`loaders.carregar_dados_clinicos`: um `dict` com `demografia` (idade, sexo,
raça/etnia), `admissao` (tipo, origem, desfecho, datas de entrada/alta) e
`radiografia.achados_chexpert`. A interface exibe esses campos na aba
**Dados clínicos**, com um aviso de que o Symile-MIMIC não traz queixa
principal, história ou comorbidades — o quadro clínico é inferido a partir
dos exames e da admissão (ver §2 de
[`02-organizacao-modalidades.md`](02-organizacao-modalidades.md)).

---

## 🧪 Como reproduzir

```bash
python -m src.build_subset --n-casos 150   # gera data/symile-mimic/
python -m streamlit run app/streamlit_app.py
```

Com o app aberto, selecione qualquer `patient_XXXX` na barra lateral: as
quatro abas (Dados clínicos, Radiografia, ECG, Laboratório) carregam as
quatro modalidades desse caso via `src/loaders.py`. Os testes
`tests/test_loaders.py` e `tests/test_dados.py` cobrem a leitura de cada
modalidade de forma automatizada.
