/**
 * Provisiona o n8n no boot do container, de forma idempotente:
 * owner local, credencial do Google Drive, importacao do workflow e ativacao.
 *
 * Substitui quatro passos manuais na interface do n8n. O ultimo e o critico:
 * enquanto o workflow nao esta ativo, o path /webhook/ nao existe e o POST do
 * app volta 404.
 *
 * A importacao nao sobrescreve um workflow existente, para nao apagar ajustes
 * feitos na interface; use CLINICALFUSION_N8N_FORCE_SYNC=1 para forcar.
 *
 * Toda falha aqui vira log e o processo sai 0: provisionamento nao pode impedir
 * o n8n de subir.
 */

import { readFileSync, existsSync } from 'node:fs';

const BASE = process.env.CLINICALFUSION_N8N_BASE_URL ?? 'http://localhost:5678';
const ARQUIVO_WORKFLOW =
  process.env.CLINICALFUSION_N8N_WORKFLOW_FILE ??
  '/opt/clinicalfusion/workflow-relatorio-clinico.json';

const OWNER = {
  email: process.env.CLINICALFUSION_N8N_OWNER_EMAIL ?? 'admin@clinicalfusion.local',
  firstName: process.env.CLINICALFUSION_N8N_OWNER_FIRST_NAME ?? 'ClinicalFusion',
  lastName: process.env.CLINICALFUSION_N8N_OWNER_LAST_NAME ?? 'Admin',
  password: process.env.CLINICALFUSION_N8N_OWNER_PASSWORD ?? 'ClinicalFusion2025',
};

const NOME_CREDENCIAL = 'ClinicalFusion Google Drive';

const log = (msg) => console.log(`[provisionar] ${msg}`);

let cookie = '';

const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

// Durante o boot o n8n responde 200 em qualquer rota, mas com este texto puro no
// lugar do JSON: aqui, 200 nao significa "pronto".
const AINDA_SUBINDO = 'n8n is starting up';

async function requisicao(metodo, caminho, corpo) {
  const resp = await fetch(`${BASE}/rest${caminho}`, {
    method: metodo,
    headers: {
      'Content-Type': 'application/json',
      ...(cookie ? { Cookie: cookie } : {}),
      // O n8n rejeita POST/PATCH sem Browser-Id (protecao de CSRF do proprio painel).
      'browser-id': 'clinicalfusion-provisionador',
    },
    ...(corpo ? { body: JSON.stringify(corpo) } : {}),
  });

  const setCookie = resp.headers.getSetCookie?.() ?? [];
  const auth = setCookie.find((c) => c.startsWith('n8n-auth='));
  if (auth) cookie = auth.split(';')[0];

  const texto = await resp.text();
  let json;
  try {
    json = texto ? JSON.parse(texto) : {};
  } catch {
    json = { raw: texto };
  }
  return { ok: resp.ok, status: resp.status, json, texto };
}

// Reenvia enquanto o n8n disser que ainda esta subindo.
async function api(metodo, caminho, corpo) {
  for (let i = 0; i < 60; i++) {
    const resp = await requisicao(metodo, caminho, corpo);
    if (!resp.texto?.includes(AINDA_SUBINDO)) return resp;
    await dormir(2000);
  }
  return { ok: false, status: 503, json: { raw: AINDA_SUBINDO }, texto: AINDA_SUBINDO };
}

// Pronto = JSON com `data`, nao apenas 200 (ver AINDA_SUBINDO). Ate 3 min.
async function esperarN8N() {
  for (let i = 0; i < 180; i++) {
    try {
      const resp = await requisicao('GET', '/settings');
      if (resp.ok && resp.json?.data) return true;
    } catch {
      // porta ainda fechada
    }
    await dormir(1000);
  }
  return false;
}

/**
 * Cria o owner local, ou faz login se ele ja existe.
 *
 * Owner local nao e conta na nuvem: fica so no volume n8n_data. Pre-criado a
 * partir do .env, dispensa o assistente de primeiro acesso do n8n.
 */
