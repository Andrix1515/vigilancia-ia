import asyncio
import base64
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import aiohttp
import yaml
from pathlib import Path
import sys

# Agregar utils al path
sys.path.append('/app/utils')
from logger import setup_logger
from helpers import image_to_base64, base64_to_image

app = FastAPI(title="Ingesta Service", version="1.0.0")
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

    async def initialize(self):
        self.session = aiohttp.ClientSession()
        logger.info(f"Inicializando captura desde: {esp32_url}")

    async def start_stream(self):
        """Inicia la captura del stream MJPEG"""
        try:
            self.cap = cv2.VideoCapture(esp32_url)
            if not self.cap.isOpened():
                raise Exception(f"No se pudo abrir el stream: {esp32_url}")
            
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.running = True
            logger.info("Stream iniciado correctamente")
        except Exception as e:
            logger.error(f"Error al iniciar stream: {e}")
            raise

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
        
        frame_interval = 1.0 / fps
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("No se pudo leer frame, reintentando...")
                    await asyncio.sleep(1)
                    continue
                
                await self.process_frame(frame)
                await asyncio.sleep(frame_interval)
                
            except Exception as e:
                logger.error(f"Error en loop principal: {e}")
                await asyncio.sleep(1)

    async def stop(self):
        """Detiene el procesamiento"""
        self.running = False
        if self.cap:
            self.cap.release()
        if self.session:
            await self.session.close()
        logger.info("Stream detenido")

processor = StreamProcessor()

@app.on_event("startup")
async def startup_event():
    """Inicia el procesador de stream en background"""
    asyncio.create_task(processor.run())

@app.on_event("shutdown")
async def shutdown_event():
    """Detiene el procesador"""
    await processor.stop()

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

