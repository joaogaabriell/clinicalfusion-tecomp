# 09 — Integração com n8n (desafio extra)

> **Objetivo:** automatizar a geração e o arquivamento de relatórios clínicos com
> o [n8n](https://n8n.io). O código já expõe um **ponto de entrada** pronto para
> ser chamado pelo n8n; este documento descreve o fluxo. A execução exige uma
> instância n8n (local via Docker ou n8n Cloud) — por isso não foi rodada aqui.

## Subir tudo com Docker

`docker-compose.yml` sobe o app Streamlit e o n8n juntos, num único comando:

```bash
docker compose up -d --build
```

- App: http://localhost:8501
- n8n: http://localhost:5678

A chave `GOOGLE_API_KEY` vem do `.env` da raiz (copie `.env.example` para `.env`
antes, se ainda não fez). O `CLINICALFUSION_N8N_WEBHOOK` já vem configurado
pelo próprio `docker-compose.yml` apontando para `http://n8n:5678/...` — dentro
da rede do compose os serviços se enxergam pelo nome, não por `localhost`
(que dentro do container do app apontaria para ele mesmo).

Na primeira vez que abrir `http://localhost:5678`, o n8n pede para criar um
**owner local** (nome/e-mail/senha) — isso não é uma conta na nuvem, fica salvo
só no volume `n8n_data` do container, sem verificação nenhuma.

### Importar o workflow pronto

`n8n/workflow-relatorio-clinico.json` já traz os 3 nós montados (Webhook →
converte o base64 em PDF → envia ao Google Drive). Para trazê-lo para dentro
da sua instância:

1. No n8n, **Workflows → Import from File** e selecione
   `n8n/workflow-relatorio-clinico.json`.
2. Abra o nó **Google Drive** e crie/selecione a credencial
   (**Create New Credential → Google Drive OAuth2 API**) — esse é o único
   passo que exige um clique manual de autorização no navegador (exigência do
   próprio Google, não dá para pular).
3. Ative o workflow (chave **Active**, canto superior direito).

Depois disso o fluxo já fica completo: o app manda o PDF pronto para o
webhook, e o n8n só arquiva no Drive.

## Ponto de entrada

O módulo `src/gerar_relatorio.py` gera o relatório de um caso e imprime **JSON**
no stdout, com código de saída `0` (sucesso) ou `1` (falha):

```bash
python -m src.gerar_relatorio \
  --paciente patient_0001 \
  --modelo gemini-flash-lite
```

> `--pergunta` é **opcional**: sem ela o modelo produz a análise completa do caso —
> o mesmo fluxo da interface, onde o relatório sai com um clique. Passe uma
> pergunta apenas quando quiser orientar o recorte da análise.

> Sem chave de API válida, use `--modelo demo`: devolve um relatório **simulado**
> (marcado com `[SIMULADO]`, sem chamar API) para demonstrar o fluxo do n8n de
> ponta a ponta. Exige `CLINICALFUSION_DEMO=1` — já definida no
> `docker-compose.yml`.

Saída (resumida):

```json
{
  "paciente": "patient_0001",
  "modelo": "gemini-2.0-flash-lite",
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

## Arquivamento automático a partir da interface

Além do fluxo acima (disparado à mão no n8n), a interface arquiva sozinha: ao gerar um
relatório, ela manda o PDF pronto para um segundo workflow, que só faz o upload.

```
[Streamlit]  ──POST──▶  [Webhook]  →  [Code]  →  [Google Drive]
 gera e paga             /webhook/     base64      pasta
 a inferência            relatorio-    → binário    "ClinicalFusion - Relatorios"
                         clinico
```

**Por que o PDF vai pronto, em vez de o n8n rodar o CLI:** o relatório já foi gerado (e
pago) na interface. Se o workflow chamasse o LLM de novo, seriam duas cobranças e dois
textos possivelmente diferentes — o arquivo no Drive não seria o mesmo que está na tela.

Para ligar:

1. No n8n, deixe o workflow **"App → Google Drive (webhook)" ativo** (chave *Active*). A URL
   de produção (`/webhook/...`) só responde com o workflow ativo — se estiver inativo, o
   `POST` volta `404`, e é isso que a interface reporta.
2. No `.env`, defina:
   ```
   CLINICALFUSION_N8N_WEBHOOK=http://localhost:5678/webhook/relatorio-clinico
   ```

Sem essa variável a interface funciona igual, apenas sem arquivar. O envio nunca derruba a
geração: se o n8n estiver fora do ar, o relatório aparece normalmente e a tela mostra um
aviso de que não foi arquivado (`src/n8n.py` e `arquivar_no_drive` em `app/streamlit_app.py`).

## Observações

- **Segurança:** o `.env` com as chaves fica só no host do n8n; não versionar.
- **Quota:** em lote, respeite os limites do provedor (free-tier dá 429/503); o
  CLI já falha rápido em quota esgotada, então trate o código de saída `1`.
- **Idempotência:** inclua o `paciente` + `pergunta` na chave do arquivo para não
  duplicar relatórios ao reprocessar.
