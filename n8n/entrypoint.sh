#!/bin/sh
# Entrypoint do container do n8n: reconcilia a chave de criptografia, dispara o
# provisionamento (n8n/provisionar.mjs) e entrega o controle ao entrypoint da imagem.

# Se o volume ja tem chave propria, ela vence: e a unica que decifra as
# credenciais gravadas nele. Impor outra faz o n8n abortar em loop com
# "Mismatching encryption keys", que aparece no log como "command start not
# found". Assim, N8N_ENCRYPTION_KEY vale so em volume novo -- o caso de uso dela.
if [ -n "$N8N_ENCRYPTION_KEY" ] && [ -f /home/node/.n8n/config ]; then
  CHAVE_DO_VOLUME=$(node -e '
    try {
      const c = require("fs").readFileSync("/home/node/.n8n/config", "utf8");
      process.stdout.write(JSON.parse(c).encryptionKey ?? "");
    } catch { /* config ilegivel: segue com a chave do .env */ }
  ')
  if [ -n "$CHAVE_DO_VOLUME" ] && [ "$CHAVE_DO_VOLUME" != "$N8N_ENCRYPTION_KEY" ]; then
    echo "[entrypoint] O volume n8n_data ja tem chave de criptografia propria;" \
         "mantendo a dele e ignorando N8N_ENCRYPTION_KEY (as credenciais salvas" \
         "so abrem com a chave do volume). Para adotar a chave do .env, remova o" \
         "volume: docker compose down -v"
    unset N8N_ENCRYPTION_KEY
  fi
fi

node /opt/clinicalfusion/provisionar.mjs &
exec /docker-entrypoint.sh "$@"
