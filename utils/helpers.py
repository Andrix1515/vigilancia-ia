import base64
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
from typing import Union

def image_to_base64(image: np.ndarray, format: str = 'JPEG') -> str:
    """Convierte una imagen OpenCV a base64"""
    try:
        # Convertir BGR a RGB si es necesario
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image
        
        # Convertir a PIL Image
        pil_image = Image.fromarray(image_rgb)
        
        # Convertir a base64
        buffer = BytesIO()
        pil_image.save(buffer, format=format)
        img_bytes = buffer.getvalue()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return img_b64
    except Exception as e:
        raise ValueError(f"Error convirtiendo imagen a base64: {e}")

def base64_to_image(img_b64: str) -> np.ndarray:
    """Convierte una imagen base64 a OpenCV"""
    try:
        # Decodificar base64
        img_bytes = base64.b64decode(img_b64)
        
        # Convertir a numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # Decodificar imagen
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("No se pudo decodificar la imagen")
        
        return img
    except Exception as e:
        raise ValueError(f"Error convirtiendo base64 a imagen: {e}")

def resize_image(image: np.ndarray, max_size: int = 1920) -> np.ndarray:
    """Redimensiona imagen manteniendo aspect ratio"""
    height, width = image.shape[:2]
    
    if max(height, width) <= max_size:
        return image
    
    if height > width:
        new_height = max_size
        new_width = int(width * (max_size / height))
    else:
        new_width = max_size
        new_height = int(height * (max_size / width))
    
    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

def validate_image(image: Union[np.ndarray, str]) -> bool:
    """Valida que la imagen sea válida"""
    try:
        if isinstance(image, str):
            img = base64_to_image(image)
        else:
            img = image
        
        if img is None or img.size == 0:
            return False
        
        return True
    except:
        return False

