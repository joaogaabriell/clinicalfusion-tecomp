# app — Interface (Streamlit)

Protótipo da interface do ClinicalFusion (item 7 da Semana 1).

## Conteúdo

| Arquivo | Descrição |
|---------|-----------|
| `streamlit_app.py` | Aplicação Streamlit (tela inicial + visão do caso clínico) |
| `mock_data.py` | Pacientes fictícios e geradores sintéticos de radiografia e ECG |
| `assets/logo.svg` | Logo do projeto |
| `assets/favicon.png` | Ícone da aba do navegador |

## Como executar

Na raiz do repositório:

```bash
pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

O app abre em <http://localhost:8501>.

## Escopo do protótipo

- [x] Tela inicial;
- [x] Seleção do paciente (barra lateral);
- [x] Visualização da radiografia;
- [x] Visualização do ECG;
- [x] Visualização dos exames laboratoriais;
- [x] Campo para perguntas em linguagem natural;
- [x] Área destinada ao relatório clínico (*placeholder*, resposta simulada).

> ⚠️ Nesta fase o app usa **dados 100% fictícios** (*mock data*) gerados em `mock_data.py` — nenhum dado real do
> Symile-MIMIC é utilizado ou versionado. A leitura dos dados reais (Semana 2) e a integração com o LLM multimodal
> (Semana 3) substituirão os mocks.
