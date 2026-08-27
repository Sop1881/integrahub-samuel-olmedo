"""
Interfaz común de los clientes de proveedores. El orquestador depende
de esta abstracción, no de las implementaciones concretas (Dependency
Inversion) — así se puede testear con un fake sin red, y agregar un
proveedor nuevo no obliga a tocar el orquestador salvo para invocarlo.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class ProviderClient(ABC, Generic[T]):
    @abstractmethod
    async def fetch(self, customer_id: str, request_id: str) -> T:
        """
        Obtiene los datos crudos del proveedor para un cliente dado y
        los devuelve como su DTO correspondiente.

        `request_id` se propaga como header `X-Request-Id` en la
        llamada saliente y se usa para correlacionar el log de esta
        llamada con el resto de la petición.

        Debe lanzar únicamente excepciones de app.core.exceptions
        (ProviderTimeoutError, ProviderConnectionError, Provider5xxError,
        ProviderClientError, CustomerNotFoundError) — nunca dejar escapar
        excepciones crudas de httpx hacia capas superiores.
        """
        raise NotImplementedError
