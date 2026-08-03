# Imagem do app Streamlit (ver docker-compose.yml).
# O dataset (data/) fica de fora da imagem -- entra em tempo de execucao via
# bind mount, do mesmo jeito que o n8n.Dockerfile trata o codigo do projeto.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0"]