async function garantirOwner() {
  const setup = await api('POST', '/owner/setup', OWNER);
  if (setup.ok) {
    log(`owner criado: ${OWNER.email}`);
    return true;
  }
  // 400 "Instance owner already setup": caminho normal do 2o boot em diante.
  const login = await api('POST', '/login', {
    email: OWNER.email,
    password: OWNER.password,
  });
  if (login.ok) {
    log(`login ok: ${OWNER.email}`);
    return true;
  }
  log(
    `nao consegui autenticar (${login.status}). Se voce ja criou um owner a mao ` +
      'com outro e-mail/senha, ajuste CLINICALFUSION_N8N_OWNER_* no .env para os ' +
      'mesmos dados, ou apague o volume n8n_data para comecar limpo.',
  );
  return false;
}

/** Le a service account de um caminho de arquivo ou de JSON inline. */
function lerServiceAccount() {
  const bruto = (process.env.CLINICALFUSION_GDRIVE_SA_JSON ?? '').trim();
  if (!bruto) return null;
  try {
    const texto = bruto.startsWith('{')
      ? bruto
      : existsSync(bruto)
        ? readFileSync(bruto, 'utf8')
        : null;
    if (!texto) {
      log(`CLINICALFUSION_GDRIVE_SA_JSON aponta para um arquivo inexistente: ${bruto}`);
      return null;
    }
    const sa = JSON.parse(texto);
    if (!sa.client_email || !sa.private_key) {
      log('JSON da service account sem client_email/private_key.');
      return null;
    }
    return sa;
  } catch (erro) {
    log(`nao consegui ler a service account: ${erro.message}`);
    return null;
  }
}

/**
 * Monta a credencial do Google a partir do .env, ou null se nao houver nenhuma
 * configurada (ai o workflow entra sem credencial, para ser ligada na interface).
 *
 * Service account nao exige clique nenhum, mas precisa de um Drive compartilhado
 * porque nao tem cota propria. OAuth2 exige um unico clique em "Connect my
 * account": a tela de consentimento do Google nao e automatizavel.
 */
function montarCredencial() {
  const sa = lerServiceAccount();
  if (sa) {
    return {
      tipo: 'googleApi',
      autenticacao: 'serviceAccount',
      dados: {
        email: sa.client_email,
        privateKey: sa.private_key,
        inpersonate: Boolean(process.env.CLINICALFUSION_GDRIVE_DELEGATED_EMAIL),
        delegatedEmail: process.env.CLINICALFUSION_GDRIVE_DELEGATED_EMAIL ?? '',
      },
    };
  }

  const clientId = (process.env.CLINICALFUSION_GOOGLE_CLIENT_ID ?? '').trim();
  const clientSecret = (process.env.CLINICALFUSION_GOOGLE_CLIENT_SECRET ?? '').trim();
  if (clientId && clientSecret) {
    return {
      tipo: 'googleDriveOAuth2Api',
      autenticacao: 'oAuth2',
      dados: { clientId, clientSecret },
    };
  }

  return null;
}

async function garantirCredencial(cred) {
  const lista = await api('GET', '/credentials');
  const existentes = lista.json?.data ?? [];
  const atual = existentes.find((c) => c.name === NOME_CREDENCIAL);

  if (atual) {
    // Nao mexemos numa credencial OAuth2 existente: o PATCH apagaria o
    // oauthTokenData obtido no clique de consentimento.
    if (cred.tipo === 'googleApi') {
      await api('PATCH', `/credentials/${atual.id}`, {
        name: NOME_CREDENCIAL,
        type: cred.tipo,
        data: cred.dados,
      });
    }
    return { id: atual.id, name: NOME_CREDENCIAL };
  }

  const criada = await api('POST', '/credentials', {
    name: NOME_CREDENCIAL,
    type: cred.tipo,
    data: cred.dados,
  });
  const idCriado = criada.json?.data?.id ?? criada.json?.id;
  if (!criada.ok || !idCriado) {
    log(`falha ao criar credencial (${criada.status}): ${JSON.stringify(criada.json)}`);
    return null;
  }
  log(
    cred.tipo === 'googleApi'
      ? 'credencial de service account criada -- integracao 100% automatica.'
      : 'credencial OAuth2 criada com client id/secret. Falta UM clique, uma vez: ' +
          `abra ${BASE} > Credentials > "${NOME_CREDENCIAL}" > "Connect my account".`,
  );
  return { id: idCriado, name: NOME_CREDENCIAL };
}

