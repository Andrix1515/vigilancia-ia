FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY server.py .
# `utils` y `config` se montan en tiempo de ejecución desde `docker-compose.yml`
# (evitamos copiar fuera del contexto de build para que `docker compose` funcione).

EXPOSE 8000

CMD ["python", "server.py"]

