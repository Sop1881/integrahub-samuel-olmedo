"""
Excepciones internas usadas para comunicar fallos entre providers/,
orchestration/ y el handler HTTP, sin filtrar detalles de httpx hacia
capas superiores.
"""


class ProviderError(Exception):
    """Excepción base de cualquier fallo de un proveedor externo."""


class ProviderTimeoutError(ProviderError):
    """El proveedor no respondió dentro del timeout configurado (retryable)."""


class ProviderConnectionError(ProviderError):
    """Error de red/conexión al intentar contactar al proveedor (retryable)."""


class Provider5xxError(ProviderError):
    """El proveedor respondió un error de servidor (5xx) (retryable)."""


class ProviderClientError(ProviderError):
    """
    El proveedor respondió un error 4xx distinto de 404 (NO retryable).
    Se deja como excepción separada de CustomerNotFoundError porque un
    404 tiene un significado de dominio propio (recurso no existe),
    mientras que otros 4xx son simplemente un error de request.
    """


class ProviderInvalidResponseError(ProviderError):
    """
    El proveedor respondió 200 pero con un cuerpo que no es JSON válido,
    o que no cumple el schema esperado (campos faltantes/tipo incorrecto).
    NO es retryable: un reintento no arregla un payload malformado —es
    la señal de que el proveedor cambió su contrato sin avisar.
    """


class CustomerNotFoundError(ProviderError):
    """
    CORE respondió 404: el cliente no existe. NO es una degradación
    (no dispara partial=true), es un caso de "recurso no encontrado"
    que el handler debe traducir a 404 HTTP.
    """

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        super().__init__(f"Cliente '{customer_id}' no encontrado en CORE")
