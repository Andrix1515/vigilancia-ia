# Sistema de Vigilancia con IA - ESP32

Sistema completo de vigilancia inteligente que procesa streams MJPEG desde ESP32, realiza detección de objetos con YOLOv8, y envía alertas a Telegram y dashboard web.

## Arquitectura

```
ESP32 (MJPEG Stream)
    ↓
[Ingesta Service:8000] → Extrae frames → Base64
    ↓
[Inferencia Service:8001] → YOLOv8n → Detecciones
    ↓
[Fusion Service:8002] → Reglas → Alertas
    ↓
Telegram Bot + [Web Dashboard:8080]
```

## Componentes

- **Ingesta (8000)**: Recibe stream MJPEG del ESP32, extrae frames y los envía a inferencia
- **Inferencia (8001)**: Carga modelo YOLOv8n, procesa frames y detecta objetos
- **Fusion (8002)**: Aplica reglas de negocio y envía alertas a Telegram
- **Web (8080)**: Dashboard para visualizar alertas y logs

## Instalación

### Prerrequisitos

- Docker y Docker Compose
- ESP32 configurado con stream MJPEG

### Configuración

1. Clonar el repositorio:
```bash
git clone <repo-url>
cd seguridad-ia-esp32
```

2. Configurar Telegram:
```bash
cp config/telegram.env.example config/telegram.env
# Editar config/telegram.env con BOT_TOKEN y CHAT_ID
```

3. Configurar ESP32 en `config/system_config.yaml`:
```yaml
esp32:
  stream_url: "http://ESP32_IP:81/stream"
```

4. Iniciar servicios:
```bash
docker-compose up -d
```

## Entrenamiento del Modelo

El sistema usa YOLOv8n pre-entrenado. Para entrenar un modelo personalizado:

```bash
# Instalar dependencias
pip install ultralytics

# Entrenar modelo
yolo detect train data=dataset.yaml model=yolov8n.pt epochs=100 imgsz=640
```

Colocar el modelo entrenado en `inferencia/models/custom.pt` y actualizar `yolov8_config.yaml`.

## Conexión ESP32

### Código ESP32 (Arduino)

```cpp
#include <WiFi.h>
#include <ESP32Camera.h>

const char* ssid = "TU_WIFI";
const char* password = "TU_PASSWORD";

void setup() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    return;
  }

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  // Iniciar servidor MJPEG en puerto 81
  // Usar librería ESP32Camera con servidor HTTP
}
```

### Configuración en el Sistema

Actualizar `config/system_config.yaml`:
```yaml
esp32:
  stream_url: "http://192.168.1.100:81/stream"
```

## Extensión del Sistema

### Agregar Nuevas Reglas de Detección

Editar `fusion/rules.py`:

```python
class CustomRule(DetectionRule):
    def evaluate(self, detections):
        # Lógica personalizada
        pass
```

### Agregar Nuevos Endpoints

Cada servicio es independiente. Agregar endpoints en:
- `ingesta/server.py` - Para nuevos streams
- `inferencia/service.py` - Para nuevos modelos
- `fusion/alert_service.py` - Para nuevos canales de alerta

### Integrar con Base de Datos

Modificar `fusion/alert_service.py` para persistir alertas:

```python
from sqlalchemy import create_engine
# Implementar persistencia
```

## Monitoreo

- Logs: `docker-compose logs -f [service_name]`
- Health checks: `http://localhost:8000/health`, `http://localhost:8001/health`, etc.
- Dashboard: `http://localhost:8080`

## Troubleshooting

1. **Stream no conecta**: Verificar IP del ESP32 y firewall
2. **Modelo no carga**: Verificar que YOLOv8n se descargue correctamente
3. **Telegram no envía**: Verificar BOT_TOKEN y CHAT_ID en `config/telegram.env`
4. **Alto uso de CPU**: Reducir FPS en `config/system_config.yaml`

## Licencia

MIT

