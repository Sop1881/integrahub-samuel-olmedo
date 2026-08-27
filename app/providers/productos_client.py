"""
Cliente HTTP del proveedor PRODUCTOS
(GET https://dummyjson.com/carts/user/{id}).

Responsabilidad única: hablar HTTP con PRODUCTOS y traducir su
respuesta (o sus fallos) al vocabulario interno de excepciones/DTOs.
No decide qué hacer ante un fallo — eso es responsabilidad del
orquestador.
"""

import httpx

from app.core.config import settings
from app.core.exceptions import (
    Provider5xxError,
    ProviderClientError,
    ProviderConnectionError,
    ProviderInvalidResponseError,
    ProviderTimeoutError,
)
from app.core.http_client_factory import create_http_client
from app.models.provider_dto import ProductosResponseDTO
from app.providers.base import ProviderClient
from app.resilience.retry_policy import productos_retry_policy
from app.resilience.timeout_config import PRODUCTOS_TIMEOUT


class ProductosClient(ProviderClient[ProductosResponseDTO]):
    def __init__(self, base_url: str | None = None):
        self._base_url = base_url or settings.productos_base_url

    @productos_retry_policy
    async def fetch(self, customer_id: str) -> ProductosResponseDTO:
        url = f"{self._base_url}/carts/user/{customer_id}"

        try:
            async with create_http_client(PRODUCTOS_TIMEOUT) as client:
                response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"PRODUCTOS: timeout ({exc})") from exc
        except httpx.RequestError as exc:
            raise ProviderConnectionError(f"PRODUCTOS: error de conexión ({exc})") from exc

        if response.status_code >= 500:
            raise Provider5xxError(f"PRODUCTOS respondió {response.status_code}")

        if response.status_code >= 400:
            # A diferencia de CORE, aquí un 4xx (incluyendo un eventual
            # 404) NO tiene significado de dominio "cliente no existe"
            # — esa verificación ya la hizo CORE. Cualquier 4xx de
            # PRODUCTOS se trata simplemente como fallo no-retryable
            # del proveedor, igual que un 5xx a efectos de degradación.
            raise ProviderClientError(f"PRODUCTOS respondió {response.status_code}")

        try:
            payload = response.json()
            return ProductosResponseDTO.model_validate(payload)
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                f"PRODUCTOS: respuesta 200 con cuerpo inválido o que no cumple el schema ({exc})"
            ) from exc
