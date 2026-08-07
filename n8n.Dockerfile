# Estende a imagem oficial do n8n com um Python capaz de rodar
# `python -m src.gerar_relatorio` (ver docs/09-integracao-n8n.md).
# O código do projeto e o .env NÃO entram na imagem: são montados em tempo de
# execução via docker-compose.yml, para não reconstruir a imagem a cada alteração.
# O provisionamento (n8n/) entra, porque roda no ENTRYPOINT.
#
# Pinado em 1.70.1 (Alpine "normal", com apk) em vez de `latest`: a partir
# de certas versões a imagem oficial virou uma "Docker Hardened Image" sem
# gerenciador de pacotes, o que quebra o `apk add` abaixo.
FROM n8nio/n8n:1.70.1

USER root
RUN apk add --no-cache python3 py3-pip

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

ENV PATH="/opt/venv/bin:${PATH}"

# Cria o owner local, importa o workflow de arquivamento e o deixa ATIVO no primeiro
# boot. Sem isso o path /webhook/ não existe e o POST do app volta 404.
COPY n8n/provisionar.mjs n8n/workflow-relatorio-clinico.json /opt/clinicalfusion/
COPY n8n/entrypoint.sh /opt/clinicalfusion/entrypoint.sh
RUN chmod +x /opt/clinicalfusion/entrypoint.sh

USER node
ENTRYPOINT ["tini", "--", "/opt/clinicalfusion/entrypoint.sh"]
