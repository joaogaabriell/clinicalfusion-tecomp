# app — Interface (Streamlit)

Interface do ClinicalFusion.

## Conteúdo

| Arquivo | Descrição |
|---------|-----------|
| `streamlit_app.py` | Aplicação Streamlit (tela inicial + visão do caso clínico) |
| `dados.py` | Ponte entre a interface e o subconjunto do Symile-MIMIC |
| `mock_data.py` | Pacientes fictícios da primeira versão — órfão, **não é mais usado** pelo app (ver Pendências) |
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
- [x] Relatório clínico estruturado (RF08/RF09), com painel de evidências (RF10);
- [x] Integração com o LLM multimodal (Gemini, via LangChain — Semana 3);
- [x] Comparação entre dois casos clínicos;
- [x] Histórico das gerações da sessão;
- [x] Modo demonstração sem chave de API (`CLINICALFUSION_DEMO=1`).

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
