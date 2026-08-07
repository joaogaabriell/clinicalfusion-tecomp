# ClinicalFusion — início rápido

## Windows

**Duplo clique em `iniciar.bat`.** Deixe a janela preta aberta; o navegador abre
sozinho.

## Linux / macOS

No macOS, dê duplo clique em **`iniciar.command`**. Se o sistema bloquear na
primeira vez, clique com o botão direito, escolha **Abrir** e confirme.

Também é possível usar o Terminal, dentro desta pasta:

```bash
./iniciar.sh
```

O navegador abre sozinho.

---

- **Pré-requisito único:** Python 3.10, 3.11 ou 3.12 — recomendamos o
  **Python 3.12**: <https://www.python.org/downloads/>
  (no Windows, marque **"Add python.exe to PATH"** no instalador).
- **A primeira execução leva alguns minutos** e precisa de internet: baixa as
  bibliotecas para uma pasta `.venv` aqui dentro, sem alterar o resto do
  computador. Depois, abre em segundos.
- **Para encerrar:** feche a janela do terminal (fechar a aba do navegador não basta).

## Preparar o ZIP para entrega

No computador de quem vai enviar, dê duplo clique em **`gerar-entrega.bat`**.
O arquivo `dist/ClinicalFusion-entrega.zip` inclui o `.env` local e a pasta
`secrets/`, quando existirem, mas exclui `.git`, `.venv`, caches e dados
credenciados do Symile-MIMIC.

O `.env` pode conter a chave do Gemini para a demonstração, mas continua ignorado
pelo Git. Compartilhe esse ZIP somente com a professora e revogue a chave depois
da avaliação.

---

📖 **Manual completo — o que fazer em cada tela, como gerar o relatório e o que
fazer se algo der errado:** [`docs/11-manual-de-uso.md`](docs/11-manual-de-uso.md)

☁️ **Opcional — arquivar automaticamente no Drive de quem estiver testando:**
[`docs/12-drive-automatico.md`](docs/12-drive-automatico.md)

⚠️ Ferramenta com finalidade **exclusivamente educacional**. Não realiza
diagnóstico médico.