function ligarCredencialNoNo(workflow, cred, referencia) {
  for (const no of workflow.nodes) {
    if (no.type !== 'n8n-nodes-base.googleDrive') continue;
    no.parameters = { ...no.parameters, authentication: cred.autenticacao };
    no.credentials = { [cred.tipo]: referencia };
  }
}

async function garantirWorkflow(cred, referencia) {
  if (!existsSync(ARQUIVO_WORKFLOW)) {
    log(`workflow nao encontrado em ${ARQUIVO_WORKFLOW}; nada a importar.`);
    return;
  }
  const desejado = JSON.parse(readFileSync(ARQUIVO_WORKFLOW, 'utf8'));
  if (cred && referencia) ligarCredencialNoNo(desejado, cred, referencia);

  const lista = await api('GET', '/workflows');
  const atual = (lista.json?.data ?? []).find((w) => w.name === desejado.name);
  const forcar = process.env.CLINICALFUSION_N8N_FORCE_SYNC === '1';

  let id;
  if (!atual) {
    const criado = await api('POST', '/workflows', {
      name: desejado.name,
      // `active` e NOT NULL e a criacao nao aceita `true`: o PATCH abaixo ativa,
      // registrando o webhook no servidor em execucao.
      active: false,
      nodes: desejado.nodes,
      connections: desejado.connections,
      settings: desejado.settings ?? { executionOrder: 'v1' },
    });
    id = criado.json?.data?.id ?? criado.json?.id;
    if (!criado.ok || !id) {
      log(`falha ao criar o workflow (${criado.status}): ${JSON.stringify(criado.json)}`);
      return;
    }
    log(`workflow "${desejado.name}" importado.`);
  } else {
    id = atual.id;
    if (forcar) {
      const detalhe = await api('GET', `/workflows/${id}`);
      await api('PATCH', `/workflows/${id}`, {
        versionId: detalhe.json?.data?.versionId,
        nodes: desejado.nodes,
        connections: desejado.connections,
        settings: desejado.settings ?? { executionOrder: 'v1' },
      });
      log(`workflow "${desejado.name}" ressincronizado (FORCE_SYNC=1).`);
    } else {
      log(`workflow "${desejado.name}" ja existe; mantido como esta.`);
    }
  }

  // Sem ativo, /webhook/relatorio-clinico responde 404.
  const detalhe = await api('GET', `/workflows/${id}`);
  if (detalhe.json?.data?.active) {
    log('workflow ja estava ativo.');
    return;
  }
  const ativado = await api('PATCH', `/workflows/${id}`, {
    versionId: detalhe.json?.data?.versionId,
    active: true,
  });
  if (ativado.ok) {
    log('workflow ATIVADO -- POST /webhook/relatorio-clinico ja responde.');
  } else {
    log(`falha ao ativar (${ativado.status}): ${JSON.stringify(ativado.json)}`);
  }
}

async function main() {
  if (!(await esperarN8N())) {
    log('n8n nao respondeu em 3 min; provisionamento abortado.');
    return;
  }
  if (!(await garantirOwner())) return;

  const cred = montarCredencial();
  let referencia = null;
  if (cred) {
    referencia = await garantirCredencial(cred);
  } else {
    log(
      'sem credencial do Google no .env (CLINICALFUSION_GDRIVE_SA_JSON ou ' +
        'CLINICALFUSION_GOOGLE_CLIENT_ID/SECRET): o no do Drive vai entrar sem ' +
        'credencial. Ligue uma na interface do n8n.',
    );
  }
  await garantirWorkflow(cred, referencia);
}

// Melhor-esforco: erro aqui nao pode derrubar o n8n.
main().catch((erro) => log(`erro inesperado: ${erro?.stack ?? erro}`));
