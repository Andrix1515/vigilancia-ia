from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

class DetectionRule(ABC):
    """Clase base para reglas de detección"""
    
    @abstractmethod
    def evaluate(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evalúa y filtra detecciones según la regla"""
        pass

class ThresholdRule(DetectionRule):
    """Filtra detecciones por umbral de confianza"""
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
    
    def evaluate(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtra detecciones con confianza >= threshold"""
        return [det for det in detections if det.get('confidence', 0) >= self.threshold]

class ClassFilterRule(DetectionRule):
    """Filtra detecciones por clases permitidas"""
    
    def __init__(self, allowed_classes: List[str] = None):
        self.allowed_classes = allowed_classes or []
    
    def evaluate(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtra detecciones por clases permitidas"""
        if not self.allowed_classes:
            return detections
        
        return [
            det for det in detections 
            if det.get('class_name', '') in self.allowed_classes
        ]

class MinDetectionsRule(DetectionRule):
    """Requiere un número mínimo de detecciones"""
    
    def __init__(self, min_count: int = 1):
        self.min_count = min_count
    
    def evaluate(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Retorna detecciones solo si hay al menos min_count"""
        if len(detections) >= self.min_count:
            return detections
        return []

class CompositeRule(DetectionRule):
    """Combina múltiples reglas aplicándolas secuencialmente"""
    
    def __init__(self, rules: List[Optional[DetectionRule]]):
        self.rules = [r for r in rules if r is not None]
    
    def evaluate(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aplica todas las reglas en secuencia"""
        result = detections
        for rule in self.rules:
            result = rule.evaluate(result)
        return result

class TimeWindowRule(DetectionRule):
    """Filtra detecciones dentro de una ventana de tiempo"""
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.last_alert_time = {}
    
    def evaluate(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filtra detecciones que ocurren muy cerca en el tiempo"""
        import time
        current_time = time.time()
        filtered = []
        
        for det in detections:
            class_name = det.get('class_name', 'unknown')
            last_time = self.last_alert_time.get(class_name, 0)
            
            if current_time - last_time >= self.window_seconds:
                filtered.append(det)
                self.last_alert_time[class_name] = current_time
        
        return filtered

