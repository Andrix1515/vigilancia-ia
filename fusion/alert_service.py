import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import sys
import yaml
import os
from typing import List, Dict, Any

# Agregar utils y rules al path
sys.path.append('/app/utils')
sys.path.append('/app')
from logger import setup_logger
from rules import DetectionRule, ThresholdRule, ClassFilterRule, CompositeRule

app = FastAPI(title="Fusion Service", version="1.0.0")
logger = setup_logger("fusion")

# Cargar configuración
config_path = Path("/app/config/system_config.yaml")
if config_path.exists():
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
        alert_threshold = config.get('fusion', {}).get('alert_threshold', 0.5)
        enabled_classes = config.get('fusion', {}).get('enabled_classes', [])
else:
    alert_threshold = 0.5
    enabled_classes = []

# Cargar configuración de Telegram
telegram_token = os.getenv('BOT_TOKEN', '')
telegram_chat_id = os.getenv('CHAT_ID', '')

# Directorio de logs
logs_dir = Path("/app/logs")
logs_dir.mkdir(exist_ok=True)
log_file = logs_dir / "alerts.jsonl"

# Configurar reglas de detección
rules = CompositeRule([
    ThresholdRule(threshold=alert_threshold),
    ClassFilterRule(allowed_classes=enabled_classes) if enabled_classes else None
])
rules = CompositeRule([r for r in rules.rules if r is not None])

async def send_telegram_alert(detections: List[Dict], image_b64: str = None):
    """Envía alerta a Telegram"""
    if not telegram_token or not telegram_chat_id:
        logger.warning("Telegram no configurado")
        return False
    
    try:
        import aiohttp
        
        # Preparar mensaje
        class_counts = {}
        for det in detections:
            class_name = det.get('class_name', 'unknown')
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        message = "🚨 ALERTA DE DETECCIÓN\n\n"
        message += f"📊 Detecciones: {len(detections)}\n"
        for class_name, count in class_counts.items():
            message += f"  • {class_name}: {count}\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Enviar mensaje de texto
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "chat_id": telegram_chat_id,
                "text": message
            }) as response:
                if response.status == 200:
                    logger.info("Alerta enviada a Telegram")
                    
                    # Si hay imagen, enviarla
                    if image_b64:
                        photo_url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
                        import base64
                        from io import BytesIO
                        from PIL import Image
                        
                        image_data = base64.b64decode(image_b64)
                        image = Image.open(BytesIO(image_data))
                        bio = BytesIO()
                        image.save(bio, format='JPEG')
                        bio.seek(0)
                        
                        form_data = aiohttp.FormData()
                        form_data.add_field('chat_id', telegram_chat_id)
                        form_data.add_field('photo', bio, filename='detection.jpg')
                        
                        async with session.post(photo_url, data=form_data) as photo_response:
                            if photo_response.status == 200:
                                logger.info("Imagen enviada a Telegram")
                    
                    return True
                else:
                    logger.error(f"Error enviando a Telegram: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Error en Telegram: {e}")
        return False

def log_alert(detections: List[Dict], metadata: Dict = None):
    """Registra alerta en archivo de logs"""
    try:
        alert_entry = {
            "timestamp": datetime.now().isoformat(),
            "detections": detections,
            "count": len(detections),
            "metadata": metadata or {}
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(alert_entry) + '\n')
        
        logger.info(f"Alerta registrada: {len(detections)} detecciones")
    except Exception as e:
        logger.error(f"Error registrando alerta: {e}")

@app.post("/alert")
async def alert(request: dict):
    """Endpoint principal de alertas"""
    try:
        detections = request.get("detections", [])
        image_b64 = request.get("image", "")
        timestamp = request.get("timestamp", asyncio.get_event_loop().time())
        
        if not detections:
            return JSONResponse(content={"status": "no_detections"})
        
        # Aplicar reglas de detección
        filtered_detections = rules.evaluate(detections)
        
        if not filtered_detections:
            logger.debug("Detecciones filtradas por reglas")
            return JSONResponse(content={"status": "filtered"})
        
        # Registrar alerta
        log_alert(filtered_detections, {"timestamp": timestamp})
        
        # Enviar a Telegram
        await send_telegram_alert(filtered_detections, image_b64)
        
        return JSONResponse(content={
            "status": "alert_sent",
            "detections_count": len(filtered_detections)
        })
        
    except Exception as e:
        logger.error(f"Error procesando alerta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check endpoint"""
    telegram_configured = bool(telegram_token and telegram_chat_id)
    return {
        "status": "healthy",
        "service": "fusion",
        "telegram_configured": telegram_configured
    }

@app.get("/alerts")
async def get_alerts(limit: int = 100):
    """Obtiene alertas recientes"""
    try:
        alerts = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        alerts.append(json.loads(line.strip()))
                    except:
                        continue
        
        return JSONResponse(content={
            "alerts": alerts,
            "count": len(alerts)
        })
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def stats():
    """Estadísticas de alertas"""
    try:
        stats_data = {
            "total_alerts": 0,
            "class_counts": {},
            "last_alert": None
        }
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                for line in f:
                    try:
                        alert = json.loads(line.strip())
                        stats_data["total_alerts"] += 1
                        
                        for det in alert.get("detections", []):
                            class_name = det.get("class_name", "unknown")
                            stats_data["class_counts"][class_name] = \
                                stats_data["class_counts"].get(class_name, 0) + 1
                        
                        if not stats_data["last_alert"]:
                            stats_data["last_alert"] = alert.get("timestamp")
                    except:
                        continue
        
        return JSONResponse(content=stats_data)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

