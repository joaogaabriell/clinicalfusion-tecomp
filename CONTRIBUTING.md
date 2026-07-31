# Guia de Contribuição — ClinicalFusion

Este documento define como a equipe trabalha no repositório: fluxo de branches, padrão de commits e processo de revisão.

---

## 🔀 Fluxo de branches (git-flow simplificado)

```
main            ← versão estável / aprovada pela professora
 └── develop    ← integração do trabalho da equipe
      └── feature/*   ← desenvolvimento de cada entrega/funcionalidade
```

### Branches permanentes

- **`main`** — contém apenas o que já foi **aprovado**. Nada é commitado direto aqui.
- **`develop`** — branch de integração. Recebe as features concluídas.

### Branches de trabalho

- **`feature/<descrição>`** — criada a partir de `develop` para cada entrega/funcionalidade.
  - Semana 1: `feature/semana-01-organizacao-repositorio`
  - Semana 2: `feature/semana-02-...` (criada após a aprovação da Semana 1)

### Ciclo de uma entrega

1. Criar a branch a partir de `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/semana-0X-descricao
   ```
2. Desenvolver, commitando em pequenos passos lógicos.
3. Abrir um **Pull Request** da `feature/*` para `develop`.
4. Após a **aprovação da professora**, integrar em `develop` e então promover para `main`:
   ```bash
   git checkout main
   git merge --no-ff develop
   git push origin main
   ```
5. Iniciar a próxima entrega criando uma nova `feature/*` a partir de `develop`.

---

## 📝 Padrão de commits

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>: <descrição no imperativo, em minúsculas>
```

**Tipos:** `feat` (nova funcionalidade), `fix` (correção), `docs` (documentação), `chore` (configuração/estrutura), `refactor`, `test`, `style`.

**Exemplos:**
```
docs: adiciona estudo do dataset Symile-MIMIC
feat: implementa leitura da radiografia de tórax
chore: cria estrutura de pastas do projeto
```

Commits devem ser **atômicos** (uma mudança lógica por commit) e feitos **na identidade de cada integrante**, para que a contribuição de todos fique registrada no histórico.

---

## 🔍 Pull Requests

- Todo PR aponta para `develop` (nunca direto para `main`).
- Descreva **o que** foi feito e **por quê**.
- Relacione o item da entrega correspondente (ex.: "Item 3 — Leitura e Visualização").
- Aguarde revisão de pelo menos um colega antes do merge.
- O **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) roda sozinho no push e no PR: suíte de testes em Python 3.10 e 3.12, `ruff` (só erros que quebram execução), validação do compose do n8n e a checagem de que nenhum dado do dataset ou chave de API entrou no repositório. Merge só com o CI verde — se ele reprovar por dados versionados, **não force**: leia a seção de dados sensíveis abaixo.

---

## 🔒 Dados sensíveis

- **Nunca** commitar dados reais do Symile-MIMIC / PhysioNet (proibido pela DUA).
- O `.gitignore` já bloqueia as pastas de dados credenciados — não force o versionamento delas.
- Chaves de API de LLMs vão em `.env` ou `.streamlit/secrets.toml` (também ignorados).

### Por que não subimos o dataset — nem para facilitar

A dúvida aparece sempre, então fica registrado o porquê. A licença que vem com o dataset é a *PhysioNet Credentialed Health Data License 1.5.0*, cláusula 3:

> *The LICENSEE will not share access to PhysioNet restricted data with anyone else.*

- **"É de graça" não é "é público".** O acesso é gratuito, mas individual: exige conta no PhysioNet, treinamento CITI e a DUA assinada. Cada integrante baixa a **própria cópia**.
- **Repositório privado não resolve.** Compartilhar com quem não é credenciado é redistribuição, mesmo dentro da equipe. O credenciamento é **nominal** — quem sobe responde pessoalmente, e a cláusula 9 mantém a obrigação mesmo após o fim do acordo.
- **O git não esquece.** Uma vez no histórico, remover exige reescrevê-lo para todo o time, e qualquer clone ou fork já feito mantém a cópia.
- **Não precisamos disso.** O `src/build_subset.py` é determinístico: mesmo `--n-casos`, mesmos casos, mesmos `case_id`. Todos trabalham sobre dados idênticos sem versionar um byte de paciente.

Guarde o dataset **fora da pasta do repositório** e aponte o `.env` para ele — ver [`SETUP.md`](SETUP.md). Se `git status` mostrar `.zip`, `.npy` ou `.csv` do dataset, mova para fora; nunca use `git add -f`.
