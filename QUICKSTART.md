# Inicio Rápido

## 1. Configurar Telegram

```bash
# Editar config/telegram.env
BOT_TOKEN=tu_token_aqui
CHAT_ID=tu_chat_id_aqui
```

Para obtener el token:
1. Habla con @BotFather en Telegram
2. Crea un bot con `/newbot`
3. Copia el token

Para obtener el CHAT_ID:
1. Habla con @userinfobot
2. Copia tu ID

## 2. Configurar ESP32

Editar `config/system_config.yaml`:
```yaml
esp32:
  stream_url: "http://TU_IP_ESP32:81/stream"
```

## 3. Iniciar Sistema

```bash
docker-compose up -d
```

## 4. Verificar Servicios

- Ingesta: http://localhost:8000/health
- Inferencia: http://localhost:8001/health
- Fusion: http://localhost:8002/health
- Dashboard: http://localhost:8080

## 5. Ver Logs

```bash
docker-compose logs -f ingesta
docker-compose logs -f inferencia
docker-compose logs -f fusion
```

## Detener Sistema

```bash
docker-compose down
```

