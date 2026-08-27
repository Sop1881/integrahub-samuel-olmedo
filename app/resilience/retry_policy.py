"""
Políticas de reintento con tenacity.

Regla no negociable: el retry se dispara ÚNICAMENTE ante timeout, error
de conexión o 5xx. Nunca ante un 4xx — por eso `ProviderClientError` y
`CustomerNotFoundError` NO están en la tupla de excepciones retryable:
si el cliente de un proveedor las lanza, tenacity las deja pasar sin
reintentar, tal como exige la prueba.
"""

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential, wait_fixed

from app.core.exceptions import (
    Provider5xxError,
    ProviderConnectionError,
    ProviderTimeoutError,
)

RETRYABLE_EXCEPTIONS = (ProviderTimeoutError, ProviderConnectionError, Provider5xxError)

# CORE: 2 intentos totales (1 original + 1 retry), backoff fijo de 300ms.
# Es P0 crítico pero "rápido y estable" según el enunciado — un retry
# corto es suficiente, más reintentos solo demorarían la degradación.
core_retry_policy = retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(0.3),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)

# PRODUCTOS: 3 intentos totales (1 original + 2 retries), backoff
# exponencial 300ms -> 900ms. Tan crítico como CORE para el contrato,
# pero con payload más pesado, damos un intento extra antes de degradar.
productos_retry_policy = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.3, min=0.3, max=0.9),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)

# FX: 2 intentos totales (1 original + 1 retry), backoff fijo de
# 300ms (igual que CORE). Es P1/opcional — si falla, no vale la pena
# invertir más de 1 retry en algo que no afecta partial.
fx_retry_policy = retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(0.3),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    reraise=True,
)
