FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar Python HTTP server
RUN pip install --no-cache-dir aiohttp

# Copiar archivos web
COPY index.html .
COPY app.js .
COPY server.py .

EXPOSE 8080

CMD ["python", "server.py"]

