"""
Construcción centralizada de httpx.AsyncClient, para no repetir
configuración de timeout en cada cliente de proveedor.
"""

import httpx


def create_http_client(timeout: httpx.Timeout) -> httpx.AsyncClient:
    """Crea un AsyncClient de httpx configurado con el timeout dado."""
    return httpx.AsyncClient(timeout=timeout)
