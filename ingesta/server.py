import asyncio
import base64
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from urllib.parse import urlparse
import aiohttp
import yaml
from pathlib import Path
import sys

# Agregar utils al path
sys.path.append('/app/utils')
from logger import setup_logger
from helpers import image_to_base64, base64_to_image

logger = setup_logger("ingesta")

# Cargar configuración
config_path = Path("/app/config/system_config.yaml")
if config_path.exists():
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        esp32_url = config.get('esp32', {}).get('stream_url', 'http://192.168.1.100:81/stream')
        inference_url = config.get('services', {}).get('inference_url', 'http://inferencia:8001/infer')
        fps = config.get('ingesta', {}).get('fps', 1)
else:
    config = {}  # Configuración vacía por defecto
    esp32_url = "http://192.168.1.100:81/stream"
    inference_url = "http://inferencia:8001/infer"
    fps = 1

# Override con variable de entorno si existe
import os
inference_url = os.getenv('INFERENCE_URL', inference_url)

class StreamProcessor:
    def __init__(self):
        self.cap = None
        self.running = False
        self.session = None
        self.stream_method = None  # 'opencv', 'snapshot', o None
        self.snapshot_url = None

    async def initialize(self):
        self.session = aiohttp.ClientSession()
        logger.info(f"Inicializando captura desde: {esp32_url}")
        await self.detect_stream_method()

    async def detect_stream_method(self):
        """Detecta el método de captura disponible"""
        # Método 1: Intentar endpoints de snapshot primero (más confiable)
        # Para ESP32-CAM común: /capture está en puerto 80, stream en puerto 81
        parsed = urlparse(esp32_url)
        base_url_no_port = f"{parsed.scheme}://{parsed.hostname}"
        # Si la URL tiene puerto 81, intentar también puerto 80 para /capture
        if parsed.port == 81:
            base_url_port_80 = f"{parsed.scheme}://{parsed.hostname}:80"
        else:
            base_url_port_80 = base_url_no_port
            
        snapshot_paths = [
            f"{base_url_port_80}/capture",  # ESP32-CAM común (puerto 80)
            f"{base_url_no_port}/capture",  # Sin especificar puerto
            f"{esp32_url.rstrip('/stream').rstrip('/')}/capture",
            f"{esp32_url.rstrip('/')}/snapshot",
            f"{esp32_url.rstrip('/')}/jpg",
            f"{esp32_url.rstrip('/')}/jpeg",
            f"{esp32_url.rstrip('/')}/frame.jpg",
            f"{esp32_url.rstrip('/')}/cam.jpg"
        ]
        
        logger.info("Intentando detectar método de captura...")
        for snapshot_url in snapshot_paths:
            try:
                async with self.session.get(snapshot_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            self.stream_method = 'snapshot'
                            self.snapshot_url = snapshot_url
                            logger.info(f"Método detectado: Snapshot en {snapshot_url}")
                            return
            except Exception as e:
                logger.debug(f"Snapshot {snapshot_url} no disponible: {e}")
                continue
        
        # Método 2: Intentar OpenCV VideoCapture como fallback (puede fallar con URLs HTTP)
        logger.warning("Método snapshot no disponible, intentando OpenCV VideoCapture...")
        try:
            # Para streams HTTP, OpenCV puede requerir backend específico
            test_cap = cv2.VideoCapture(esp32_url, cv2.CAP_FFMPEG)
            if test_cap.isOpened():
                ret, frame = test_cap.read()
                if ret and frame is not None:
                    self.stream_method = 'opencv'
                    test_cap.release()
                    logger.info("Método detectado: OpenCV VideoCapture")
                    return
            test_cap.release()
        except Exception as e:
            logger.debug(f"OpenCV VideoCapture no disponible: {e}")
        
        # Si ambos métodos fallan, usar snapshot por defecto y dejar que el loop maneje los errores
        logger.warning("No se pudo detectar método de captura automáticamente, usando snapshot por defecto")
        self.stream_method = 'snapshot'
        # Usar el primer endpoint como intento inicial
        parsed = urlparse(esp32_url)
        if parsed.port == 81:
            self.snapshot_url = f"{parsed.scheme}://{parsed.hostname}:80/capture"
        else:
            self.snapshot_url = f"{parsed.scheme}://{parsed.hostname}/capture"

    async def start_stream(self):
        """Inicia la captura del stream"""
        if self.stream_method == 'opencv':
            try:
                self.cap = cv2.VideoCapture(esp32_url, cv2.CAP_FFMPEG)
                if not self.cap.isOpened():
                    # Si OpenCV falla, cambiar a snapshot
                    logger.warning("OpenCV falló, cambiando a método snapshot")
                    self.stream_method = 'snapshot'
                    parsed = urlparse(esp32_url)
                    if parsed.port == 81:
                        self.snapshot_url = f"{parsed.scheme}://{parsed.hostname}:80/capture"
                    else:
                        self.snapshot_url = f"{parsed.scheme}://{parsed.hostname}/capture"
                else:
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    logger.info("Stream OpenCV iniciado correctamente")
            except Exception as e:
                logger.warning(f"Error al iniciar stream OpenCV: {e}, cambiando a snapshot")
                # Cambiar a snapshot si OpenCV falla
                self.stream_method = 'snapshot'
                parsed = urlparse(esp32_url)
                if parsed.port == 81:
                    self.snapshot_url = f"{parsed.scheme}://{parsed.hostname}:80/capture"
                else:
                    self.snapshot_url = f"{parsed.scheme}://{parsed.hostname}/capture"
        
        if self.stream_method == 'snapshot':
            logger.info(f"Método snapshot listo (URL: {self.snapshot_url})")
        elif self.stream_method != 'opencv':
            raise Exception(f"Método de stream desconocido: {self.stream_method}")
        
        self.running = True

    async def process_frame(self, frame):
        """Procesa un frame y lo envía a inferencia"""
        try:
            # Convertir frame a base64
            frame_b64 = image_to_base64(frame)
            
            # Enviar a servicio de inferencia
            async with self.session.post(
                inference_url,
                json={"image": frame_b64},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.debug(f"Frame procesado: {result.get('detections', 0)} detecciones")
                    return result
                else:
                    logger.warning(f"Error en inferencia: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error procesando frame: {e}")
            return None

    async def run(self):
        """Loop principal de procesamiento"""
        await self.initialize()
        await self.start_stream()
        
        reconnect_interval = config.get('esp32', {}).get('reconnect_interval', 5)
        frame_interval = 1.0 / fps
        
        while self.running:
            try:
                # Intentar reconectar si es necesario (solo para OpenCV)
                if self.stream_method == 'opencv' and (self.cap is None or not self.cap.isOpened()):
                    logger.info(f"Intentando reconectar al stream: {esp32_url}")
                    await self.start_stream()
                
                # Leer frame según el método detectado
                frame = None
                if self.stream_method == 'opencv':
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        logger.warning("No se pudo leer frame OpenCV, reintentando conexión...")
                        if self.cap:
                            self.cap.release()
                            self.cap = None
                        await asyncio.sleep(reconnect_interval)
                        continue
                elif self.stream_method == 'snapshot':
                    try:
                        async with self.session.get(self.snapshot_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                            if resp.status == 200:
                                img_data = await resp.read()
                                from PIL import Image
                                from io import BytesIO
                                img = Image.open(BytesIO(img_data))
                                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                            else:
                                logger.warning(f"Error obteniendo snapshot: {resp.status}")
                                await asyncio.sleep(reconnect_interval)
                                continue
                    except Exception as e:
                        logger.error(f"Error leyendo snapshot: {e}")
                        await asyncio.sleep(reconnect_interval)
                        continue
                
                if frame is not None:
                    await self.process_frame(frame)
                await asyncio.sleep(frame_interval)
                
            except Exception as e:
                logger.error(f"Error en loop principal: {e}")
                if self.cap:
                    self.cap.release()
                    self.cap = None
                await asyncio.sleep(reconnect_interval)

    async def stop(self):
        """Detiene el procesamiento"""
        self.running = False
        if self.cap:
            self.cap.release()
        if self.session:
            await self.session.close()
        logger.info("Stream detenido")

processor = StreamProcessor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    asyncio.create_task(processor.run())
    yield
    # Shutdown
    await processor.stop()

app = FastAPI(
    title="Ingesta Service",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ingesta"}

@app.get("/status")
async def status():
    """Estado del servicio"""
    return {
        "running": processor.running,
        "stream_url": esp32_url,
        "inference_url": inference_url,
        "fps": fps
    }

@app.post("/frame")
async def process_single_frame(frame_data: dict):
    """Endpoint para procesar un frame individual"""
    try:
        image_b64 = frame_data.get("image")
        if not image_b64:
            raise HTTPException(status_code=400, detail="No se proporcionó imagen")
        
        frame = base64_to_image(image_b64)
        result = await processor.process_frame(frame)
        
        return JSONResponse(content=result or {"status": "error"})
    except Exception as e:
        logger.error(f"Error en /frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

