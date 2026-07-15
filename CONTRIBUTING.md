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

---

## 🔒 Dados sensíveis

- **Nunca** commitar dados reais do Symile-MIMIC / PhysioNet (proibido pela DUA).
- O `.gitignore` já bloqueia as pastas de dados credenciados — não force o versionamento delas.
- Chaves de API de LLMs vão em `.env` ou `.streamlit/secrets.toml` (também ignorados).
