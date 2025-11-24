# Solución para Stream del ESP32

## Problema
El ESP32 no expone un stream MJPEG directo en las rutas comunes.

## Solución Implementada

El código ahora **detecta automáticamente** el método de captura disponible:

1. **OpenCV VideoCapture**: Intenta usar `cv2.VideoCapture()` directamente
2. **Snapshot HTTP**: Si OpenCV falla, intenta endpoints de snapshot como:
   - `/snapshot`
   - `/capture`
   - `/jpg`
   - `/jpeg`
   - `/frame.jpg`
   - `/cam.jpg`

## Configuración

En `config/system_config.yaml`, usa solo la **URL base** (sin ruta):

```yaml
esp32:
  stream_url: "http://192.168.100.166"  # Sin /stream, /mjpeg, etc.
```

El sistema detectará automáticamente qué método funciona.

## Próximos Pasos

1. **Reinicia el servicio de ingesta**:
   ```powershell
   docker-compose restart ingesta
   ```

2. **Revisa los logs**:
   ```powershell
   docker-compose logs -f ingesta
   ```

3. **Busca estos mensajes**:
   - ✅ "Método detectado: OpenCV VideoCapture" → Funciona con OpenCV
   - ✅ "Método detectado: Snapshot en http://..." → Funciona con snapshot
   - ❌ "No se pudo detectar método" → Necesita más investigación

## Si Aún No Funciona

Ejecuta el script de inspección:
```powershell
.\inspeccionar_esp32.ps1
```

Este script:
- Analiza el HTML del ESP32
- Busca referencias a stream/video
- Prueba diferentes puertos
- Guarda el HTML en `esp32_page.html` para inspección manual

## Alternativa: Reprogramar ESP32

Si el ESP32 no tiene ningún método de captura disponible, necesitarás agregar uno. Las opciones más comunes son:

1. **Endpoint de snapshot** (más simple):
   ```cpp
   server.on("/snapshot", HTTP_GET, [](){
     camera_fb_t * fb = esp_camera_fb_get();
     server.send_P(200, "image/jpeg", (const char *)fb->buf, fb->len);
     esp_camera_fb_return(fb);
   });
   ```

2. **Stream MJPEG**:
   ```cpp
   server.on("/stream", HTTP_GET, [](){
     // Implementar stream MJPEG
   });
   ```

