# 09 — Integração com n8n (desafio extra)

## Objetivo

O n8n arquiva automaticamente o mesmo PDF produzido na interface, sem repetir a
inferência do modelo. A integração é opcional: se o serviço estiver desligado,
o relatório continua aparecendo na tela e pode ser baixado normalmente.

## Arquitetura adotada

```text
Streamlit ──POST──▶ Webhook n8n ──▶ base64 para binário ──▶ /relatorios
                                                               │
                                                               └─ pasta local do computador
```

O workflow não acessa diretamente a API do Google Drive e não recebe credenciais
Google. Quando o usuário deseja sincronização automática, `/relatorios` é
mapeado pelo Docker para uma pasta local do **Google Drive para computador**. A
conta e a sincronização ficam sob controle de quem estiver testando.

O passo a passo para ligar esse recurso está em
[`12-drive-automatico.md`](12-drive-automatico.md).

## Serviços Docker

O [`docker-compose.yml`](../docker-compose.yml) disponibiliza:

- aplicativo: <http://localhost:8501>;
- n8n: <http://localhost:5678>;
- volume persistente `n8n_data` para a configuração do n8n;
- volume `/relatorios`, cujo destino local vem de
  `CLINICALFUSION_RELATORIOS_DIR`.

Para subir toda a stack:

```bash
docker compose up -d --build
```

Para usar a interface pelos inicializadores e subir apenas a automação:

```bash
docker compose up -d --build n8n
```

Em seguida, execute `iniciar.bat`, `iniciar.command` ou `iniciar.sh`.

## Provisionamento automático

No primeiro boot, [`n8n/entrypoint.sh`](../n8n/entrypoint.sh) chama
[`n8n/provisionar.mjs`](../n8n/provisionar.mjs). O provisionador:

1. cria o owner local do n8n;
2. importa o arquivo
   [`n8n/workflow-relatorio-clinico.json`](../n8n/workflow-relatorio-clinico.json);
3. reconcilia uma instalação antiga que ainda usava o nó Google Drive;
4. ativa o workflow e registra o webhook de produção.

O workflow gerenciado pelo projeto chama-se **Relatório Clínico → pasta
sincronizada** e contém três nós:

1. **Webhook** — recebe o PDF e os metadados da interface;
2. **PDF (base64 → binário)** — valida o payload, normaliza o nome e reconstrói o
   arquivo;
3. **Salvar na pasta sincronizada** — grava o PDF em `/relatorios`.

Nenhuma etapa cria credencial Google ou solicita login no painel do n8n.

## Integração com a interface

O Compose configura automaticamente o webhook para o container do aplicativo:

```text
http://n8n:5678/webhook/relatorio-clinico
```

Quando a interface é iniciada fora do Docker pelo `.bat` ou `.sh`, o `.env`
deve conter:

```env
CLINICALFUSION_N8N_WEBHOOK=http://localhost:5678/webhook/relatorio-clinico
```

O módulo [`src/n8n.py`](../src/n8n.py) transforma o PDF em base64 e envia:

```json
{
  "paciente": "patient_0001",
  "pergunta": "",
  "modelo": "gemini-flash-lite",
  "arquivo": "relatorio_patient_0001_gemini-flash-lite.pdf",
  "pdf_base64": "JVBERi0xLjQ..."
}
```

O PDF vai pronto porque a inferência já ocorreu na interface. Dessa forma, o
arquivo arquivado é exatamente o relatório mostrado ao usuário e não há uma
segunda chamada paga ao modelo.

## Destino dos arquivos

Sem configuração adicional, o Compose usa `./relatorios` na raiz do projeto.
Essa pasta é ignorada pelo Git.

Para escolher outra pasta, defina no `.env`:

```env
CLINICALFUSION_RELATORIOS_DIR=/caminho/local/para/Relatórios
```

O caminho precisa existir e estar acessível ao Docker. Para sincronização com o
Drive, ele deve apontar para uma pasta disponibilizada localmente pelo Google
Drive para computador. Exemplos específicos de Windows, WSL e macOS estão em
[`12-drive-automatico.md`](12-drive-automatico.md).

## Tratamento de falhas

O arquivamento ocorre depois da geração do relatório. Uma falha no n8n não apaga
o resultado nem impede o download manual do PDF.

Por padrão, detalhes técnicos ficam somente no log. Para mostrá-los na interface
durante a configuração, use:

```env
CLINICALFUSION_DEBUG=1
```

| Sintoma | Causa provável |
|---|---|
| HTTP 404 | workflow ainda não foi ativado ou o n8n está iniciando |
| HTTP 500 | pasta inexistente, caminho incompatível com o Docker ou sem permissão de escrita |
| sem resposta | container `clinicalfusion-n8n` fora do ar |

Diagnóstico:

```bash
docker compose ps
docker compose logs n8n
```

## CLI para geração em lote

O módulo `src.gerar_relatorio` continua disponível para automações próprias:

```bash
python -m src.gerar_relatorio \
  --paciente patient_0001 \
  --modelo gemini-flash-lite
```

Ele imprime JSON em `stdout`. O workflow padrão da interface não usa essa rota,
pois recebe o PDF já gerado.
