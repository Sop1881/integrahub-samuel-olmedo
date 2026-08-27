"""
Configuración centralizada, leída de variables de entorno.
Ningún cliente de proveedor debe tener URLs incrustadas en el código.
"""

import os


class Settings:
    core_base_url: str = os.getenv("CORE_BASE_URL", "https://dummyjson.com")


settings = Settings()
