# app — Interface (Streamlit)

Interface do ClinicalFusion.

## Conteúdo

| Arquivo | Descrição |
|---------|-----------|
| `streamlit_app.py` | Aplicação Streamlit (tela inicial + visão do caso clínico) |
| `dados.py` | Ponte entre a interface e o subconjunto do Symile-MIMIC |
| `mock_data.py` | Pacientes fictícios da primeira versão — **não é mais usado** pelo app |
| `assets/logo.svg` | Logo do projeto |
| `assets/favicon.png` | Ícone da aba do navegador |

## Como executar

Na raiz do repositório:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env               # e ajuste SYMILE_MIMIC_DIR
python -m src.build_subset         # gera o subconjunto (150 casos)

python -m streamlit run app/streamlit_app.py
```

O app abre em <http://localhost:8501>. Sem o subconjunto gerado, a tela inicial explica como criá-lo.

## Escopo atual

- [x] Tela inicial;
- [x] Seleção do paciente (barra lateral);
- [x] Visualização da radiografia;
- [x] Visualização do ECG;
- [x] Visualização dos exames laboratoriais;
- [x] Chat livre sobre o caso (perguntas em linguagem natural, com memória);
- [x] Relatório completo com um clique (sem caixa de pergunta);
- [x] Área destinada ao relatório clínico (*placeholder*);
- [ ] Integração com o LLM multimodal (Semana 3).

## De onde vêm os dados

O app lê os casos gerados por `python -m src.build_subset`, a partir do **Symile-MIMIC real**:

| Modalidade | Procedência |
|------------|-------------|
| Exames laboratoriais | **Real** — os 50 exames, em valor e percentil |
| Dados clínicos e demografia | **Real** — idade, sexo, raça e dados da admissão |
| Achados radiológicos | **Real** — rótulos do CheXpert |
| Radiografia | **Real** nos 46 primeiros casos; placeholder nos demais |
| ECG | **Mock** — o sinal não acompanha o material disponibilizado |

A tela mostra a procedência de cada modalidade. O porquê dos mocks está em [`../data/README.md`](../data/README.md).

> ⚠️ **Os dados reais não são versionados** (DUA do PhysioNet). Cada integrante gera o subconjunto localmente.

> ⚠️ **Uso exclusivamente educacional.** Não realiza diagnóstico médico e não substitui avaliação profissional.

## Pendências

- `mock_data.py` ficou órfão depois da ligação com os dados reais. Mantido por ora — a remoção é decisão do time.
- O relatório é um *placeholder*: exibe a estrutura do RF09 e as evidências reais do caso, sem gerar texto clínico. Quem preenche é o LLM, na Semana 3.
