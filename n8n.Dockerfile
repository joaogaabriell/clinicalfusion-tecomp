# Estende a imagem oficial do n8n com um Python capaz de rodar
# `python -m src.gerar_relatorio` (ver docs/09-integracao-n8n.md).
# O código do projeto e o .env NÃO entram na imagem: são montados em
# tempo de execução via docker-compose.n8n.yml, para não precisar
# reconstruir a imagem a cada alteração no código.
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
USER node
