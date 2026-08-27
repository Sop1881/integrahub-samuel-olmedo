"""
Cliente HTTP del proveedor FX
(GET https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR,GBP).

A diferencia de CORE/PRODUCTOS, FX no es por-cliente: las tasas son
las mismas para cualquier customer_id, así que se cachean en una sola
instancia compartida (ver profile_orchestrator.py) con TTL — de modo
que no se llama a FX en cada request, tal como pide el enunciado.

El parámetro `customer_id` de `fetch()` se mantiene por compatibilidad
con la interfaz común `ProviderClient`, pero no se usa: FX no depende
del cliente.
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
from app.models.provider_dto import FxRatesDTO
from app.providers.base import ProviderClient
from app.resilience.retry_policy import fx_retry_policy
from app.resilience.timeout_config import FX_TIMEOUT
from app.resilience.ttl_cache import TTLCache


class FxClient(ProviderClient[FxRatesDTO]):
    def __init__(self, base_url: str | None = None, cache: TTLCache[FxRatesDTO] | None = None):
        self._base_url = base_url or settings.fx_base_url
        self._cache = cache or TTLCache[FxRatesDTO](ttl_seconds=settings.fx_cache_ttl_seconds)

    async def fetch(self, customer_id: str = "") -> FxRatesDTO:
        cached = self._cache.get()
        if cached is not None:
            return cached

        result = await self._fetch_from_provider()
        self._cache.set(result)
        return result

    @fx_retry_policy
    async def _fetch_from_provider(self) -> FxRatesDTO:
        url = f"{self._base_url}/v1/latest?base=USD&symbols=EUR,GBP"

        try:
            async with create_http_client(FX_TIMEOUT) as client:
                response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"FX: timeout ({exc})") from exc
        except httpx.RequestError as exc:
            raise ProviderConnectionError(f"FX: error de conexión ({exc})") from exc

        if response.status_code >= 500:
            raise Provider5xxError(f"FX respondió {response.status_code}")

        if response.status_code >= 400:
            raise ProviderClientError(f"FX respondió {response.status_code}")

        try:
            payload = response.json()
            return FxRatesDTO.model_validate(payload)
        except ValueError as exc:
            raise ProviderInvalidResponseError(
                f"FX: respuesta 200 con cuerpo inválido o que no cumple el schema ({exc})"
            ) from exc
