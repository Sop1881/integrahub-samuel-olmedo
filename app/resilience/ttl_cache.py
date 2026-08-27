"""
Caché TTL en memoria, genérico y de un solo valor por instancia.

Deliberadamente simple: FX solo necesita cachear "la última respuesta
de tasas", no un mapa de múltiples claves — así que esto es un slot
único con expiración, no un diccionario. Vive en resilience/ porque es
un mecanismo de resiliencia/performance (evitar llamadas innecesarias
a un proveedor externo), igual que timeout_config.py y retry_policy.py.

No es thread-safe ni persistente entre procesos — para el alcance de
esta prueba (un solo proceso Uvicorn), es suficiente.
"""

import time
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._value: Optional[T] = None
        self._expires_at: float = 0.0

    def get(self) -> Optional[T]:
        """Devuelve el valor cacheado si sigue vigente, o None si expiró o nunca se seteó."""
        if self._value is not None and time.monotonic() < self._expires_at:
            return self._value
        return None

    def set(self, value: T) -> None:
        self._value = value
        self._expires_at = time.monotonic() + self._ttl_seconds
