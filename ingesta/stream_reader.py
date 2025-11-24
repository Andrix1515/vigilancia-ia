"""
Lector de stream flexible para ESP32
Soporta MJPEG stream y captura de frames individuales
"""
import cv2
import numpy as np
import aiohttp
import asyncio
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class StreamReader:
    """Lector de stream que soporta múltiples métodos"""
    
    def __init__(self, url: str, stream_type: str = "auto"):
        self.url = url
        self.stream_type = stream_type
        self.cap = None
        self.session = None
        
    async def initialize(self):
        """Inicializa la sesión HTTP"""
        self.session = aiohttp.ClientSession()
        
    async def detect_stream_type(self):
        """Detecta automáticamente el tipo de stream"""
        if self.stream_type != "auto":
            return self.stream_type
            
        # Probar si es un stream MJPEG
        try:
            self.cap = cv2.VideoCapture(self.url)
            if self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    logger.info("Stream detectado como MJPEG (OpenCV)")
                    return "mjpeg_opencv"
                self.cap.release()
                self.cap = None
        except:
            pass
        
        # Probar si hay un endpoint de snapshot
        snapshot_urls = [
            f"{self.url}/snapshot",
            f"{self.url}/capture",
            f"{self.url}/jpg",
            f"{self.url}/jpeg",
            f"{self.url}/frame.jpg",
        ]
        
        for snapshot_url in snapshot_urls:
            try:
                async with self.session.get(snapshot_url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        content_type = resp.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            logger.info(f"Stream detectado como snapshot: {snapshot_url}")
                            return "snapshot"
            except:
                continue
        
        # Probar stream MJPEG manual
        try:
            async with self.session.get(self.url, timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('Content-Type', '')
                    if 'multipart' in content_type or 'mjpeg' in content_type.lower():
                        logger.info("Stream detectado como MJPEG (HTTP)")
                        return "mjpeg_http"
        except:
            pass
        
        return None
    
    async def read_frame_mjpeg_opencv(self):
        """Lee un frame usando OpenCV VideoCapture"""
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.url)
            if not self.cap.isOpened():
                return None
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        ret, frame = self.cap.read()
        if ret and frame is not None:
            return frame
        return None
    
    async def read_frame_snapshot(self, snapshot_url: str = None):
        """Lee un frame desde un endpoint de snapshot"""
        if snapshot_url is None:
            # Intentar diferentes rutas
            for path in ["/snapshot", "/capture", "/jpg", "/jpeg", "/frame.jpg"]:
                snapshot_url = f"{self.url}{path}"
                try:
                    async with self.session.get(snapshot_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            img_data = await resp.read()
                            img = Image.open(BytesIO(img_data))
                            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                            return frame
                except:
                    continue
        else:
            try:
                async with self.session.get(snapshot_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        img_data = await resp.read()
                        img = Image.open(BytesIO(img_data))
                        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                        return frame
            except Exception as e:
                logger.error(f"Error leyendo snapshot: {e}")
        
        return None
    
    async def read_frame(self):
        """Lee un frame usando el método detectado"""
        if not hasattr(self, '_stream_type'):
            self._stream_type = await self.detect_stream_type()
            if self._stream_type is None:
                raise Exception(f"No se pudo detectar el tipo de stream para: {self.url}")
        
        if self._stream_type == "mjpeg_opencv":
            return await self.read_frame_mjpeg_opencv()
        elif self._stream_type == "snapshot":
            return await self.read_frame_snapshot()
        elif self._stream_type == "mjpeg_http":
            # Implementar parsing de MJPEG HTTP si es necesario
            return await self.read_frame_snapshot()  # Fallback a snapshot
        
        return None
    
    async def close(self):
        """Cierra los recursos"""
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.session:
            await self.session.close()
            self.session = None

