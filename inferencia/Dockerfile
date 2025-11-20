FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias del sistema para OpenCV y GL
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
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
COPY ../utils /app/utils
COPY ../config /app/config

EXPOSE 8001

CMD ["python", "service.py"]

