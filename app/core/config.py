"""
Configuración centralizada, leída de variables de entorno.
Ningún cliente de proveedor debe tener URLs incrustadas en el código.
"""

import os


class Settings:
    core_base_url: str = os.getenv("CORE_BASE_URL", "https://dummyjson.com")
    productos_base_url: str = os.getenv("PRODUCTOS_BASE_URL", "https://dummyjson.com")
    fx_base_url: str = os.getenv("FX_BASE_URL", "https://api.frankfurter.dev")
    # FX cambia como mucho una vez al día (ver enunciado): 1h de TTL
    # es un margen conservador que igual evita llamar a FX en cada request.
    fx_cache_ttl_seconds: float = float(os.getenv("FX_CACHE_TTL_SECONDS", "3600"))


settings = Settings()
