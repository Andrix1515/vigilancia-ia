FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio de logs
RUN mkdir -p /app/logs

# Copiar código
COPY alert_service.py .
COPY rules.py .
# `utils` y `config` se montan en tiempo de ejecución desde `docker-compose.yml`
# (evitamos copiar fuera del contexto de build para que `docker compose` funcione).

EXPOSE 8002

CMD ["python", "alert_service.py"]

