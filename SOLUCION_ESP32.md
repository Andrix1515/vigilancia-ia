# Solución Encontrada para ESP32-CAM

## Análisis del HTML del ESP32

Después de analizar el código HTML del ESP32, encontré las siguientes rutas:

### Rutas Disponibles:

1. **Stream MJPEG**: `http://192.168.100.166:81/stream`
   - Puerto: 81
   - Tipo: Stream continuo MJPEG
   - Uso: Para video en tiempo real

2. **Snapshot/Capture**: `http://192.168.100.166/capture`
   - Puerto: 80 (por defecto)
   - Tipo: Imagen JPEG individual
   - Uso: Para capturas de frames individuales

## Configuración Actualizada

La configuración ya está actualizada en `config/system_config.yaml`:

```yaml
esp32:
  stream_url: "http://192.168.100.166:81/stream"
```

## Cómo Funciona Ahora

El código intentará en este orden:

1. **OpenCV VideoCapture** con la URL configurada (`:81/stream`)
   - Si funciona, usa stream MJPEG continuo
   - Más eficiente para video en tiempo real

2. **Snapshot HTTP** (`/capture` en puerto 80)
   - Si OpenCV falla, usa capturas individuales
   - Hace una petición HTTP por cada frame
   - Funciona pero es menos eficiente

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
   - ✅ "Método detectado: OpenCV VideoCapture" → Usando stream MJPEG
   - ✅ "Stream OpenCV iniciado correctamente" → ¡Funcionando!
   - ✅ "Método detectado: Snapshot en http://..." → Usando capturas individuales

## Si Aún No Funciona

Si OpenCV VideoCapture no funciona con `:81/stream`, el sistema automáticamente usará el método de snapshot (`/capture`), que debería funcionar sin problemas.

## No Necesitas Reprogramar

El ESP32 ya tiene todo lo necesario:
- ✅ Stream MJPEG en puerto 81
- ✅ Endpoint de captura en puerto 80
- ✅ Interfaz web funcional

Solo necesitabas la configuración correcta, que ya está actualizada.

