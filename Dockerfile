# Imagem do app Streamlit (ver docker-compose.yml).
# O dataset (data/) fica de fora da imagem -- entra em tempo de execucao via
# bind mount somente-leitura.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address=0.0.0.0"]
