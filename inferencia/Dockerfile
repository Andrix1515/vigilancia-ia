FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema para OpenCV y GL
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio para modelos
RUN mkdir -p /app/models

# Copiar código
COPY service.py .
# `utils` y `config` se montan en tiempo de ejecución desde `docker-compose.yml`
# (evitamos copiar fuera del contexto de build para que `docker compose` funcione).

EXPOSE 8001

CMD ["python", "service.py"]

