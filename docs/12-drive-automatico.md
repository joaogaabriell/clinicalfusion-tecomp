# 12 — Arquivamento automático no Google Drive

## Decisão adotada

O ClinicalFusion não leva uma conta Google pré-configurada. Não existem Client
ID, Client Secret, service account, token OAuth ou senha do Drive no código, no
`.env` ou nos inicializadores.

Cada pessoa que testar o projeto pode usar a própria conta por meio do **Google
Drive para computador**. O n8n grava o PDF em uma pasta local e o aplicativo do
Google sincroniza essa pasta com a conta que estiver conectada naquele
computador.

```text
ClinicalFusion → webhook do n8n → pasta local → Google Drive para computador
```

Se esta configuração não for feita, o sistema continua funcionando normalmente:
o relatório aparece na tela e pode ser baixado pelo botão **Baixar PDF**.

## Pré-requisitos da automação

- Docker e Docker Compose funcionando;
- Google Drive para computador instalado;
- a pessoa que está testando conectada à própria conta do Google;
- uma pasta do Drive disponível localmente, de preferência no modo espelhado ou
  marcada para uso off-line.

## 1. Preparar a pasta na própria conta

1. Abra o Google Drive para computador e entre com a conta que receberá os
   relatórios.
2. Dentro de **Meu Drive**, crie a pasta `ClinicalFusion` e, dentro dela,
   `Relatórios`.
3. Confirme que essa pasta aparece no Explorador de Arquivos do Windows ou no
   Finder do macOS e aguarde a primeira sincronização.
4. Copie o caminho local completo da pasta `Relatórios`.

A pasta pertence à conta conectada nesse computador. Ela fica privada enquanto
o próprio usuário não alterar o compartilhamento no Google Drive.

## 2. Informar o caminho ao ClinicalFusion

Abra o arquivo `.env` da raiz do projeto e adicione
`CLINICALFUSION_RELATORIOS_DIR` com o caminho copiado.

### Windows com Docker Desktop

```env
CLINICALFUSION_RELATORIOS_DIR="C:/Users/SEU_USUARIO/Meu Drive/ClinicalFusion/Relatórios"
CLINICALFUSION_N8N_WEBHOOK=http://localhost:5678/webhook/relatorio-clinico
```

### Windows com Docker Engine dentro do WSL

O caminho precisa estar na forma que a distribuição Linux enxerga:

```env
CLINICALFUSION_RELATORIOS_DIR="/mnt/c/Users/SEU_USUARIO/Meu Drive/ClinicalFusion/Relatórios"
CLINICALFUSION_N8N_WEBHOOK=http://localhost:5678/webhook/relatorio-clinico
```

Execute os comandos Docker dentro da mesma distribuição WSL onde o Engine está
rodando.

### macOS

```env
CLINICALFUSION_RELATORIOS_DIR="/Users/SEU_USUARIO/Library/CloudStorage/GoogleDrive-SUA_CONTA/Meu Drive/ClinicalFusion/Relatórios"
CLINICALFUSION_N8N_WEBHOOK=http://localhost:5678/webhook/relatorio-clinico
```

O nome exato da pasta do Drive pode variar conforme o sistema e o idioma da
conta. Use o caminho que aparece no computador; não copie literalmente os
exemplos acima.

## 3. Iniciar o arquivamento automático

Na pasta do projeto, execute:

```bash
docker compose up -d --build n8n
```

Depois inicie a interface normalmente:

- Windows: duplo clique em `iniciar.bat`;
- macOS: duplo clique em `iniciar.command`;
- Linux: `./iniciar.sh`.

O n8n cria e ativa sozinho o workflow **Relatório Clínico → pasta
sincronizada**. Não é necessário abrir o painel do n8n nem cadastrar uma conta
Google nele.

## 4. Testar

1. Abra um caso no ClinicalFusion.
2. Entre na aba **Relatório (LLM)** e gere o relatório.
3. Confirme a mensagem **Arquivado na pasta sincronizada**.
4. Verifique se o PDF apareceu na pasta local `Relatórios`.
5. Aguarde o ícone do Google Drive indicar que a sincronização terminou e
   confirme o arquivo na conta conectada.

O arquivo é gravado com um nome semelhante a
`relatorio_patient_0001_gemini-flash-lite.pdf`.

## Solução de problemas

| Sintoma | O que verificar |
|---|---|
| O relatório foi gerado, mas não apareceu na pasta | Rode `docker compose ps` e confirme que `clinicalfusion-n8n` está ativo. |
| O n8n responde HTTP 500 | Confira se a pasta existe e se `CLINICALFUSION_RELATORIOS_DIR` usa o formato correto para o Docker em uso. |
| O PDF aparece localmente, mas não no site do Drive | Confira a sessão e o estado de sincronização do Google Drive para computador. |
| O app não tenta arquivar | Confirme `CLINICALFUSION_N8N_WEBHOOK` no `.env` e reinicie o `iniciar.bat`/`iniciar.sh`. |
| A porta 5678 está ocupada | Encerre a outra instância do n8n antes de executar o Compose deste projeto. |

Para ver os logs do serviço:

```bash
docker compose logs n8n
```

## Privacidade e portabilidade

O ZIP pode ser enviado sem nenhuma credencial do Drive. A autenticação permanece
no Google Drive para computador, fora do projeto e sob controle de quem está
testando. Dessa forma, cada instalação arquiva somente na conta conectada
naquela máquina.
