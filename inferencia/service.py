import base64
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from ultralytics import YOLO
import yaml
from pathlib import Path
import sys
import aiohttp
import asyncio
from typing import List, Dict, Any

# Agregar utils al path
sys.path.append('/app/utils')
from logger import setup_logger
from helpers import base64_to_image, image_to_base64

app = FastAPI(title="Inferencia Service", version="1.0.0")
logger = setup_logger("inferencia")

# Cargar configuración
config_path = Path("/app/config/yolov8_config.yaml")
if config_path.exists():
    with open(config_path, 'r') as f:
        yolo_config = yaml.safe_load(f)
        model_path = yolo_config.get('model_path', 'yolov8n.pt')
        conf_threshold = yolo_config.get('conf_threshold', 0.25)
        iou_threshold = yolo_config.get('iou_threshold', 0.45)
else:
    model_path = 'yolov8n.pt'
    conf_threshold = 0.25
    iou_threshold = 0.45

# Cargar configuración del sistema
system_config_path = Path("/app/config/system_config.yaml")
fusion_url = "http://fusion:8002/alert"
if system_config_path.exists():
    with open(system_config_path, 'r') as f:
        system_config = yaml.safe_load(f)
        fusion_url = system_config.get('services', {}).get('fusion_url', fusion_url)

# Override con variable de entorno
import os
fusion_url = os.getenv('FUSION_URL', fusion_url)

# Cargar modelo YOLO
logger.info(f"Cargando modelo: {model_path}")
try:
    model = YOLO(model_path)
    logger.info("Modelo cargado correctamente")
except Exception as e:
    logger.error(f"Error cargando modelo: {e}")
    model = None

session = None

@app.on_event("startup")
async def startup_event():
    """Inicializa sesión HTTP"""
    global session
    session = aiohttp.ClientSession()

@app.on_event("shutdown")
async def shutdown_event():
    """Cierra sesión HTTP"""
    global session
    if session:
        await session.close()

def process_detections(results) -> List[Dict[str, Any]]:
    """Procesa resultados de YOLO a formato estándar"""
    detections = []
    
    if results and len(results) > 0:
        boxes = results[0].boxes
        for box in boxes:
            detection = {
                "class": int(box.cls[0]),
                "class_name": results[0].names[int(box.cls[0])],
                "confidence": float(box.conf[0]),
                "bbox": {
                    "x1": float(box.xyxy[0][0]),
                    "y1": float(box.xyxy[0][1]),
                    "x2": float(box.xyxy[0][2]),
                    "y2": float(box.xyxy[0][3])
                }
            }
            detections.append(detection)
    
    return detections

async def send_alert(detections: List[Dict], image_b64: str):
    """Envía alerta al servicio de fusión si hay detecciones"""
    if not detections:
        return
    
    try:
        async with session.post(
            fusion_url,
            json={
                "detections": detections,
                "image": image_b64,
                "timestamp": asyncio.get_event_loop().time()
            },
            timeout=aiohttp.ClientTimeout(total=5)
        ) as response:
            if response.status == 200:
                logger.info(f"Alerta enviada: {len(detections)} detecciones")
            else:
                logger.warning(f"Error enviando alerta: {response.status}")
    except Exception as e:
        logger.error(f"Error enviando alerta: {e}")

@app.post("/infer")
async def infer(request: dict):
    """Endpoint principal de inferencia"""
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible")
    
    try:
        # Decodificar imagen base64
        image_b64 = request.get("image")
        if not image_b64:
            raise HTTPException(status_code=400, detail="No se proporcionó imagen")
        
        frame = base64_to_image(image_b64)
        
        # Realizar inferencia
        results = model.predict(
            frame,
            conf=conf_threshold,
            iou=iou_threshold,
            verbose=False
        )
        
        # Procesar detecciones
        detections = process_detections(results)
        
        # Enviar alerta si hay detecciones
        if detections:
            await send_alert(detections, image_b64)
        
        return JSONResponse(content={
            "detections": detections,
            "count": len(detections),
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Error en inferencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    model_status = "loaded" if model is not None else "not_loaded"
    return {
        "status": "healthy",
        "service": "inferencia",
        "model": model_status
    }

@app.get("/model/info")
async def model_info():
    """Información del modelo"""
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo no disponible")
    
    return {
        "model_path": model_path,
        "conf_threshold": conf_threshold,
        "iou_threshold": iou_threshold,
        "classes": model.names if hasattr(model, 'names') else {}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

