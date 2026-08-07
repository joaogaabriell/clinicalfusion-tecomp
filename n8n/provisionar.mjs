/**
 * Provisiona o n8n no boot do container, de forma idempotente:
 * owner local, importacao do workflow e ativacao.
 *
 * Substitui quatro passos manuais na interface do n8n. O ultimo e o critico:
 * enquanto o workflow nao esta ativo, o path /webhook/ nao existe e o POST do
 * app volta 404.
 *
 * O workflow e gerenciado pelo projeto e reconciliado a cada boot. Isso tambem
 * migra automaticamente a versao antiga que usava credenciais do Google.
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

const NOMES_ANTIGOS = ['Relatório Clínico → Google Drive'];

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

async function garantirWorkflow() {
  if (!existsSync(ARQUIVO_WORKFLOW)) {
    log(`workflow nao encontrado em ${ARQUIVO_WORKFLOW}; nada a importar.`);
    return;
  }
  const desejado = JSON.parse(readFileSync(ARQUIVO_WORKFLOW, 'utf8'));

  const lista = await api('GET', '/workflows');
  const atual = (lista.json?.data ?? []).find(
    (w) => w.name === desejado.name || NOMES_ANTIGOS.includes(w.name),
  );

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
    const detalheAtual = await api('GET', `/workflows/${id}`);
    if (!detalheAtual.json?.data?.versionId) {
      log(`nao consegui ler o workflow existente ${id}; sincronizacao ignorada.`);
      return;
    }
    const atualizado = await api('PATCH', `/workflows/${id}`, {
      versionId: detalheAtual.json.data.versionId,
      name: desejado.name,
      nodes: desejado.nodes,
      connections: desejado.connections,
      settings: desejado.settings ?? { executionOrder: 'v1' },
    });
    if (!atualizado.ok) {
      log(`falha ao sincronizar (${atualizado.status}): ${JSON.stringify(atualizado.json)}`);
      return;
    }
    log(`workflow "${desejado.name}" sincronizado.`);
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

  await garantirWorkflow();
}

// Melhor-esforco: erro aqui nao pode derrubar o n8n.
main().catch((erro) => log(`erro inesperado: ${erro?.stack ?? erro}`));
