"""
Orquestador del caso de uso "perfil de cliente".

Este corte integra CORE + PRODUCTOS en paralelo. FX se sigue marcando
explícitamente como "not_implemented" en `sources` — todavía no se
llama ni afecta `partial`.

Diseño de la concurrencia: CORE y PRODUCTOS se lanzan a la vez con
`asyncio.gather(..., return_exceptions=True)`, cada uno con su propio
timeout y política de retry ya aplicados dentro de su cliente. Un
fallo de uno nunca cancela ni bloquea al otro.

Caso especial: si CORE termina en `CustomerNotFoundError` (404 —el
cliente no existe—), esto tiene prioridad absoluta sobre cualquier
resultado de PRODUCTOS, incluso si PRODUCTOS respondió con éxito: se
descarta ese resultado y se propaga el 404. Es el costo aceptado de
correr ambos en paralelo (en vez de esperar a CORE antes de llamar a
PRODUCTOS): se gasta una llamada de más en el caso 404, a cambio de
paralelismo real en el caso feliz — trade-off documentado en AI-LOG.md.
"""

import asyncio
from datetime import datetime, timezone

from app.core.exceptions import CustomerNotFoundError, ProviderError
from app.mapping.core_mapper import empty_personal_info, to_personal_info
from app.mapping.productos_mapper import to_purchase_summary
from app.models.canonical import CustomerProfile, Meta, ProfileWarning
from app.providers.core_client import CoreClient
from app.providers.productos_client import ProductosClient

_core_client = CoreClient()
_productos_client = ProductosClient()


async def get_profile(customer_id: str) -> CustomerProfile:
    warnings: list[ProfileWarning] = []
    sources: dict[str, str] = {
        "core": "ok",
        "productos": "ok",
        "fx": "not_implemented",
    }

    core_result, productos_result = await asyncio.gather(
        _core_client.fetch(customer_id),
        _productos_client.fetch(customer_id),
        return_exceptions=True,
    )

    # CORE 404 manda sobre todo lo demás: el recurso no existe, no es
    # una degradación. Se propaga tal cual para que el handler HTTP la
    # traduzca a 404 (no a partial=true), descartando lo que haya
    # devuelto PRODUCTOS.
    if isinstance(core_result, CustomerNotFoundError):
        raise core_result

    if isinstance(core_result, ProviderError):
        # CORE agotó reintentos (timeout / 5xx / conexión / respuesta
        # inválida). No se aborta el request: se degrada con
        # personalInfo vacío.
        sources["core"] = "failed"
        personal_info = empty_personal_info()
        warnings.append(
            ProfileWarning(
                provider="core",
                reason=type(core_result).__name__,
                detail=str(core_result),
            )
        )
    elif isinstance(core_result, BaseException):
        # Excepción no contemplada (no es un fallo conocido de
        # proveedor): es un bug real, no un caso de degradación —
        # se deja propagar para que se vea como lo que es.
        raise core_result
    else:
        personal_info = to_personal_info(core_result)

    if isinstance(productos_result, ProviderError):
        # PRODUCTOS agotó reintentos. Independiente de lo que haya
        # pasado con CORE: purchaseSummary completo se vuelve None (no
        # tiene sentido un objeto parcial de agregados).
        sources["productos"] = "failed"
        purchase_summary = None
        warnings.append(
            ProfileWarning(
                provider="productos",
                reason=type(productos_result).__name__,
                detail=str(productos_result),
            )
        )
    elif isinstance(productos_result, BaseException):
        raise productos_result
    else:
        purchase_summary = to_purchase_summary(productos_result)

    partial = sources["core"] == "failed" or sources["productos"] == "failed"

    return CustomerProfile(
        customerId=customer_id,
        personalInfo=personal_info,
        purchaseSummary=purchase_summary,
        meta=Meta(
            partial=partial,
            warnings=warnings,
            generatedAt=datetime.now(timezone.utc).isoformat(),
            sources=sources,
        ),
    )
