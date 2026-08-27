"""
Orquestador del caso de uso "perfil de cliente".

Este corte integra CORE + PRODUCTOS en paralelo, y FX de forma
condicional y secuencial después de resolver ambos.

Diseño de la concurrencia CORE/PRODUCTOS: se lanzan a la vez con
`asyncio.gather(..., return_exceptions=True)`, cada uno con su propio
timeout y política de retry ya aplicados dentro de su cliente. Un
fallo de uno nunca cancela ni bloquea al otro.

Caso especial: si CORE termina en `CustomerNotFoundError` (404 —el
cliente no existe—), esto tiene prioridad absoluta sobre cualquier
resultado de PRODUCTOS, incluso si PRODUCTOS respondió con éxito: se
descarta ese resultado y se propaga el 404. Es el costo aceptado de
correr ambos en paralelo (en vez de esperar a CORE antes de llamar a
PRODUCTOS): se gasta una llamada de más en el caso 404, a cambio de
paralelismo real en el caso feliz.

FX es distinto: depende del resultado de PRODUCTOS (necesita
`totalSpentUSD` para convertir) y es P1/opcional, así que se resuelve
después del gather, solo si se pidió `convert=true` y PRODUCTOS tuvo
éxito. Un fallo de FX nunca convierte la respuesta en error ni activa
`partial` — solo deja `convertedAmounts` ausente.
"""

import asyncio
from datetime import datetime, timezone

from app.core.exceptions import CustomerNotFoundError, ProviderError
from app.mapping.core_mapper import empty_personal_info, to_personal_info
from app.mapping.fx_mapper import to_converted_amounts
from app.mapping.productos_mapper import to_purchase_summary
from app.models.canonical import CustomerProfile, Meta, ProfileWarning
from app.providers.core_client import CoreClient
from app.providers.fx_client import FxClient
from app.providers.productos_client import ProductosClient

_core_client = CoreClient()
_productos_client = ProductosClient()
_fx_client = FxClient()


async def get_profile(customer_id: str, convert: bool = False) -> CustomerProfile:
    warnings: list[ProfileWarning] = []
    sources: dict[str, str] = {
        "core": "ok",
        "productos": "ok",
        "fx": "skipped",
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

    # FX: solo se intenta si se pidió conversión Y hay un total que
    # convertir (PRODUCTOS tuvo éxito). Nunca afecta `partial`, sin
    # importar el resultado.
    if convert and purchase_summary is not None:
        try:
            fx_dto = await _fx_client.fetch(customer_id)
            purchase_summary.convertedAmounts = to_converted_amounts(
                fx_dto, purchase_summary.totalSpentUSD
            )
            sources["fx"] = "ok"
        except ProviderError as exc:
            sources["fx"] = "failed"
            warnings.append(
                ProfileWarning(
                    provider="fx",
                    reason=type(exc).__name__,
                    detail=str(exc),
                )
            )
        except BaseException as exc:
            raise exc
    elif convert and purchase_summary is None:
        # Se pidió conversión pero no hay total que convertir porque
        # PRODUCTOS falló: no se intenta la llamada a FX.
        sources["fx"] = "skipped"
    # else: convert=False -> sources["fx"] ya quedó en "skipped" por
    # defecto, sin necesidad de warning (fue una elección, no un fallo).

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
