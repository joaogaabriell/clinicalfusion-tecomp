# 09 — Integração com n8n (desafio extra)

> **Objetivo:** automatizar a geração e o arquivamento de relatórios clínicos com
> o [n8n](https://n8n.io). O código já expõe um **ponto de entrada** pronto para
> ser chamado pelo n8n; este documento descreve o fluxo. A execução exige uma
> instância n8n (local via Docker ou n8n Cloud) — por isso não foi rodada aqui.

## Ponto de entrada

O módulo `src/gerar_relatorio.py` gera o relatório de um caso e imprime **JSON**
no stdout, com código de saída `0` (sucesso) ou `1` (falha):

```bash
python -m src.gerar_relatorio \
  --paciente patient_0001 \
  --pergunta "Quais os principais achados deste caso?" \
  --modelo gemini-flash
```

Saída (resumida):

```json
{
  "paciente": "patient_0001",
  "modelo": "gemini-3.5-flash",
  "ok": true,
  "latencia_s": 14.2,
  "tokens_entrada": 2295,
  "tokens_saida": 767,
  "custo_usd": 0.002606,
  "relatorio": { "resumo": "...", "achados_radiologicos": {...}, "...": "..." }
}
```

## Fluxo n8n sugerido

```
[Trigger]  →  [Execute Command]  →  [Parse JSON]  →  [Salvar/Arquivar]  →  [Notificar]
  Cron ou       python -m            (o stdout já      Google Drive /       Slack / e-mail
  Webhook       src.gerar_relatorio  é JSON)           Notion / arquivo     com o resumo
```

Passos:

1. **Trigger** — `Cron` (lote diário de casos) ou `Webhook` (sob demanda, recebendo `paciente`, `pergunta`, `modelo` no corpo).
2. **Execute Command** — roda o CLI acima. Monte o comando com os campos do trigger:
   ```
   {{ $env.VENV_PY }} -m src.gerar_relatorio --paciente {{$json.paciente}} --pergunta "{{$json.pergunta}}" --modelo {{$json.modelo}}
   ```
   Rode com o *working directory* na raiz do projeto e com o `.venv` ativado (ou aponte `VENV_PY` para o Python do `.venv`). As chaves de API vêm do `.env` do projeto.
3. **Parse JSON** — o stdout já é JSON; use um nó `Set`/`Code` para extrair `relatorio.resumo`, `custo_usd`, etc.
4. **Arquivar** — grave o JSON (ou um PDF gerado) em Google Drive, Notion, banco ou disco. Para PDF, um segundo `Execute Command` pode chamar um script que use `src/export_pdf.py`.
5. **Notificar** — envie o resumo por Slack/e-mail; trate `ok=false` como alerta.

## Observações

- **Segurança:** o `.env` com as chaves fica só no host do n8n; não versionar.
- **Quota:** em lote, respeite os limites do provedor (free-tier dá 429/503); o
  CLI já falha rápido em quota esgotada, então trate o código de saída `1`.
- **Idempotência:** inclua o `paciente` + `pergunta` na chave do arquivo para não
  duplicar relatórios ao reprocessar.
