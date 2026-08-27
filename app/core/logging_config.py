"""
Logging estructurado mínimo — sin dependencias nuevas (usa el módulo
estándar `logging`). Cada llamada a un proveedor externo emite UNA
línea JSON con requestId, provider, result y latencyMs, sin importar
cuántos reintentos internos haya hecho tenacity: la latencia reportada
es el tiempo total observado por el llamador (reintentos incluidos).
"""

import json
import logging

logger = logging.getLogger("integrahub")


def configure_logging() -> None:
    """Configura el logger raíz una sola vez, al arrancar la app."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_provider_call(
    request_id: str,
    provider: str,
    result: str,
    latency_ms: float,
    **extra: object,
) -> None:
    payload = {
        "requestId": request_id,
        "provider": provider,
        "result": result,
        "latencyMs": round(latency_ms, 1),
        **extra,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
