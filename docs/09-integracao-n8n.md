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

### Provisionamento automático (nada de cliques no n8n)

Uma instância nova do n8n normalmente exige quatro passos manuais antes de o
webhook existir: criar o *owner* local, importar o workflow, ligar a credencial
do Google e ativar o workflow. **O container faz os quatro sozinho no boot**
(`n8n/entrypoint.sh` → `n8n/provisionar.mjs`), de forma idempotente:

| Passo | Como é resolvido |
| --- | --- |
| Owner local | Criado a partir de `CLINICALFUSION_N8N_OWNER_EMAIL` / `_PASSWORD` — conta padrão fixa, sem assistente de primeiro acesso. Não é conta na nuvem: fica só no volume `n8n_data`. |
| Workflow | `n8n/workflow-relatorio-clinico.json` importado via API REST (Webhook → converte o base64 em PDF → envia ao Google Drive). |
| Credencial do Google | Criada a partir do `.env` (service account **ou** client OAuth2 — ver abaixo). |
| Ativação | `PATCH active: true`. **É este passo que faz o path `/webhook/` existir**; sem ele o `POST` do app volta `404`. |

Reimportar não sobrescreve um workflow já existente, para não apagar ajustes
feitos na interface. Para forçar a ressincronização a partir do JSON, suba com
`CLINICALFUSION_N8N_FORCE_SYNC=1`.

### O login do Google

O usuário final nunca abre o n8n — ele usa só o Streamlit na porta 8501. Já a
autorização do Google tem dois caminhos, e a escolha decide se ainda sobra algum
clique para quem administra:

- **Service account** (`CLINICALFUSION_GDRIVE_SA_JSON`) — **zero login, nem no
  Google**. Em troca, uma restrição do próprio Google: service account não tem
  cota de armazenamento, então a pasta de destino precisa estar num **Drive
  compartilhado** onde o e-mail da service account seja editor.
- **OAuth2** (`CLINICALFUSION_GOOGLE_CLIENT_ID` / `_SECRET`) — o script já cria a
  credencial com o client preenchido; sobra **um clique, uma única vez**, em
  *Connect my account*, porque a tela de consentimento do Google não pode ser
  automatizada. O token fica no volume `n8n_data` e vale indefinidamente.

Para o token sobreviver à recriação do volume, `N8N_ENCRYPTION_KEY` está fixa no
`docker-compose.yml`. Se o volume já tiver uma chave própria (sorteada num boot
anterior), o entrypoint mantém a do volume e ignora a variável — impor outra faz
o n8n abortar em loop com *"Mismatching encryption keys"*, que aparece no log
disfarçado de `command start not found`.

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

Para ligar, subindo via `docker compose up -d`, não há nada a fazer: o workflow é
importado e **ativado** no boot (seção *Provisionamento automático*) e o
`CLINICALFUSION_N8N_WEBHOOK` já vem do próprio compose. Rodando o app fora do
Docker, defina no `.env`:

```
CLINICALFUSION_N8N_WEBHOOK=http://localhost:5678/webhook/relatorio-clinico
```

Sem essa variável a interface funciona igual, apenas sem arquivar.

### Quando o arquivamento falha

O envio nunca derruba a geração — o relatório já foi gerado (e pago) antes do
`POST`. Se o n8n estiver fora do ar ou o workflow inativo, o relatório aparece
normalmente na tela e **o usuário final não vê nada sobre isso**: arquivar é
etapa de infraestrutura, e ele não tem como agir sobre ela.

O motivo técnico vai para o log do container (`docker compose logs app`). Para
trazê-lo de volta à tela durante a operação, use `CLINICALFUSION_DEBUG=1`. Ver
`n8n.diagnostico_visivel` em `src/n8n.py` e `arquivar_no_drive` em
`app/streamlit_app.py`.

Códigos que aparecem no log e o que cada um significa:

| Resposta do n8n | Causa |
| --- | --- |
| `404` | Workflow inexistente ou **inativo** — o path `/webhook/` só existe com o workflow ativo. Era o sintoma antes do provisionamento automático. |
| `500` | O workflow rodou e falhou; quase sempre o nó do Drive sem credencial ou sem permissão na pasta. Veja a execução em *Executions*, no n8n. |
| sem resposta | Container do n8n fora do ar (`docker ps`). |

## Observações

- **Segurança:** o `.env` com as chaves fica só no host do n8n; não versionar.
- **Quota:** em lote, respeite os limites do provedor (free-tier dá 429/503); o
  CLI já falha rápido em quota esgotada, então trate o código de saída `1`.
- **Idempotência:** inclua o `paciente` + `pergunta` na chave do arquivo para não
  duplicar relatórios ao reprocessar.
