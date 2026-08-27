"""
Orquestador del caso de uso "perfil de cliente".

Este corte SOLO integra CORE. PRODUCTOS y FX se marcan explícitamente
como "not_implemented" en `sources` — todavía no se llaman ni afectan
`partial`, para no fingir un estado que no existe. Se implementan en
los siguientes cortes verticales.
"""

from datetime import datetime, timezone

from app.core.exceptions import CustomerNotFoundError, ProviderError
from app.mapping.core_mapper import empty_personal_info, to_personal_info
from app.models.canonical import CustomerProfile, Meta, ProfileWarning
from app.providers.core_client import CoreClient

_core_client = CoreClient()


async def get_profile(customer_id: str) -> CustomerProfile:
    warnings: list[ProfileWarning] = []
    sources: dict[str, str] = {
        "core": "ok",
        "productos": "not_implemented",
        "fx": "not_implemented",
    }

    try:
        core_dto = await _core_client.fetch(customer_id)
        personal_info = to_personal_info(core_dto)
    except CustomerNotFoundError:
        # No es degradación: el recurso no existe. Se propaga tal cual
        # para que el handler HTTP la traduzca a 404 (no a partial=true).
        raise
    except ProviderError as exc:
        # CORE agotó reintentos (timeout / 5xx / error de conexión).
        # No se aborta el request: se degrada con personalInfo vacío.
        sources["core"] = "failed"
        personal_info = empty_personal_info()
        warnings.append(
            ProfileWarning(
                provider="core",
                reason=type(exc).__name__,
                detail=str(exc),
            )
        )

    partial = sources["core"] == "failed"

    return CustomerProfile(
        customerId=customer_id,
        personalInfo=personal_info,
        purchaseSummary=None,
        meta=Meta(
            partial=partial,
            warnings=warnings,
            generatedAt=datetime.now(timezone.utc).isoformat(),
            sources=sources,
        ),
    )
