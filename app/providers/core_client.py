"""
Cliente HTTP del proveedor CORE (GET https://dummyjson.com/users/{id}).

Responsabilidad única: hablar HTTP con CORE y traducir su respuesta
(o sus fallos) al vocabulario interno de excepciones/DTOs. No decide
qué hacer ante un fallo — eso es responsabilidad del orquestador.
"""

import httpx

from app.core.config import settings
from app.core.exceptions import (
    CustomerNotFoundError,
    Provider5xxError,
    ProviderClientError,
    ProviderConnectionError,
    ProviderInvalidResponseError,
    ProviderTimeoutError,
)
from app.core.http_client_factory import create_http_client
from app.models.provider_dto import CoreUserDTO
from app.providers.base import ProviderClient
from app.resilience.retry_policy import core_retry_policy
from app.resilience.timeout_config import CORE_TIMEOUT


class CoreClient(ProviderClient[CoreUserDTO]):
    def __init__(self, base_url: str | None = None):
        self._base_url = base_url or settings.core_base_url

    @core_retry_policy
    async def fetch(self, customer_id: str) -> CoreUserDTO:
        url = f"{self._base_url}/users/{customer_id}"

        try:
            async with create_http_client(CORE_TIMEOUT) as client:
                response = await client.get(url)
        except httpx.TimeoutException as exc:
            # Cubre ConnectTimeout, ReadTimeout, WriteTimeout, PoolTimeout.
            raise ProviderTimeoutError(f"CORE: timeout ({exc})") from exc
        except httpx.RequestError as exc:
            # Cubre ConnectError, error de DNS, conexión reseteada, etc.
            raise ProviderConnectionError(f"CORE: error de conexión ({exc})") from exc

        if response.status_code == 404:
            raise CustomerNotFoundError(customer_id)

        if response.status_code >= 500:
            raise Provider5xxError(f"CORE respondió {response.status_code}")

        if response.status_code >= 400:
            # 4xx distinto de 404 (p.ej. 400) — NO se reintenta, no es
            # un caso de "no encontrado" ni un problema de disponibilidad.
            raise ProviderClientError(f"CORE respondió {response.status_code}")

        try:
            # ValueError cubre tanto json.JSONDecodeError (cuerpo no es
            # JSON) como pydantic.ValidationError (JSON válido pero que
            # no cumple el schema): en pydantic, ValidationError hereda
            # de ValueError. Ninguno de los dos casos se reintenta —no
            # es un problema de red, es un cambio de contrato del
            # proveedor— y ambos se convierten en degradación explícita
            # en vez de propagarse como un 500 no controlado.
            payload = response.json()
            return CoreUserDTO.model_validate(payload)
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                f"CORE: respuesta 200 con cuerpo inválido o que no cumple el schema ({exc})"
            ) from exc
